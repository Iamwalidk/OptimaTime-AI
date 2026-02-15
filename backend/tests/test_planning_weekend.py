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


def _next_saturday(from_date: date) -> date:
    days_ahead = (5 - from_date.weekday()) % 7
    return from_date + timedelta(days=days_ahead)


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

    yield client, TestingSessionLocal, user_id

    app.dependency_overrides.clear()


def test_planning_creates_settings_and_allows_weekend(client_env):
    client, session_factory, user_id = client_env
    plan_date = _next_saturday(date.today())
    deadline = datetime.combine(plan_date, datetime.min.time()) + timedelta(hours=23, minutes=59)

    _create_task(client, "Weekend Task", deadline)
    _plan(client, plan_date)

    with session_factory() as db:
        settings = (
            db.query(models.UserSettings)
            .filter(models.UserSettings.user_id == user_id)
            .first()
        )
        assert settings is not None


def test_planning_ignores_workday_mask_for_selected_date(client_env):
    client, session_factory, user_id = client_env
    plan_date = _next_saturday(date.today())
    deadline = datetime.combine(plan_date, datetime.min.time()) + timedelta(hours=23, minutes=59)

    with session_factory() as db:
        settings = models.UserSettings(
            user_id=user_id,
            work_days_mask="1111100",
            working_hours_start="08:00",
            working_hours_end="18:00",
        )
        db.add(settings)
        db.commit()

    _create_task(client, "Weekend Task 2", deadline)
    _plan(client, plan_date)
