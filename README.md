# OptimaTime AI  
**Hybrid ML-Assisted Task Scheduling System**

OptimaTime AI is a lightweight intelligent planner that combines machine learning–based task prioritization with a deterministic heuristic scheduling engine.

The system separates statistical learning (priority estimation) from rule-based optimization (time allocation) to ensure modularity, interpretability, and reproducibility.

---

## Architecture

React Frontend → FastAPI Backend → ML Priority Model → Heuristic Scheduler → SQLite Database

**Tech Stack**
- Python, FastAPI
- Scikit-learn (GradientBoostingRegressor)
- SQLite + Alembic migrations
- JWT authentication
- React + Vite

---

## ML Pipeline

**Feature Engineering**
- Task duration
- Deadline proximity
- Importance level
- User profile encoding
- Preference-weighted signals

**Model**
- GradientBoostingRegressor (Scikit-learn)
- Trained on structured synthetic dataset
- Seeded for reproducibility

**Output**
- Continuous priority score
- Used as input to the deterministic scheduling engine

---

## Scheduling Engine

- 30-minute discrete time slots
- Deadline penalties
- Time window constraints
- Energy-level penalties
- Conflict detection
- Small local adjustment pass

The scheduler is heuristic and deterministic — not a formal optimizer (no MILP / CP-SAT).

---

## Engineering Decisions

- Chose heuristic scheduling over MILP to keep the system lightweight and explainable.
- Separated ML scoring from scheduling logic to preserve modularity.
- Used synthetic data for controlled experimentation prior to real user data collection.
- Designed the system as a hybrid approach: statistical learning + rule-based allocation.

---

## Limitations

- The ML model is trained on synthetic data.
- Scheduling is greedy and may produce suboptimal plans.
- No online retraining (feedback biases runtime only).
- Time resolution fixed to 30-minute slots.

---

## Future Directions

- Replace synthetic training data with anonymized real usage data.
- Explore ranking-based models instead of regression.
- Add feature importance visualization.
- Compare heuristic scheduling with MILP baseline.
- Experiment with reinforcement learning for adaptive scheduling.

---

## Local Setup

### Backend
```bash
python -m venv .venv
# Activate environment (Windows)
.venv\Scripts\activate
# macOS/Linux
# source .venv/bin/activate

pip install -r backend/requirements.txt
python -m alembic upgrade head
python -m uvicorn backend.app:app --reload

Backend runs at:
http://localhost:8000

Swagger docs:
http://localhost:8000/api/docs


### Frontend

cd frontend
npm install
npm run dev

Frontend runs at:
http://localhost:5173

### API (v1)

POST /api/v1/auth/signup

POST /api/v1/auth/login

GET/POST /api/v1/tasks

POST /api/v1/planning/plan

GET/POST /api/v1/feedback