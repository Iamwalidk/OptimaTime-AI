from datetime import date, datetime, timedelta

import pytest

from backend import ml


class _DummyModel:
    def __init__(self, output: float = 42.0):
        self.output = output
        self.calls = 0
        self.last_features = None

    def predict(self, payload):
        self.calls += 1
        # payload is [[features...]]
        self.last_features = list(payload[0])
        return [self.output]


def test_predict_priority_uses_cached_model(monkeypatch):
    dummy = _DummyModel(output=77.5)
    monkeypatch.setattr(ml, "get_priority_model", lambda: dummy)

    task = {
        "id": 1,
        "title": "Deep Work",
        "duration_minutes": 90,
        "deadline": datetime(2025, 5, 5, 15, 0),
        "importance": "high",
        "task_type": "work",
        "preferred_time": "morning",
        "energy": "high",
    }

    score = ml.predict_priority(
        task,
        user_profile="worker",
        plan_date=date(2025, 5, 5),
    )

    assert score == pytest.approx(77.5)
    assert dummy.calls == 1
    assert dummy.last_features is not None
    assert len(dummy.last_features) == 9  # safeguard for feature drift
    assert dummy.last_features[1] == float(task["duration_minutes"])


def test_prioritize_tasks_sorts_and_annotations(monkeypatch):
    priorities = {"Quick Sync": 80.0, "Deep Research": 25.0}

    def fake_predict(task, user_profile, plan_date):
        return priorities[task["title"]]

    monkeypatch.setattr(ml, "predict_priority", fake_predict)

    tasks = [
        {
            "id": 2,
            "title": "Deep Research",
            "duration_minutes": 120,
            "deadline": datetime.now() + timedelta(hours=4),
        },
        {
            "id": 3,
            "title": "Quick Sync",
            "duration_minutes": 30,
            "deadline": datetime.now() + timedelta(hours=1),
        },
    ]

    prioritized = ml.prioritize_tasks(tasks, user_profile="worker", plan_date=date.today())

    assert [t["title"] for t in prioritized] == ["Quick Sync", "Deep Research"]
    assert all("priority" in t for t in prioritized)
    assert "priority" not in tasks[0] and "priority" not in tasks[1]
