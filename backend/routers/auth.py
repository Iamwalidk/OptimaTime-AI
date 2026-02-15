from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .. import models, schemas
from ..dependencies import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_db,
    _decode_token,
)
from ..config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

# pbkdf2_sha256 avoids bcrypt backend issues on Windows; strong enough for thesis scope.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

REFRESH_COOKIE_NAME = "refresh_token"


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_expire_minutes * 60,
        path="/",
    )


def _clear_refresh_cookie(response: Response):
    response.delete_cookie(REFRESH_COOKIE_NAME, path="/")


def _auth_response(user: models.User, response: Response) -> schemas.AuthResponse:
    access_token = create_access_token(user)
    refresh_token = create_refresh_token(user)
    _set_refresh_cookie(response, refresh_token)
    return schemas.AuthResponse(access_token=access_token, user=user)


@router.post("/signup", response_model=schemas.AuthResponse)
def signup(user_in: schemas.UserCreate, response: Response, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == user_in.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = models.User(
        email=user_in.email,
        name=user_in.name,
        profile=user_in.profile,
        hashed_password=_hash_password(user_in.password),
    )
    db.add(user)
    db.flush()
    db.add(
        models.UserSettings(
            user_id=user.id,
        )
    )
    db.commit()
    db.refresh(user)
    return _auth_response(user, response)


@router.post("/login", response_model=schemas.AuthResponse)
def login(login_req: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == login_req.email).first()
    if not user or not _verify_password(login_req.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive account")
    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return _auth_response(user, response)


@router.post("/refresh", response_model=schemas.AuthResponse)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")

    payload = _decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    user_id = payload.get("sub")
    token_version = payload.get("tv")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(models.User, int(user_id))
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if token_version is None or token_version != user.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    # rotate refresh token and issue new access
    auth = _auth_response(user, response)
    return auth


@router.post("/logout")
def logout(response: Response, db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    user.token_version += 1  # invalidate old refresh tokens
    db.commit()
    _clear_refresh_cookie(response)
    return {"detail": "Logged out"}
