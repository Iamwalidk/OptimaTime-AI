import pytest
try:
    from fastapi.testclient import TestClient
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    TestClient = None
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app import app
from backend.database import Base
from backend.dependencies import get_db
from backend import models
from backend.routers.auth import _hash_password

if TestClient is None:
    pytest.skip("fastapi TestClient requires requests", allow_module_level=True)


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
            hashed_password=_hash_password("correct-password"),
            is_active=True,
            token_version=0,
        )
        db.add(user)
        db.commit()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield client

    app.dependency_overrides.clear()


def test_login_rejects_wrong_password_and_sets_no_cookie(client_env):
    client = client_env
    res = client.post("/api/v1/auth/login", json={"email": "user@example.com", "password": "wrong-password"})
    assert res.status_code == 401
    assert "access_token" not in res.json()
    set_cookie = res.headers.get("set-cookie", "").lower()
    assert "refresh_token" not in set_cookie
