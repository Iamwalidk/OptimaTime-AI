# Release Checklist (Source-Only)

Include these paths:
- README.md
- alembic/
- alembic.ini
- backend/ (source only; includes backend/.env.example)
- frontend/ (source only)
- scripts/
- RELEASE_CHECKLIST.md
- .gitignore

Do NOT include:
- backend/.env or any other .env files
- optimatime.db or any *.db files
- __pycache__/ or *.pyc
- .venv/ or venv/
- frontend/node_modules/
- frontend/dist/
- .git/

Notes:
- Use scripts/make_release_zip.ps1 to package tracked files only.
- Commit or stage changes before packaging to ensure all sources are included.
