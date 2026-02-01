from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def _warn_missing_jwt_secret() -> None:
    if not os.getenv("JWT_SECRET"):
        print("WARNING: JWT_SECRET is not set; auth endpoints will fail.")


def _ensure_sqlite_db(db_url: str, repo_root: Path) -> None:
    if not db_url.startswith("sqlite:///"):
        return

    path_str = db_url[len("sqlite:///"):]
    if not path_str or path_str.startswith(":memory:"):
        return

    db_path = Path(path_str)
    if not db_path.is_absolute():
        db_path = (repo_root / db_path).resolve()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        db_path.touch()


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(repo_root))

    _warn_missing_jwt_secret()

    from backend.app import app  # noqa: F401
    from backend.config import settings

    _ensure_sqlite_db(settings.database_url, repo_root)

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=str(repo_root),
        check=True,
    )

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
