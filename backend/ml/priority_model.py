from __future__ import annotations

from pathlib import Path
from typing import List, Sequence

import joblib
import numpy as np

MODEL_PATH = Path(__file__).resolve().parent / "priority_model.pkl"

USER_TYPE_MAP = {"student": 0, "worker": 1, "entrepreneur": 2}
IMPORTANCE_MAP = {"low": 0, "medium": 1, "high": 2}
TASK_TYPE_MAP = {
    "study": 0,
    "work": 1,
    "meeting": 2,
    "personal": 3,
    "social": 4,
    "admin": 5,
}
PREF_TIME_MAP = {"morning": 0, "afternoon": 1, "evening": 2, "anytime": 3}
ENERGY_MAP = {"low": 0, "medium": 1, "high": 2}

FEATURE_ORDER = [
    "user_type",
    "duration_minutes",
    "hours_until_deadline",
    "importance",
    "task_type",
    "preferred_time",
    "energy",
    "plan_day_of_week",
    "is_weekend",
]


def encode_features(
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
    return [
        float(USER_TYPE_MAP.get(user_type, 0)),
        float(duration_minutes),
        float(hours_until_deadline),
        float(IMPORTANCE_MAP.get(importance, 1)),
        float(TASK_TYPE_MAP.get(task_type, 0)),
        float(PREF_TIME_MAP.get(preferred_time, 3)),
        float(ENERGY_MAP.get(energy, 1)),
        float(plan_day_of_week),
        float(is_weekend),
    ]


def load_model(path: str | Path = MODEL_PATH):
    model_path = Path(path)
    if not model_path.exists():
        raise FileNotFoundError(f"Priority model artifact not found at {model_path}")
    return joblib.load(model_path)


def predict(features: Sequence[float], *, model=None, path: str | Path = MODEL_PATH) -> float:
    estimator = model or load_model(path)
    payload = np.array([features], dtype=float)
    return float(estimator.predict(payload)[0])


def get_feature_importances(model) -> List[float]:
    if hasattr(model, "feature_importances_"):
        return list(model.feature_importances_)
    return []
