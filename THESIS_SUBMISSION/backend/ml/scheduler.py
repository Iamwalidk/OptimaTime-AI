import random
from datetime import datetime, timedelta, date
from typing import List, Dict, Any, Tuple, Optional, Sequence

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


def _bias_from_feedback(feedback: Optional[List[Any]]) -> Tuple[Dict[str, float], float]:
    if not feedback:
        return {}, 0.0
    now = datetime.utcnow()
    totals: Dict[str, float] = {}
    weights: Dict[str, float] = {}
    total_weight = 0.0
    for fb in feedback:
        task = getattr(fb, "task", None)
        if not task or fb.outcome is None:
            continue
        created_at = getattr(fb, "created_at", None) or now
        age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
        weight = float(np.exp(-age_days / 14.0))
        total_weight += weight
        keys = (
            f"type_importance:{task.task_type}:{task.importance}",
            f"preferred_time:{task.preferred_time}",
            f"energy:{task.energy}",
        )
        for key in keys:
            totals[key] = totals.get(key, 0.0) + fb.outcome * weight
            weights[key] = weights.get(key, 0.0) + weight
    bias = {}
    for key, total in totals.items():
        weight = weights.get(key, 0.0)
        if weight <= 0:
            continue
        avg = total / weight
        bias[key] = 2.0 * avg
    strength = min(1.0, total_weight / 8.0) if total_weight > 0.0 else 0.0
    if strength > 0.0:
        for key in list(bias.keys()):
            bias[key] *= strength
    else:
        bias = {}
    return bias, strength


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


def _fragmentation_penalty(
    occupied: List[Optional[int]],
    start_idx: int,
    required_slots: int,
) -> float:
    n_slots = len(occupied)
    end_idx = start_idx + required_slots
    penalty = 0.0

    left_gap = 0
    i = start_idx - 1
    while i >= 0 and occupied[i] is None:
        left_gap += 1
        i -= 1
    if 0 < left_gap < 2 and i >= 0 and occupied[i] is not None:
        penalty += 1.0

    right_gap = 0
    i = end_idx
    while i < n_slots and occupied[i] is None:
        right_gap += 1
        i += 1
    if 0 < right_gap < 2 and i < n_slots and occupied[i] is not None:
        penalty += 1.0

    return penalty * 2.0


def _placement_cost(
    *,
    occupied: List[Optional[int]],
    day_slots: List[datetime],
    start_idx: int,
    required_slots: int,
    latest_end: datetime,
    preferred_window: Tuple[int, int],
    task_energy: str,
    duration_minutes: int,
    hours_until_deadline: float,
) -> float:
    pref_start, pref_end = preferred_window
    preferred_penalty = 0.0 if pref_start <= start_idx < pref_end else 4.0

    end_dt = day_slots[start_idx] + timedelta(minutes=duration_minutes)
    slack_minutes = max(0.0, (latest_end - end_dt).total_seconds() / 60.0)
    urgency_penalty = 0.0
    if hours_until_deadline < 48.0:
        urgency_weight = (48.0 - hours_until_deadline) / 48.0
        if slack_minutes < 240.0:
            urgency_penalty = ((240.0 - slack_minutes) / 240.0) * 6.0 * urgency_weight

    energy_mismatch_penalty = 0.0
    start_hour = day_slots[start_idx].hour
    if task_energy == "high" and start_hour >= 17:
        energy_mismatch_penalty = 2.0
    elif task_energy == "low" and start_hour < 12:
        energy_mismatch_penalty = 2.0

    fragmentation_penalty = _fragmentation_penalty(occupied, start_idx, required_slots)

    return preferred_penalty + urgency_penalty + energy_mismatch_penalty + fragmentation_penalty


def _best_start_slot(
    occupied: List[Optional[int]],
    day_slots: List[datetime],
    required_slots: int,
    latest_end: datetime,
    preferred_window: Tuple[int, int],
    task_energy: str,
    duration_minutes: int,
    hours_until_deadline: float,
    feedback_strength: float,
    rng: random.Random,
) -> Optional[int]:
    n_slots = len(day_slots)

    def _can_place(start_idx: int) -> bool:
        end_idx = start_idx + required_slots
        if end_idx > n_slots:
            return False
        if day_slots[end_idx - 1] >= latest_end:
            return False
        return all(occupied[i] is None for i in range(start_idx, end_idx))

    pref_start, pref_end = preferred_window
    if pref_end > pref_start:
        pref_center = (pref_start + pref_end - 1) / 2.0
    else:
        pref_center = max(0.0, (n_slots - 1) / 2.0)

    candidates: List[Tuple[float, float, int, int]] = []
    candidates_by_cost: List[Tuple[float, int]] = []

    for start_idx in range(0, n_slots - required_slots + 1):
        if not _can_place(start_idx):
            continue
        cost = _placement_cost(
            occupied=occupied,
            day_slots=day_slots,
            start_idx=start_idx,
            required_slots=required_slots,
            latest_end=latest_end,
            preferred_window=preferred_window,
            task_energy=task_energy,
            duration_minutes=duration_minutes,
            hours_until_deadline=hours_until_deadline,
        )
        center_distance = abs(start_idx - pref_center)
        early_start_penalty = 1 if start_idx == 0 else 0
        candidates.append((cost, center_distance, early_start_penalty, start_idx))
        candidates_by_cost.append((cost, start_idx))

    if not candidates:
        return None

    if feedback_strength < 0.4 and rng.random() < 0.10:
        candidates_by_cost.sort(key=lambda item: item[0])
        top = candidates_by_cost[:3]
        return rng.choice(top)[1]

    candidates.sort(key=lambda item: (item[0], item[1], item[2], item[3]))
    return candidates[0][3]


