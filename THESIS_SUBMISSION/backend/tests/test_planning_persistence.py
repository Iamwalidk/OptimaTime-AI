from datetime import date, datetime, timedelta

import pytest
from fastapi import Depends
try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    TestClient = None
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import app
from backend.database import Base
from backend.dependencies import get_current_user, get_db
from backend import models

if TestClient is None:
    pytest.skip("fastapi TestClient requires requests", allow_module_level=True)


def _create_task(client: TestClient, title: str, deadline: datetime) -> dict:
    payload = {
        "title": title,
        "description": None,
        "duration_minutes": 60,
        "deadline": deadline.isoformat(),
        "task_type": "work",
        "importance": "high",
        "preferred_time": "morning",
        "energy": "high",
    }
    res = client.post("/api/v1/tasks", json=payload)
    assert res.status_code == 200, res.text
    return res.json()


def _plan(client: TestClient, plan_date: date) -> dict:
    res = client.post("/api/v1/planning/plan", json={"date": plan_date.isoformat()})
    assert res.status_code == 200, res.text
    return res.json()


def _has_overlaps(items: list[dict]) -> bool:
    parsed = [
        (datetime.fromisoformat(i["start"]), datetime.fromisoformat(i["end"]))
        for i in items
    ]
    for i, (start_a, end_a) in enumerate(parsed):
        for start_b, end_b in parsed[i + 1 :]:
            if start_a < end_b and end_a > start_b:
                return True
    return False


@pytest.fixture()
def client_env():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    with TestingSessionLocal() as db:
        user = models.User(
            email="user@example.com",
            name="Test User",
            profile=models.UserProfile.worker,
            role=models.UserRole.user,
            timezone="UTC",
            hashed_password="not-used",
            is_active=True,
            token_version=0,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        user_id = user.id

    def override_get_current_user(db=Depends(get_db)):
        return db.get(models.User, user_id)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    client = TestClient(app)

    yield client, TestingSessionLocal

    app.dependency_overrides.clear()


def test_planning_persistence_overlaps_and_feedback(client_env):
    client, session_factory = client_env
    plan_date = date.today()
    deadline = datetime.combine(plan_date, datetime.min.time()) + timedelta(hours=23, minutes=59)

    _create_task(client, "Task A", deadline)
    _create_task(client, "Task B", deadline)

    first_plan = _plan(client, plan_date)
    scheduled_first = first_plan["scheduled"]
    assert len(scheduled_first) == 2
    first_item_ids = {item["plan_item_id"] for item in scheduled_first}

    item_a = scheduled_first[0]
    item_b = scheduled_first[1]
    a_start = datetime.fromisoformat(item_a["start"])
    a_end = datetime.fromisoformat(item_a["end"])
    overlap_start = datetime.fromisoformat(item_b["start"]) + timedelta(minutes=15)
    overlap_end = overlap_start + (a_end - a_start)
    res = client.patch(
        f"/api/v1/planning/item/{item_a['plan_item_id']}",
        params={"start": overlap_start.isoformat(), "end": overlap_end.isoformat()},
    )
    assert res.status_code == 400
    assert "Time slot already occupied" in res.json()["detail"]

    _create_task(client, "Task C", deadline)
    second_plan = _plan(client, plan_date)
    scheduled_second = second_plan["scheduled"]
    assert len(scheduled_second) == 3
    assert first_item_ids.issubset({item["plan_item_id"] for item in scheduled_second})
    assert not _has_overlaps(scheduled_second)

    earliest = min(scheduled_second, key=lambda item: item["start"])
    earliest_start = datetime.fromisoformat(earliest["start"])
    earliest_end = datetime.fromisoformat(earliest["end"])
    moved_start = earliest_start - timedelta(hours=1)
    moved_end = moved_start + (earliest_end - earliest_start)
    res = client.patch(
        f"/api/v1/planning/item/{earliest['plan_item_id']}",
        params={"start": moved_start.isoformat(), "end": moved_end.isoformat()},
    )
    assert res.status_code == 200

    feedback_res = client.get("/api/v1/feedback")
    assert feedback_res.status_code == 200
    feedback = feedback_res.json()
    assert any(
        fb["task_id"] == earliest["task_id"] and fb["outcome"] == 1 for fb in feedback
    )

    with session_factory() as db:
        moved_item = db.get(models.PlanItem, earliest["plan_item_id"])
        assert moved_item.source == "manual"

    _create_task(client, "Task D", deadline)
    third_plan = _plan(client, plan_date)
    scheduled_third = third_plan["scheduled"]
    assert len(scheduled_third) == 4
    assert not _has_overlaps(scheduled_third)
