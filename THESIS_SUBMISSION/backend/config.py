from pathlib import Path
from typing import List, Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DEFAULT_DB_PATH = (PROJECT_ROOT / "optimatime.db").resolve()


class Settings(BaseSettings):
    app_name: str = "OptimaTime AI"
    version: str = "1.0.0"
    database_url: str = Field(f"sqlite:///{DEFAULT_DB_PATH.as_posix()}", alias="DATABASE_URL")
    backend_cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    jwt_secret: Optional[str] = Field(None, alias="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7
    refresh_cookie_secure: bool = Field(True, alias="REFRESH_COOKIE_SECURE")

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
