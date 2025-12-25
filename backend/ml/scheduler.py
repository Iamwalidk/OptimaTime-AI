import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Tuple, Optional

import numpy as np

from .priority_model import encode_features, load_model, get_feature_importances
from .explainer import generate_explanation

SLOT_MINUTES = 30


def build_day_slots(
    day_date: date,
    start_hour: int = 8,
    end_hour: int = 22,
) -> List[datetime]:
    start = datetime.combine(day_date, datetime.min.time()).replace(hour=start_hour)
    end = datetime.combine(day_date, datetime.min.time()).replace(hour=end_hour)
    slots = []
    current = start
    while current < end:
        slots.append(current)
        current += timedelta(minutes=SLOT_MINUTES)
    return slots


def _bias_from_feedback(feedback: Optional[List[Any]]) -> Dict[str, float]:
    if not feedback:
        return {}
    scores: Dict[str, List[int]] = {}
    for fb in feedback:
        if fb.task and fb.outcome:
            key = f"{fb.task.task_type}:{fb.task.importance}"
            scores.setdefault(key, []).append(fb.outcome)
    bias = {}
    for task_type, outcomes in scores.items():
        avg = sum(outcomes) / max(1, len(outcomes))
        # stronger personalization weight so feedback is noticeable
        bias[task_type] = 5.0 * avg
    return bias


def _time_window_indices(pref: str, n_slots: int, start_hour: int, end_hour: int) -> Tuple[int, int]:
    """
    Map preferred time windows to slot ranges based on configured working hours.
    """

    def hour_to_idx(hour: int) -> int:
        return max(0, int(((hour - start_hour) * 60) / SLOT_MINUTES))

    morning_end = min(end_hour, 12)
    afternoon_start = max(start_hour, 12)
    afternoon_end = min(end_hour, 18)
    evening_start = max(start_hour, 18)

    if pref == "morning":
        return 0, max(0, hour_to_idx(morning_end))
    elif pref == "afternoon":
        return hour_to_idx(afternoon_start), hour_to_idx(afternoon_end)
    elif pref == "evening":
        return hour_to_idx(evening_start), n_slots
    else:
        return 0, n_slots


def _attempt_place(
    occupied: List[Optional[int]],
    day_slots: List[datetime],
    required_slots: int,
    latest_end: datetime,
    preferred_window: Tuple[int, int],
) -> Optional[int]:
    n_slots = len(day_slots)
    pref_start, pref_end = preferred_window

    def _can_place(start_idx: int) -> bool:
        end_idx = start_idx + required_slots
        if end_idx > n_slots:
            return False
        if day_slots[end_idx - 1] >= latest_end:
            return False
        return all(occupied[i] is None for i in range(start_idx, end_idx))

    for start_idx in range(pref_start, min(pref_end, n_slots - required_slots + 1)):
        if _can_place(start_idx):
            return start_idx

    for start_idx in range(0, n_slots - required_slots + 1):
        if _can_place(start_idx):
            return start_idx

    return None


def _shift_earlier(assignments, occupied, day_slots):
    # Try to move tasks earlier if possible to reduce lateness and align preferences
    n_slots = len(day_slots)
    for task_id, info in assignments.items():
        required_slots = info["required_slots"]
        current_start = info["start_idx"]
        latest_end = info["latest_end"]
        for start_idx in range(0, current_start):
            end_idx = start_idx + required_slots
            if end_idx > n_slots or day_slots[end_idx - 1] >= latest_end:
                break
            if all(occupied[i] in (None, task_id) for i in range(start_idx, end_idx)):
                # free current slots
                for i in range(info["start_idx"], info["end_idx"]):
                    occupied[i] = None
                # place earlier
                for i in range(start_idx, end_idx):
                    occupied[i] = task_id
                info["start_idx"] = start_idx
                info["end_idx"] = end_idx
                break


def _llm_style_explanation(task, start_dt, user_profile, priority, bias_text):
    return (
        f"I placed '{task['title']}' at {start_dt.strftime('%H:%M')} because you're a {user_profile}, "
        f"priority {priority:.1f}. {bias_text or 'Kept preferences and deadline in mind.'}"
    )


