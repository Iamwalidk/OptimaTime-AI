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
- Refresh cookies default to Secure; set `REFRESH_COOKIE_SECURE=false` in `backend/.env` for local HTTP.

## Reproducibility
- Backend deps: `pip install -r requirements.txt` (no vendored dependencies in the repo).
- Frontend deps: `npm install` using `frontend/package.json` and `frontend/package-lock.json`.
- Configure env: copy `backend/.env.example` to `backend/.env` and set `JWT_SECRET`.
- Database default: `optimatime.db` in the project root (set `DATABASE_URL` to override).
- If the model artifact is missing, it will auto-train on first use (or run `python backend/ml/train_priority_model.py`).
- Run migrations: `python -m alembic upgrade head`.

## Local setup (dev)
- Copy `backend/.env.example` to `backend/.env` and set `JWT_SECRET` (64+ chars).
- Optional reset: delete `optimatime.db` in the project root to start clean.
- Run migrations (use venv python): `python -m alembic upgrade head`.
- Start backend: `python -m uvicorn backend.app:app --reload`.
- Start frontend: `cd frontend && npm install && npm run dev`.
- Open `http://localhost:8000/api/docs` for a quick API check.
- Optional: rebuild the priority model with `python backend/ml/train_priority_model.py`.

## Windows quickstart (PowerShell)
Backend:
```powershell
cd <project_root>
py -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m alembic upgrade head
python -m uvicorn backend.app:app --reload
```

Frontend:
```powershell
cd frontend
npm install
npm run dev
```
Node.js LTS (20/22) recommended if Node 24 causes issues.

## Backend setup
```bash
python -m venv .venv
# Windows (cmd): .venv\Scripts\activate
# Windows (PowerShell): .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m alembic upgrade head
python backend\ml\train_priority_model.py
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

## Manual verification checklist (Windows)
Auth correctness:
1) In a private/incognito window, open `http://localhost:5173`.
2) Attempt login with a valid email and a wrong password.
3) Confirm you see “Invalid credentials” and remain on the login screen (no sidebar/tools).
4) Open DevTools > Application > Cookies for `http://localhost:8000` and confirm no new `refresh_token` cookie was set.
5) Login with the correct password and confirm the app shell renders.
6) Test in normal window where you were logged in: try login with wrong password -> should log you out.

UI:
1) Open the Tools sidebar on mobile width (or narrow the window).
2) Confirm there is only one close icon (the regular X in the panel header).

## API (v1)
- `POST /api/v1/auth/signup` -> returns JWT + user
- `POST /api/v1/auth/login` -> returns JWT + user
- `GET/POST /api/v1/tasks` -> list/create tasks (auth required)
- `POST /api/v1/planning/plan` -> generate schedule for a given date
- `GET/POST /api/v1/feedback` -> capture user schedule feedback