def _apply_occupied_intervals(
    occupied: List[Optional[int]],
    day_slots: List[datetime],
    intervals: Optional[Sequence[Tuple[datetime, datetime]]],
) -> None:
    if not intervals or not day_slots:
        return
    day_start = day_slots[0]
    day_end = day_slots[-1] + timedelta(minutes=SLOT_MINUTES)
    for start, end in intervals:
        if end <= day_start or start >= day_end:
            continue
        for idx, slot_start in enumerate(day_slots):
            slot_end = slot_start + timedelta(minutes=SLOT_MINUTES)
            if slot_start < end and slot_end > start:
                occupied[idx] = -1


def _shift_earlier(assignments, occupied, day_slots):
    # Try to move tasks earlier if the placement cost improves.
    n_slots = len(day_slots)
    for task_id, info in assignments.items():
        required_slots = info["required_slots"]
        current_start = info["start_idx"]
        latest_end = info["latest_end"]
        preferred_window = info.get("preferred_window", (0, n_slots))
        task_energy = info.get("energy", "medium")
        duration_minutes = info.get("duration_minutes", required_slots * SLOT_MINUTES)
        hours_until_deadline = info.get("hours_until_deadline", 0.0)
        temp_occupied = [None if slot == task_id else slot for slot in occupied]
        current_cost = _placement_cost(
            occupied=temp_occupied,
            day_slots=day_slots,
            start_idx=current_start,
            required_slots=required_slots,
            latest_end=latest_end,
            preferred_window=preferred_window,
            task_energy=task_energy,
            duration_minutes=duration_minutes,
            hours_until_deadline=hours_until_deadline,
        )
        for start_idx in range(0, current_start):
            end_idx = start_idx + required_slots
            if end_idx > n_slots or day_slots[end_idx - 1] >= latest_end:
                break
            if all(temp_occupied[i] is None for i in range(start_idx, end_idx)):
                candidate_cost = _placement_cost(
                    occupied=temp_occupied,
                    day_slots=day_slots,
                    start_idx=start_idx,
                    required_slots=required_slots,
                    latest_end=latest_end,
                    preferred_window=preferred_window,
                    task_energy=task_energy,
                    duration_minutes=duration_minutes,
                    hours_until_deadline=hours_until_deadline,
                )
                if candidate_cost >= current_cost:
                    continue
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
    occupied_intervals: Optional[Sequence[Tuple[datetime, datetime]]] = None,
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
    _apply_occupied_intervals(occupied, day_slots, occupied_intervals)

    plan_start = day_slots[0]
    scheduled = []
    assignments = {}
    unscheduled = []

    bias_map, feedback_strength = _bias_from_feedback(feedback)
    seed = hash((plan_date.isoformat(), user_profile)) & 0xFFFFFFFF
    rng = random.Random(seed)
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
        bias = 0.0
        bias_reasons = []
        type_key = f"type_importance:{t['task_type']}:{t['importance']}"
        if type_key in bias_map:
            bias += bias_map[type_key]
            bias_reasons.append(f"{t['task_type']} {t['importance']}")
        pref_key = f"preferred_time:{t['preferred_time']}"
        if pref_key in bias_map:
            bias += bias_map[pref_key]
            if t["preferred_time"] != "anytime":
                bias_reasons.append(f"{t['preferred_time']} time")
            else:
                bias_reasons.append("time preference")
        energy_key = f"energy:{t['energy']}"
        if energy_key in bias_map:
            bias += bias_map[energy_key]
            bias_reasons.append(f"{t['energy']} energy")

        urgency_boost = 0.0
        if hours_until_deadline < 48.0:
            urgency_boost = (48.0 - hours_until_deadline) / 48.0 * 1.5
            if hours_until_deadline < 24.0:
                urgency_boost += (24.0 - hours_until_deadline) / 24.0 * 1.5

        importance_boost = 0.4 if t["importance"] == "high" else 0.0

        priority = base_priority + bias + urgency_boost + importance_boost
        scored_tasks.append(
            {
                "task": t,
                "priority": priority,
                "base_priority": base_priority,
                "hours_until_deadline": hours_until_deadline,
                "bias": bias,
                "bias_reasons": bias_reasons,
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
        best_start = _best_start_slot(
            occupied=occupied,
            day_slots=day_slots,
            required_slots=required_slots,
            latest_end=latest_end,
            preferred_window=preferred_window,
            task_energy=t["energy"],
            duration_minutes=t["duration_minutes"],
            hours_until_deadline=item["hours_until_deadline"],
            feedback_strength=feedback_strength,
            rng=rng,
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
        if abs(item["bias"]) > 0 and item["bias_reasons"]:
            direction = "earlier" if item["bias"] > 0 else "later"
            reasons = ", ".join(item["bias_reasons"])
            bias_text = f"Personalization: adjusted {direction} based on your feedback for {reasons}."

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
            "preferred_window": preferred_window,
            "energy": t["energy"],
            "duration_minutes": t["duration_minutes"],
            "hours_until_deadline": item["hours_until_deadline"],
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
