from datetime import datetime, timedelta
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal
from .models import User

security = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


def _require_jwt_secret() -> str:
    secret = settings.jwt_secret
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="JWT_SECRET is not configured",
        )
    return secret


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _create_token(data: dict, expires_minutes: int) -> str:
    secret = _require_jwt_secret()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=expires_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=settings.jwt_algorithm)


def create_access_token(user: User) -> str:
    return _create_token(
        {
            "sub": str(user.id),
            "email": user.email,
            "profile": user.profile.value,
            "type": "access",
            "tv": user.token_version,
        },
        settings.access_token_expire_minutes,
    )


def create_refresh_token(user: User) -> str:
    return _create_token(
        {"sub": str(user.id), "type": "refresh", "tv": user.token_version},
        settings.refresh_token_expire_minutes,
    )


def _decode_token(token: str) -> dict:
    secret = _require_jwt_secret()
    try:
        return jwt.decode(token, secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        logger.exception("JWT decode failed")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    token = credentials.credentials
    payload = _decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    user_id = payload.get("sub")
    token_version = payload.get("tv")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = db.get(User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if token_version is None or token_version != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return user
