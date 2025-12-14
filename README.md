# OptimaTime AI

A research-flavored daily planner that blends learning-to-rank prioritization, temporal features, online feedback, and local search optimization.

## Highlights
- FastAPI backend with versioned routing (`/api/v1`), JWT auth, and env-based settings.
- Gradient Boosting "priority brain" trained on synthetic expert labels with temporal/user context.
- Feedback logging to nudge the model per user (+1 earlier, -1 later).
- Greedy + local-improvement scheduler with explainability hooks.
- Modern React/Vite UI with schedule feedback buttons and a futuristic theme.

## Backend setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --reload
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
- `POST /api/v1/auth/signup` → returns JWT + user
- `POST /api/v1/auth/login` → returns JWT + user (password optional)
- `GET/POST /api/v1/tasks` → list/create tasks (auth required)
- `POST /api/v1/planning/plan` → generate schedule for a given date
- `GET/POST /api/v1/feedback` → capture user schedule feedback
