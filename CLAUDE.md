# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

RehabBuddy is an educational telerehabilitation prototype (portfolio project, not for real clinical use). Patients perform exercises in front of a camera; the browser tracks body pose and counts reps; a Python backend recomputes movement metrics from the joint data; an LLM (Claude) drafts a plain-language summary and suggested next steps for a doctor to review and apply. See `docs/superpowers/specs/2026-09-06-rehabbuddy-design.md` for the full design — it is the authority the plans argue from; check it before making an architectural decision the code doesn't already answer.

**Current status:** only Phase 1 (Foundation) is built — see `docs/superpowers/plans/2026-09-06-01-foundation.md`. That covers auth, the full data model, the exercise-definition library (squat only so far), the `/exercises` endpoint, the seed script, and a frontend shell with role-routed placeholder pages. There is **no camera/pose tracking, no session upload/analysis, no dashboard, and no AI summary code yet** — those are Phases 2–8 in the spec's Section 10, not yet planned or built. Don't assume functionality beyond what's actually in `backend/app/` and `frontend/src/`.

## Commands

### Backend (Python 3.12, FastAPI)

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env          # point at a running Postgres (see below)
alembic upgrade head
python -m app.seed.run        # idempotent — creates demo doctor/patients + exercise catalog
uvicorn app.main:app --reload
```

Requires PostgreSQL 16 reachable at `DATABASE_URL`/`TEST_DATABASE_URL` in `.env` — either `docker compose up -d` (see root `docker-compose.yml`, creates both `rehabbuddy` and `rehabbuddy_test` databases via `docker/init-test-db.sql`) or a native install with a `rehab`/`rehab` role that owns both databases.

```bash
pytest                                          # full suite
pytest tests/test_auth.py -v                    # one file
pytest tests/test_auth.py::test_login_returns_token_for_valid_credentials -v   # one test
alembic revision --autogenerate -m "message"    # after changing a model
```

Tests run against the real `rehabbuddy_test` Postgres database (not SQLite, not mocks) — the `db` fixture in `tests/conftest.py` wraps each test in an outer transaction plus a savepoint (`join_transaction_mode="create_savepoint"`) and rolls back afterward, so tests never leave rows behind even if the code under test calls `commit()`. The `engine` fixture drops and recreates all tables once per test session via `Base.metadata.create_all` — it does not run Alembic migrations, so a model change is visible to tests immediately but still needs a migration for the dev database.

### Frontend (React 19, Vite 8, TypeScript 6, Node 20+)

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_URL, defaults to http://localhost:8000/api/v1
npm run dev               # http://localhost:5173
npm test                  # vitest run — all tests
npx vitest run src/routes.test.tsx     # one file
npx tsc --noEmit -p tsconfig.app.json  # type-check only
npm run build              # tsc -b + vite build — also type-checks vite.config.ts
npm run lint               # oxlint
```

Demo logins (password `demo1234` for all): `doctor@rehabbuddy.dev`, `patient1@rehabbuddy.dev`, `patient2@rehabbuddy.dev`, `patient3@rehabbuddy.dev`.

**Toolchain note:** this scaffold ended up on newer majors than a typical tutorial assumes (Vite 8 / TypeScript 6 / React 19, not Vite 5 / TS 5 / React 18). Two things that bit us once and can again: TypeScript 6 runs with `erasableSyntaxOnly`, which rejects `enum`, `namespace`, and constructor parameter-property shorthand — use plain types/interfaces and explicit field assignment instead. And vitest's `test:` config block must live in its own `vitest.config.ts` (merged via `mergeConfig`), not inline in `vite.config.ts` — vitest 2's type augmentation for that key doesn't match Vite 8's `defineConfig` overloads and silently breaks `npm run build` (this is why `vite.config.ts` and `vitest.config.ts` are separate files, not one).

## Architecture

**The exercise-definition JSON files under `shared/exercises/*.json` are the single source of truth for rep-detection and form-check rules — not the `exercises` database table, which is only a display catalog (name/description/illustration).** Both the backend (`app/core/exercise_library.py`, validated by the Pydantic model in `app/schemas/exercise.py`) and the eventual frontend rep counter are meant to read the same JSON. The rep-threshold block in that JSON is named `detection`, not `rep` — this is deliberate (the spec is explicit that these are algorithmic thresholds, not clinical targets) and `ExerciseDefinition` uses `extra="forbid"`, so a legacy `rep` key fails validation rather than being silently ignored. Landmark names in a definition (`required_landmarks`, angle `points`) are validated against the keys in `shared/landmarks.json`, the MediaPipe Pose landmark-name-to-index lookup.

**Auth is JWT bearer, role is server-side only.** `POST /auth/register` always creates a `patient` — there is no way to self-register as a doctor; doctors only exist via the seed script. The JWT payload is `{sub: <user uuid as str>, role, exp}`; `app/core/deps.py`'s `get_current_user` re-fetches the user row by id on every request (so a role change takes effect immediately, not just on next login) and `require_role(role)` 403s on mismatch. Ownership (a doctor may only see their assigned patients, a patient only their own data) is enforced server-side via the `doctor_patients` join table — the frontend's route guards (`RequireRole`/`RoleHome` in `frontend/src/routes.tsx`) are a UX convenience, never the security boundary.

**Data model naming is intentionally not the "obvious" name in a few places** (per the design spec, so keep these when extending `session_analysis` in later phases): `form_consistency` not `form_score` (it's a percentage of clean reps, not a quality score), `rom_trend_slope` not `fatigue_slope` (a descriptive trend, not a diagnosed cause), `symmetry` as `min(left,right)/max(left,right)` in `[0,1]`. `plans` has a partial unique index (`postgresql_where=text("active")` on `patient_id`) enforcing one active plan per patient — it lives in the model's `__table_args__` (so it applies to the test suite's `Base.metadata.create_all`) *and* must appear in the Alembic migration; if you regenerate the migration and it's missing from the autogenerated diff, add it by hand.

**Backend package layout:** `app/core/` (config, db session, security/JWT, auth dependencies, exercise-library loader) → `app/models/` (SQLAlchemy ORM, one file per entity group) → `app/schemas/` (Pydantic request/response + the exercise-definition schema) → `app/api/` (routers, one per resource, aggregated in `app/api/router.py` under `/api/v1`) → `app/seed/` (idempotent demo-data script, safe to run repeatedly).
