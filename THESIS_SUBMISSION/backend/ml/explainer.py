from datetime import datetime
from typing import Dict, Any, List


PART_LABELS = {
    0: "user profile affinity",
    1: "shorter duration",
    2: "deadline proximity",
    3: "task importance",
    4: "task category",
    5: "preferred time",
    6: "energy requirement",
    7: "day-of-week fit",
    8: "weekend/weekday context",
}


def _part_of_day(dt: datetime) -> str:
    h = dt.hour
    if 6 <= h < 12:
        return "morning"
    if 12 <= h < 18:
        return "afternoon"
    return "evening"


def _top_feature_phrases(top_features: List[int]) -> List[str]:
    phrases = []
    for feat_idx in top_features:
        label = PART_LABELS.get(feat_idx)
        if label:
            phrases.append(label)
    return phrases


def generate_explanation(
    task: Dict[str, Any],
    user_profile: str,
    priority: float,
    start_dt: datetime,
    end_dt: datetime,
    hours_until_deadline: float,
    active_constraints: Dict[str, bool],
    top_features: List[int],
    bias_reason: str = "",
) -> str:
    parts = []

    # Importance + deadline
    if task["importance"] == "high":
        parts.append("Marked as high importance.")
    elif task["importance"] == "medium":
        parts.append("Moderate importance, balanced with other tasks.")
    else:
        parts.append("Lower importance, scheduled after critical items.")

    if hours_until_deadline <= 4:
        parts.append("Deadline is imminent, so it was prioritized aggressively.")
    elif hours_until_deadline <= 24:
        parts.append("Due within the day, elevated in the ranking.")
    elif hours_until_deadline <= 72:
        parts.append("Due in a few days, kept near the middle of the day.")
    else:
        parts.append("Deadline is far out, giving flexibility.")

    # Profile-specific emphasis
    if user_profile == "student" and task["task_type"] == "study":
        parts.append("Study items boosted for your student profile.")
    if user_profile == "worker" and task["task_type"] in ("work", "meeting"):
        parts.append("Work/meeting tasks favored for a working profile.")
    if user_profile == "entrepreneur" and task["task_type"] in ("work", "admin"):
        parts.append("Work/admin emphasized for entrepreneurial profile.")

    # Scheduling rationale
    scheduled_part = _part_of_day(start_dt)
    if task["preferred_time"] != "anytime":
        if active_constraints.get("preferred_window", False):
            parts.append(f"Placed in the {scheduled_part} to match your preferred window.")
        else:
            parts.append(
                f"Preferred {task['preferred_time']} but scheduled in the {scheduled_part} to satisfy constraints."
            )
    else:
        parts.append(f"Scheduled in the {scheduled_part} since no specific time preference was set.")

    if active_constraints.get("deadline_binding", False):
        parts.append("Slot chosen to remain before the deadline.")
    if active_constraints.get("low_conflicts", False):
        parts.append("Position selected to reduce context switches.")

    # Model introspection summary
    top_phrases = _top_feature_phrases(top_features)
    if top_phrases:
        parts.append("Key signals: " + ", ".join(top_phrases) + ".")

    if bias_reason:
        parts.append(bias_reason)

    parts.append(f"Learned priority score: {priority:.1f} (relative scale).")

    return " ".join(parts)
