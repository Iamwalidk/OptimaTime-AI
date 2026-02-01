from datetime import datetime, timedelta

from backend.ml import scheduler


class _DummyTask:
    def __init__(self, task_type, importance, preferred_time, energy):
        self.task_type = task_type
        self.importance = importance
        self.preferred_time = preferred_time
        self.energy = energy


class _DummyFeedback:
    def __init__(self, task, outcome, created_at):
        self.task = task
        self.outcome = outcome
        self.created_at = created_at


def test_bias_strength_near_zero_without_recent_feedback():
    bias, strength = scheduler._bias_from_feedback([])
    assert bias == {}
    assert strength == 0.0

    now = datetime.utcnow()
    task = _DummyTask("work", "high", "morning", "high")
    old_feedback = [_DummyFeedback(task, outcome=1, created_at=now - timedelta(days=200))]

    bias_old, strength_old = scheduler._bias_from_feedback(old_feedback)

    assert strength_old < 0.01
    assert abs(bias_old["type_importance:work:high"]) < 0.01


def test_bias_strength_grows_with_recent_feedback():
    now = datetime.utcnow()
    task = _DummyTask("work", "high", "morning", "high")
    feedback = [
        _DummyFeedback(task, outcome=1, created_at=now - timedelta(hours=2)),
        _DummyFeedback(task, outcome=1, created_at=now - timedelta(hours=3)),
        _DummyFeedback(task, outcome=1, created_at=now - timedelta(hours=4)),
        _DummyFeedback(task, outcome=1, created_at=now - timedelta(hours=5)),
        _DummyFeedback(task, outcome=1, created_at=now - timedelta(hours=6)),
        _DummyFeedback(task, outcome=1, created_at=now - timedelta(hours=7)),
        _DummyFeedback(task, outcome=1, created_at=now - timedelta(hours=8)),
        _DummyFeedback(task, outcome=1, created_at=now - timedelta(hours=9)),
    ]

    bias_one, strength_one = scheduler._bias_from_feedback(feedback[:1])
    bias_many, strength_many = scheduler._bias_from_feedback(feedback)

    assert strength_many > strength_one
    assert bias_many["type_importance:work:high"] > bias_one["type_importance:work:high"]
    assert "preferred_time:morning" in bias_many
    assert "energy:high" in bias_many


def test_bias_uses_most_recent_feedback_when_limited():
    now = datetime.utcnow()
    task = _DummyTask("work", "high", "morning", "high")
    feedback = [
        _DummyFeedback(task, outcome=1, created_at=now - timedelta(minutes=i)) for i in range(500)
    ]
    feedback.extend(
        _DummyFeedback(task, outcome=-1, created_at=now - timedelta(days=30 + i)) for i in range(100)
    )

    recent_only = sorted(feedback, key=lambda fb: fb.created_at, reverse=True)[:500]
    bias_recent, strength_recent = scheduler._bias_from_feedback(recent_only)
    bias_all, _ = scheduler._bias_from_feedback(feedback)

    assert strength_recent > 0.0
    assert bias_recent["type_importance:work:high"] > 0.0
    assert bias_recent["type_importance:work:high"] > bias_all["type_importance:work:high"]
