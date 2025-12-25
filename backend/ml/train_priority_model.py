from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Tuple

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

if __package__ is None:
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from backend.ml.data_gen import generate_synthetic_dataset
    from backend.ml.priority_model import MODEL_PATH, encode_features
else:
    from .data_gen import generate_synthetic_dataset
    from .priority_model import MODEL_PATH, encode_features


def _build_training_matrix(samples: Iterable[dict]) -> Tuple[np.ndarray, np.ndarray]:
    X: List[List[float]] = []
    y: List[float] = []
    for row in samples:
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
    return np.array(X, dtype=float), np.array(y, dtype=float)


def train_and_save_model(path: Path | str = MODEL_PATH, samples: int = 8000) -> Path:
    dataset = generate_synthetic_dataset(samples)
    X, y = _build_training_matrix(dataset)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = GradientBoostingRegressor(random_state=42, n_estimators=200, max_depth=3)
    model.fit(X_train, y_train)
    score = model.score(X_test, y_test)

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, output_path)

    print(f"Priority model R^2 on synthetic test set: {score:.3f}")
    print(f"Model saved to {output_path}")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train the OptimaTime priority model.")
    parser.add_argument(
        "--output",
        type=Path,
        default=MODEL_PATH,
        help="Where to write the trained model artifact.",
    )
    parser.add_argument(
        "--samples",
        type=int,
        default=8000,
        help="How many synthetic samples to generate for training.",
    )
    args = parser.parse_args()

    train_and_save_model(path=args.output, samples=args.samples)
