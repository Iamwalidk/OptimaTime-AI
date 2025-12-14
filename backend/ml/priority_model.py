import os
from typing import List
import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

from .data_gen import generate_synthetic_dataset

MODEL_PATH = os.path.join(os.path.dirname(__file__), "priority_model.pkl")

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


def train_and_save_model(path: str = MODEL_PATH):
    data = generate_synthetic_dataset(8000)
    X = []
    y = []
    for row in data:
        features = encode_features(
            user_type=row["user_type"],
            duration_minutes=row["duration_minutes"],
            hours_until_deadline=row["hours_until_deadline"],
            importance=row["importance"],
            task_type=row["task_type"],
            preferred_time=row["preferred_time"],
            energy=row["energy"],
            plan_day_of_week=row["plan_day_of_week"],
            is_weekend=row["is_weekend"],
        )
        X.append(features)
        y.append(row["priority"])

    X = np.array(X)
    y = np.array(y)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = GradientBoostingRegressor(random_state=42, n_estimators=200, max_depth=3)
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)
    print(f"Priority model R^2 on synthetic test set: {score:.3f}")

    joblib.dump(model, path)
    print(f"Model saved to {path}")


def load_model(path: str = MODEL_PATH):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        train_and_save_model(path)
    return joblib.load(path)


def get_feature_importances(model) -> List[float]:
    if hasattr(model, "feature_importances_"):
        return list(model.feature_importances_)
    return []
