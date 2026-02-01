# OptimaTime AI

A task planner that combines a small ML scoring model with heuristic scheduling rules to propose daily schedules.

## Highlights
- FastAPI backend with JWT auth, Alembic migrations, and a REST API.
- GradientBoostingRegressor trained on synthetic data to score tasks by duration, deadline, importance, profile, and preferences.
- Heuristic scheduler that assigns 30-minute slots using deadline/time-window/energy penalties, plus a small local adjustment pass.
- Feedback logging that biases future scheduling decisions (no online retraining).
- React/Vite UI for tasks, plans, and feedback.

## What it is / What it isn't
- What it is: A lightweight, ML-assisted planner that scores tasks and schedules them with explicit rules and constraints.
- What it is: A deterministic (seeded) planner over 30-minute slots with template-based explanations.
- What it isn't: A formal optimizer (no MILP/CP-SAT) or guaranteed optimal scheduler.
- What it isn't: An online learning system; feedback only adds runtime bias and does not retrain the model.
- What it isn't: An LLM-based planner; explanations are generated from rules and feature importance labels.

## Limitations
- The priority model is trained on synthetic data and may not reflect real user preferences without retraining.
- Scheduling is heuristic and greedy, so it can leave tasks unscheduled or place them suboptimally.
- Time is discretized into 30-minute slots; very short or irregular tasks are approximated.
- Refresh cookies are always marked Secure in code, so local HTTP refresh may not work without HTTPS.

## Reproducibility
- Backend deps: `pip install -r backend/requirements.txt` (no vendored dependencies in the repo).
- Frontend deps: `npm install` using `frontend/package.json` and `frontend/package-lock.json`.
- Configure env: copy `backend/.env.example` to `backend/.env` and set `JWT_SECRET`.
- If the model artifact is missing, regenerate with `python backend/ml/train_priority_model.py`.
- Run migrations: `python -m alembic upgrade head`.

## Local setup (dev)
- Copy `backend/.env.example` to `backend/.env` and set `JWT_SECRET` (64+ chars).
- Set `DATABASE_URL=sqlite:///./optimatime.db` in `backend/.env`.
- Optional reset: delete `optimatime.db` to start clean.
- Run migrations (use venv python): `python -m alembic upgrade head`.
- Start backend: `python -m uvicorn backend.app:app --reload`.
- Start frontend: `cd frontend && npm install && npm run dev`.
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
- `POST /api/v1/auth/login` -> returns JWT + user
- `GET/POST /api/v1/tasks` -> list/create tasks (auth required)
- `POST /api/v1/planning/plan` -> generate schedule for a given date
- `GET/POST /api/v1/feedback` -> capture user schedule feedback
