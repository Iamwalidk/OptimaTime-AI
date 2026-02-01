from __future__ import annotations

import logging
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .priority_model import (
    MODEL_PATH,
    encode_features,
    get_feature_importances,
    load_model,
    predict,
)
from .scheduler import SLOT_MINUTES, schedule_day
from .train_priority_model import train_and_save_model

logger = logging.getLogger(__name__)

TaskDict = Dict[str, Any]
_PRIORITY_MODEL_CACHE = None


def _get_package():
    return sys.modules.get(__name__.rsplit(".", 1)[0])


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
    return encode_features(
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


def _hours_until_deadline(deadline: Optional[datetime], reference: datetime) -> float:
    if not deadline:
        return 0.0
    return max(0.0, (deadline - reference).total_seconds() / 3600.0)


def get_priority_model(force_reload: bool = False):
    global _PRIORITY_MODEL_CACHE
    if force_reload or _PRIORITY_MODEL_CACHE is None:
        try:
            _PRIORITY_MODEL_CACHE = load_model()
        except FileNotFoundError as exc:
            message = (
                f"Priority model artifact not found at {MODEL_PATH}. "
                "Run backend/ml/train_priority_model.py to generate it."
            )
            logger.error(message)
            raise RuntimeError(message) from exc
    return _PRIORITY_MODEL_CACHE


def train_priority_model(path: Path | str = MODEL_PATH, force_retrain: bool = False):
    artifact_path = Path(path)
    if force_retrain or not artifact_path.exists():
        train_and_save_model(path=artifact_path)
        return get_priority_model(force_reload=True)
    return get_priority_model()


def predict_priority(
    task: TaskDict,
    *,
    user_profile: str,
    plan_date: date,
    reference_start_hour: int = 8,
) -> float:
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
    pkg = _get_package()
    model_provider = getattr(pkg, "get_priority_model", get_priority_model) if pkg else get_priority_model
    model = model_provider()
    return predict(features, model=model)


def prioritize_tasks(
    tasks: Sequence[TaskDict],
    *,
    user_profile: str,
    plan_date: date,
) -> List[TaskDict]:
    prioritized: List[TaskDict] = []
    pkg = _get_package()
    predict_fn = getattr(pkg, "predict_priority", predict_priority) if pkg else predict_priority
    for task in tasks:
        score = predict_fn(task, user_profile=user_profile, plan_date=plan_date)
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
    occupied: Optional[Sequence[Tuple[datetime, datetime]]] = None,
) -> Tuple[List[Dict[str, Any]], List[TaskDict], Optional[float]]:
    model = get_priority_model()
    scheduled, unscheduled, model_confidence = schedule_day(
        tasks=list(tasks),
        user_profile=user_profile,
        plan_date=plan_date,
        feedback=feedback,
        start_hour=start_hour,
        end_hour=end_hour,
        occupied_intervals=occupied,
        model=model,
    )
    feature_importances = get_feature_importances(model)
    if feature_importances and model_confidence is None:
        model_confidence = float(sum(feature_importances[:3]))
    return scheduled, unscheduled, model_confidence
