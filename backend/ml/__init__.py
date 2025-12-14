"""
High-level helpers that wire together the OptimaTime AI ML components.

The individual modules expose the model, scheduling, explanation, and data
generation utilities. This package initializer re-exports the most useful bits
and provides convenience helpers so application code can interact with the ML
stack via a single import.
"""

from __future__ import annotations

import os
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .data_gen import expert_priority_score, generate_synthetic_dataset
from .explainer import generate_explanation
from .priority_model import (
    MODEL_PATH,
    encode_features as _encode_features,
    get_feature_importances,
    load_model as _load_priority_model,
    train_and_save_model,
)
from .scheduler import SLOT_MINUTES, schedule_day

TaskDict = Dict[str, Any]

__all__ = [
    "MODEL_PATH",
    "encode_task_features",
    "get_priority_model",
    "train_priority_model",
    "predict_priority",
    "prioritize_tasks",
    "generate_schedule",
    "generate_explanation",
    "generate_synthetic_dataset",
    "expert_priority_score",
    "get_feature_importances",
]

_PRIORITY_MODEL_CACHE = None


def encode_task_features(
    *,
    user_type: str,
    duration_minutes: int,
    hours_until_deadline: float,
    importance: str,
    task_type: str,
    preferred_time: str,
    energy: str,
    plan_day_of_week: int,
    is_weekend: int,
) -> List[float]:
    """Public wrapper that keeps feature assembling co-located with the package API."""

    return _encode_features(
        user_type=user_type,
        duration_minutes=duration_minutes,
        hours_until_deadline=hours_until_deadline,
        importance=importance,
        task_type=task_type,
        preferred_time=preferred_time,
        energy=energy,
        plan_day_of_week=plan_day_of_week,
        is_weekend=is_weekend,
    )


def get_priority_model(force_reload: bool = False):
    """Returns the cached priority model instance, loading it from disk on demand."""

    global _PRIORITY_MODEL_CACHE
    if force_reload or _PRIORITY_MODEL_CACHE is None:
        _PRIORITY_MODEL_CACHE = _load_priority_model()
    return _PRIORITY_MODEL_CACHE


def train_priority_model(path: str = MODEL_PATH, force_retrain: bool = False):
    """Ensures a trained priority model exists and returns the loaded model."""

    if force_retrain or not os.path.exists(path):
        train_and_save_model(path)
        return get_priority_model(force_reload=True)
    return get_priority_model()


def _hours_until_deadline(deadline: Optional[datetime], reference: datetime) -> float:
    if not deadline:
        return 0.0
    return max(0.0, (deadline - reference).total_seconds() / 3600.0)


def predict_priority(
    task: TaskDict,
    *,
    user_profile: str,
    plan_date: date,
    reference_start_hour: int = 8,
) -> float:
    """Predicts a scalar priority score for a task using the trained model."""

    plan_start = datetime.combine(plan_date, datetime.min.time()).replace(hour=reference_start_hour)
    hours_until_deadline = _hours_until_deadline(task.get("deadline"), plan_start)
    plan_day_of_week = plan_date.weekday()
    features = encode_task_features(
        user_type=user_profile,
        duration_minutes=int(task.get("duration_minutes", SLOT_MINUTES)),
        hours_until_deadline=hours_until_deadline,
        importance=task.get("importance", "medium"),
        task_type=task.get("task_type", "work"),
        preferred_time=task.get("preferred_time", "anytime"),
        energy=task.get("energy", "medium"),
        plan_day_of_week=plan_day_of_week,
        is_weekend=1 if plan_day_of_week >= 5 else 0,
    )
    model = get_priority_model()
    return float(model.predict([features])[0])


def prioritize_tasks(
    tasks: Sequence[TaskDict],
    *,
    user_profile: str,
    plan_date: date,
) -> List[TaskDict]:
    """Returns the provided tasks annotated with a model-derived priority."""

    prioritized: List[TaskDict] = []
    for task in tasks:
        score = predict_priority(task, user_profile=user_profile, plan_date=plan_date)
        annotated = dict(task)
        annotated["priority"] = score
        prioritized.append(annotated)
    prioritized.sort(key=lambda t: t.get("priority", 0.0), reverse=True)
    return prioritized


def generate_schedule(
    tasks: Iterable[TaskDict],
    *,
    user_profile: str,
    plan_date: date,
    feedback: Optional[Sequence[Any]] = None,
    start_hour: int = 8,
    end_hour: int = 22,
) -> Tuple[List[Dict[str, Any]], List[TaskDict]]:
    """High-level façade around scheduler.schedule_day for convenience."""

    return schedule_day(
        tasks=list(tasks),
        user_profile=user_profile,
        plan_date=plan_date,
        feedback=feedback,
        start_hour=start_hour,
        end_hour=end_hour,
    )