def schedule_day(
    tasks: List[Dict[str, Any]],
    user_profile: str,
    plan_date: date,
    feedback: Optional[List[Any]] = None,
    start_hour: int = 8,
    end_hour: int = 22,
    model=None,
):
    model = model or load_model()
    feature_importances = get_feature_importances(model)
    top_features = list(np.argsort(feature_importances)[::-1][:3]) if feature_importances else []
    model_confidence = float(np.sum(feature_importances[:3])) if feature_importances else None

    day_slots = build_day_slots(plan_date, start_hour=start_hour, end_hour=end_hour)
    if not day_slots:
        return [], [{**t, "reason": "No working hours configured for this day"} for t in tasks], model_confidence
    n_slots = len(day_slots)
    occupied: List[Optional[int]] = [None] * n_slots

    plan_start = day_slots[0]
    scheduled = []
    assignments = {}
    unscheduled = []

    bias_by_task_type = _bias_from_feedback(feedback)
    plan_day_of_week = plan_date.weekday()
    is_weekend = 1 if plan_day_of_week >= 5 else 0

    scored_tasks = []
    for t in tasks:
        hours_until_deadline = max(
            0.0, (t["deadline"] - plan_start).total_seconds() / 3600.0
        )
        features = encode_features(
            user_type=user_profile,
            duration_minutes=t["duration_minutes"],
            hours_until_deadline=hours_until_deadline,
            importance=t["importance"],
            task_type=t["task_type"],
            preferred_time=t["preferred_time"],
            energy=t["energy"],
            plan_day_of_week=plan_day_of_week,
            is_weekend=is_weekend,
        )
        base_priority = float(model.predict([features])[0])
        bias_key = f"{t['task_type']}:{t['importance']}"
        bias = bias_by_task_type.get(bias_key, 0.0)
        priority = base_priority + bias
        scored_tasks.append(
            {
                "task": t,
                "priority": priority,
                "base_priority": base_priority,
                "hours_until_deadline": hours_until_deadline,
            }
        )

    scored_tasks.sort(key=lambda x: x["priority"], reverse=True)

    for item in scored_tasks:
        t = item["task"]
        required_slots = (t["duration_minutes"] + SLOT_MINUTES - 1) // SLOT_MINUTES

        if required_slots > n_slots:
            unscheduled.append({**t, "reason": "Duration exceeds available day length"})
            continue

        latest_end = min(
            datetime.combine(plan_date, datetime.min.time()).replace(hour=end_hour),
            t["deadline"],
        )

        preferred_window = _time_window_indices(t["preferred_time"], n_slots, start_hour, end_hour)
        best_start = _attempt_place(
            occupied=occupied,
            day_slots=day_slots,
            required_slots=required_slots,
            latest_end=latest_end,
            preferred_window=preferred_window,
        )

        if best_start is None:
            unscheduled.append({**t, "reason": "No available slot before deadline/preference"})
            continue

        for i in range(best_start, best_start + required_slots):
            occupied[i] = t["id"]

        start_dt = day_slots[best_start]
        end_dt = start_dt + timedelta(minutes=t["duration_minutes"])

        active_constraints = {
            "preferred_window": best_start >= preferred_window[0] and best_start < preferred_window[1],
            "deadline_binding": end_dt >= t["deadline"] - timedelta(hours=1),
            "low_conflicts": True,
        }

        bias_text = ""
        if abs(bias) > 0:
            direction = "earlier" if bias > 0 else "later"
            bias_text = f"Personalization: adjusted {direction} based on your past feedback for {t['task_type']} tasks."

        explanation = generate_explanation(
            task=t,
            user_profile=user_profile,
            priority=item["priority"],
            start_dt=start_dt,
            end_dt=end_dt,
            hours_until_deadline=item["hours_until_deadline"],
            active_constraints=active_constraints,
            top_features=top_features,
            bias_reason=bias_text,
        )
        llm_exp = _llm_style_explanation(t, start_dt, user_profile, item["priority"], bias_text)

        scheduled.append(
            {
                "task_id": t["id"],
                "title": t["title"],
                "start": start_dt.isoformat(),
                "end": end_dt.isoformat(),
                "explanation": explanation,
                "priority": item["priority"],
                "llm_explanation": llm_exp,
            }
        )

        assignments[t["id"]] = {
            "start_idx": best_start,
            "end_idx": best_start + required_slots,
            "latest_end": latest_end,
            "required_slots": required_slots,
        }

    # Local improvement: move tasks earlier when possible
    _shift_earlier(assignments, occupied, day_slots)

    # Recompute scheduled outputs to reflect shifts
    for s in scheduled:
        info = assignments.get(s["task_id"])
        if info:
            start_dt = day_slots[info["start_idx"]]
            end_dt = day_slots[info["end_idx"] - 1] + timedelta(minutes=SLOT_MINUTES)
            s["start"] = start_dt.isoformat()
            s["end"] = end_dt.isoformat()

    return scheduled, unscheduled, model_confidence
