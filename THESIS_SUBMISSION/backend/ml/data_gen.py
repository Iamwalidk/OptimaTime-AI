import random
from datetime import timedelta, datetime
from typing import List, Dict

USER_TYPES = ["student", "worker", "entrepreneur"]
TASK_TYPES = ["study", "work", "meeting", "personal", "social", "admin"]
IMPORTANCE = ["low", "medium", "high"]
PREF_TIMES = ["morning", "afternoon", "evening", "anytime"]
ENERGY = ["low", "medium", "high"]


def expert_priority_score(
    user_type: str,
    duration_minutes: int,
    hours_until_deadline: float,
    importance: str,
    task_type: str,
    preferred_time: str,
    energy: str,
    plan_day_of_week: int,
    is_weekend: int,
) -> float:
    # base importance
    if importance == "high":
        score = 70
    elif importance == "medium":
        score = 45
    else:
        score = 20

    # deadline pressure
    if hours_until_deadline <= 4:
        score += 25
    elif hours_until_deadline <= 24:
        score += 15
    elif hours_until_deadline <= 72:
        score += 5

    # user-task affinity
    if user_type == "student" and task_type == "study":
        score += 10
    if user_type == "worker" and task_type in ("work", "meeting"):
        score += 10
    if user_type == "entrepreneur" and task_type in ("work", "admin"):
        score += 10

    # duration penalty for long items
    if duration_minutes > 120:
        score -= 5

    # energy boost
    if energy == "high":
        score += 5

    # temporal patterns: weekend vs weekday scheduling
    if is_weekend:
        if task_type in ("social", "personal"):
            score += 8
        if task_type in ("work", "study"):
            score -= 5
    else:
        if task_type in ("work", "meeting"):
            score += 6

    # preferred time alignment heuristic: morning tasks earlier in week, evening later
    if preferred_time == "morning" and plan_day_of_week <= 2:
        score += 3
    if preferred_time == "evening" and plan_day_of_week >= 3:
        score += 2

    return max(0.0, min(100.0, score))


def generate_synthetic_dataset(n: int = 6000) -> List[Dict]:
    now = datetime.utcnow()
    data = []
    for _ in range(n):
        user_type = random.choice(USER_TYPES)
        duration = random.choice([30, 60, 90, 120, 150, 180])
        hours_until_deadline = random.uniform(1, 120)
        importance = random.choices(IMPORTANCE, weights=[0.3, 0.4, 0.3])[0]
        task_type = random.choice(TASK_TYPES)
        preferred_time = random.choice(PREF_TIMES)
        energy = random.choices(ENERGY, weights=[0.3, 0.5, 0.2])[0]

        plan_day_of_week = random.randint(0, 6)
        is_weekend = 1 if plan_day_of_week >= 5 else 0

        deadline = now + timedelta(hours=hours_until_deadline)
        y = expert_priority_score(
            user_type=user_type,
            duration_minutes=duration,
            hours_until_deadline=hours_until_deadline,
            importance=importance,
            task_type=task_type,
            preferred_time=preferred_time,
            energy=energy,
            plan_day_of_week=plan_day_of_week,
            is_weekend=is_weekend,
        )

        data.append(
            dict(
                user_type=user_type,
                duration_minutes=duration,
                hours_until_deadline=hours_until_deadline,
                importance=importance,
                task_type=task_type,
                preferred_time=preferred_time,
                energy=energy,
                deadline=deadline,
                priority=y,
                plan_day_of_week=plan_day_of_week,
                is_weekend=is_weekend,
            )
        )
    return data
