# OptimaTime AI

A research-flavored daily planner that blends learning-to-rank prioritization, temporal features, online feedback, and local search optimization.

## Highlights
- FastAPI backend with versioned routing (`/api/v1`), JWT auth, and env-based settings.
- Gradient Boosting "priority brain" trained on synthetic expert labels with temporal/user context.
- Feedback logging to nudge the model per user (+1 earlier, -1 later).
- Greedy + local-improvement scheduler with explainability hooks.
- Modern React/Vite UI with schedule feedback buttons and a futuristic theme.

## Local setup (dev)
- Copy `backend/.env.example` to `backend/.env` and set `JWT_SECRET` (64+ chars).
- For local HTTP, keep `REFRESH_COOKIE_SECURE=false` (already in `.env.example`).
- Set `DATABASE_URL=sqlite:///./optimatime.db` in `backend/.env`.
- Optional reset: delete `optimatime.db` to start clean.
- Run migrations (use venv python): `python -m alembic upgrade head`.
- Migrations do not require `JWT_SECRET`, but the app/auth endpoints do.
- Start backend: `python -m uvicorn backend.app:app --reload`.
- Start frontend: `cd frontend && npm install && npm run dev`.
- Optional: `cd frontend && npm audit` (or `npm audit fix`).
- Open `http://localhost:8000/api/docs` for a quick API check.
- Optional: rebuild the priority model with `python backend/ml/train_priority_model.py`.

## Backend setup
```bash
python -m venv .venv
# Windows (cmd): .venv\Scripts\activate
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m alembic upgrade head
python -m uvicorn backend.app:app --reload
```
Backend runs on http://localhost:8000

## Frontend setup
```bash
cd frontend
npm install
npm run dev
```
Frontend runs on http://localhost:5173

## API (v1)
- `POST /api/v1/auth/signup` -> returns JWT + user
- `POST /api/v1/auth/login` -> returns JWT + user (password optional)
- `GET/POST /api/v1/tasks` -> list/create tasks (auth required)
- `POST /api/v1/planning/plan` -> generate schedule for a given date
- `GET/POST /api/v1/feedback` -> capture user schedule feedback
