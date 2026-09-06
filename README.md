# RehabBuddy

An educational telerehabilitation prototype. Patients perform exercises in front of their
camera, the browser tracks body pose and counts reps, a Python backend computes movement
metrics from the joint data, and an LLM drafts a summary for the doctor to review.

This is a portfolio project. It is not a clinical system and must not be used with real patients.

## Run locally

Requirements: Docker, Python 3.12, Node 20+.

```bash
docker compose up -d
cd backend && python3.12 -m venv .venv && source .venv/bin/activate && pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
python -m app.seed.run
uvicorn app.main:app --reload
```

In another terminal:

```bash
cd frontend && npm install && cp .env.example .env && npm run dev
```

Open http://localhost:5173. Demo logins (password `demo1234`):

- Doctor: `doctor@rehabbuddy.dev`
- Patients: `patient1@rehabbuddy.dev`, `patient2@rehabbuddy.dev`, `patient3@rehabbuddy.dev`

## Tests

```bash
cd backend && pytest
cd frontend && npm test
```

## Layout

- `backend/` FastAPI API, analyzer, AI summary service
- `frontend/` React app for patients and doctors
- `shared/` exercise definitions and test fixtures read by both sides
- `docs/superpowers/` design spec and implementation plans
