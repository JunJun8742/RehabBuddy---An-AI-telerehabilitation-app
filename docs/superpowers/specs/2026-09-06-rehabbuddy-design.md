# RehabBuddy Design Spec

Date: 2026-09-06
Status: Approved for planning

## 1. Purpose and scope

RehabBuddy is a telerehabilitation web app. Patients perform prescribed exercises in front of their laptop or phone camera. The browser tracks their body pose in real time, counts reps, and gives live form cues. After the session, a Python backend computes clinical metrics from the recorded joint data and an LLM drafts a plain-language summary and next-step suggestions for the doctor. The doctor reviews progress on a dashboard and adjusts the patient's plan.

This is a portfolio and learning project. It is not intended for real clinical use, so HIPAA-grade controls are out of scope. The design still avoids storing video and keeps the record of truth on the server, which is good engineering regardless.

### In scope for v1

- Email and password auth with two roles: `doctor` and `patient`.
- Live camera session with pose overlay, rep counting, form cues, and a session recap.
- Five hand-tuned exercises with per-exercise rules.
- Server-side analysis of uploaded landmark timeseries.
- LLM-generated session summary, progress note, concerns, and structured next-step suggestions.
- Doctor dashboard: patient list, per-patient charts, session review, plan editor, clinical notes.
- Patient history view.
- Seed data: one demo doctor and three demo patients with several weeks of history.

### Out of scope for v1

- Video recording or storage.
- Real-time video calls between doctor and patient.
- Native mobile apps.
- Messaging, notifications, email reminders, password reset.
- Exercise video tutorials (a static illustration per exercise is sufficient).
- Multi-clinic tenancy, HIPAA controls, audit logs.
- Automatic plan changes without doctor confirmation.

## 2. Architecture

Pose estimation runs entirely in the browser. Only landmark data, never video, leaves the device. The server recomputes all metrics from the landmarks so the browser's live counts are a preview and the server's result is the record.

```
Patient browser                          FastAPI backend                 Claude API
+------------------------+   landmarks   +---------------------------+
| MediaPipe Pose (WebGL) | ------------> | Analyzer (NumPy/pandas)   |
| angle math             |   (JSON,      | -> session_analysis       |
| rep state machine      |    ~100KB     | Summary service           | --------> claude-opus-5
| form rules             |    gzipped)   | -> ai_summaries           | <-------- structured JSON
| session buffer         |               | REST API + auth           |
+------------------------+               +---------------------------+
                                                     |
Doctor browser                                       v
+------------------------+   REST        +---------------------------+
| dashboard, charts,     | <-----------> | PostgreSQL                |
| session review,        |               | (JSONB for landmarks,     |
| plan editor            |               |  per-rep data, summaries) |
+------------------------+               +---------------------------+
```

### Stack

Frontend
- React 18 with TypeScript, built with Vite.
- `@mediapipe/tasks-vision` Pose Landmarker running on WebGL.
- Tailwind CSS with shadcn/ui components.
- Recharts for progress charts.
- TanStack Query for server state. No global state library.
- React Router for role-based routing.

Backend
- Python 3.12, FastAPI, Pydantic v2.
- SQLAlchemy 2 with Alembic migrations.
- NumPy and pandas for the analyzer.
- `anthropic` Python SDK for summaries. The implementer must follow the `claude-api` skill's Python README for SDK usage rather than recalled patterns.
- JWT auth with `python-jose` or equivalent, passwords hashed with bcrypt.
- FastAPI `BackgroundTasks` for the summary job. No task queue in v1.

Infrastructure
- PostgreSQL 16.
- Docker Compose for local development (Postgres plus optional backend container).
- Deploy targets: frontend on Vercel, backend on Railway or Render, Postgres on Neon or Supabase. All free tier.

### Repository layout

```
rehabbuddy/
  frontend/          React app
  backend/           FastAPI app
    app/
      api/           routers
      core/          config, auth, db
      models/        SQLAlchemy models
      schemas/       Pydantic schemas
      analysis/      angle math, rep detection, metrics, flags
      ai/            prompt builder, Claude client, output schema
      seed/          demo data generator
    tests/
    alembic/
  shared/
    exercises/       one JSON definition per exercise
    fixtures/        recorded landmark sessions used by both test suites
  docs/superpowers/  specs and plans
  docker-compose.yml
  README.md
```

The `shared/exercises` folder is read by both the frontend (bundled at build time) and the backend (loaded at startup). It is the single source of truth for exercise rules.

## 3. Users, roles, and features

### Auth and roles

- `users` carry a `role` of `doctor` or `patient`.
- Doctors see only patients assigned to them through `doctor_patients`.
- Patients see only their own data.
- All routes enforce role and ownership checks on the server. The frontend hides UI it should not show but is not the security boundary.

### Patient features

- Home: today's assigned exercises with target sets and reps, completion state, and a streak counter.
- Exercise session: camera preview with skeleton overlay, a "get in frame" calibration step, live rep counter, form cue banner, set and rest timers, and an end-of-session recap (reps, best range of motion, form score).
- History: list of past sessions with per-exercise trend charts.

### Doctor features

- Patient list with a status chip per patient: `on_track`, `missed_sessions`, or `flagged`.
- Patient detail: range of motion and form score charts over time per exercise, an adherence calendar, and a session list.
- Session review: per-rep breakdown table, AI summary, concerns, and suggested next steps.
- Plan editor: assign exercises from the library with sets, reps, and days per week. AI suggestions can be applied to the plan in one click, then edited. Nothing changes without the doctor saving.
- Clinical notes: free-text notes per patient, stored separately from AI output.

### AI features

- Session summary generated after each upload and cached.
- Progress narrative over the last five sessions per exercise, regenerated when a new session lands.
- Flags are computed deterministically by the analyzer. The LLM explains them but does not invent them.

## 4. Exercise definitions and the pose pipeline

### Exercise set

| id | Name | Primary angle | Camera view | Rep pattern |
|---|---|---|---|---|
| `squat` | Bodyweight squat | Knee flexion (hip, knee, ankle) | side | Standing, knee angle drops below 100 degrees, returns above 160 |
| `sit_to_stand` | Sit-to-stand | Knee flexion plus torso lean | side | Seated, rise to standing (knee above 160), return to seated |
| `shoulder_abduction` | Shoulder abduction | Shoulder angle vs torso, lateral | front | Arm raised sideways past 80 degrees, lowered below 20 |
| `front_arm_raise` | Front arm raise | Shoulder flexion | side | Arm raised forward past 80 degrees, lowered below 20 |
| `knee_extension` | Seated knee extension | Knee flexion | side | Seated, knee straightened past 160, lowered below 100 |

Threshold numbers above are starting points and are tuned during implementation against the recorded fixtures. The definition file, not this spec, is authoritative once tuned.

### Exercise definition schema

Each file in `shared/exercises/<id>.json` contains:

```json
{
  "id": "squat",
  "name": "Bodyweight squat",
  "description": "...",
  "camera_view": "side",
  "side": "both",
  "required_landmarks": [23, 24, 25, 26, 27, 28, 11, 12],
  "angles": {
    "knee": { "points": ["hip", "knee", "ankle"] },
    "torso_lean": { "points": ["shoulder", "hip"], "reference": "vertical" }
  },
  "primary_angle": "knee",
  "rep": {
    "down_threshold": 100,
    "up_threshold": 160,
    "min_hold_frames": 3
  },
  "form_rules": [
    { "id": "torso_lean", "angle": "torso_lean", "max": 30, "frames": 5, "cue": "Keep your chest up" },
    { "id": "shallow_depth", "angle": "knee", "rep_min_must_be_below": 110, "cue": "Go a little deeper" }
  ],
  "illustration": "squat.svg"
}
```

Landmark names map to MediaPipe indices through a shared lookup. `side: "both"` means the analyzer evaluates left and right independently and reports a symmetry ratio.

### Live pipeline in the browser, per frame

1. Pose Landmarker returns 33 landmarks with x, y, z, and visibility.
2. Visibility gate: every landmark in `required_landmarks` must have visibility above 0.6. If not, counting pauses and the UI shows "step back into frame". Reps are never counted while paused.
3. Compute each angle in the definition using a small vector-math helper. Smooth each angle with a one-euro filter or exponential moving average to remove jitter.
4. Feed the smoothed primary angle into the rep state machine (`up` to `down` when below `down_threshold` for `min_hold_frames`, `down` to `up` when above `up_threshold`). Each completed rep emits an event with its min and max angle and frame range.
5. Evaluate form rules on each frame during the active phase of a rep. A rule violated for more than its `frames` threshold shows the cue and is recorded against that rep.
6. Push `{t, landmarks, angles}` into the session buffer.

### Session state machine (frontend)

`idle` -> `calibrating` -> `active` <-> `paused` -> `complete` -> `uploading` -> `uploaded` | `upload_failed`

### Upload payload

```json
{
  "exercise_id": "squat",
  "plan_item_id": "...",
  "started_at": "...",
  "ended_at": "...",
  "client_rep_count": 12,
  "client_reps": [{ "start_frame": 10, "end_frame": 55, "min_angle": 92.1, "max_angle": 171.0 }],
  "fps": 15,
  "landmarks": [[[x, y, z, v], ...33], ...frames]
}
```

Landmarks are downsampled to 15 fps and rounded to three decimals before upload. The frontend holds the payload in IndexedDB until the upload succeeds.

### Python analyzer

Runs synchronously on upload. Steps:

1. Validate payload shape (33 landmarks per frame, at least 15 frames).
2. Recompute all angles from raw landmarks. Apply the same smoothing as the frontend.
3. Run the rep state machine. This count is the record. The client count is stored for comparison only.
4. Per rep: peak range of motion, duration, concentric and eccentric time, smoothness (spectral arc length of the angle velocity), form rule violations.
5. Per session: rep count, mean and best range of motion, form score (0 to 100, equal to 100 times the fraction of reps with no form rule violations), symmetry ratio for `side: "both"` exercises, fatigue slope (linear fit of peak ROM across reps).
6. Per patient, comparing to history: delta versus the previous session and versus the first-session baseline for the same exercise.
7. Flags, all deterministic:
   - `rom_drop`: mean ROM at least 15% below baseline.
   - `form_low`: form score below 60.
   - `asymmetry`: symmetry ratio outside 0.8 to 1.2.
   - `missed_sessions`: three or more prescribed days missed in the last seven (computed by a separate adherence job when the patient list loads).
   - `rep_shortfall`: reps below 70% of prescribed.

The analyzer stores an `analyzer_version` so stored landmarks can be reprocessed later and compared.

## 5. Data model

PostgreSQL. Ids are UUIDs.

- `users`: id, email (unique), password_hash, role, display_name, created_at.
- `doctor_patients`: doctor_id, patient_id. Primary key on both.
- `exercises`: id (slug, matches the JSON file), name, description, camera_view, illustration_url. Catalog only. Rules live in the JSON.
- `plans`: id, patient_id, doctor_id, created_at, active. One active plan per patient, enforced by a partial unique index.
- `plan_items`: id, plan_id, exercise_id, sets, reps, days_per_week, notes.
- `sessions`: id, patient_id, exercise_id, plan_item_id (nullable), started_at, ended_at, client_rep_count, status (`uploaded`, `analyzed`, `failed`), failure_reason (nullable), created_at.
- `session_landmarks`: session_id (primary key), fps, data (JSONB). Separate table so list queries never load it.
- `session_analysis`: session_id (primary key), analyzer_version, rep_count, mean_rom, best_rom, form_score, symmetry (nullable), fatigue_slope, per_rep (JSONB), violations (JSONB), flags (JSONB array of codes), computed_at.
- `ai_summaries`: id, session_id (nullable), patient_id, kind (`session`, `progress`), status (`pending`, `ready`, `failed`), content (JSONB, the validated structured output), model, prompt_version, error (nullable), created_at.
- `clinical_notes`: id, patient_id, doctor_id, body, created_at.

Relationships: a session belongs to a patient and an exercise, has exactly one landmarks row and one analysis row once processed, and zero or one session summary. Progress summaries hang off the patient with a null session_id.

## 6. AI summary flow

### Trigger

After the analyzer stores `session_analysis`, the upload handler enqueues a FastAPI background task and returns. The task creates an `ai_summaries` row with status `pending`, calls Claude, and updates the row to `ready` or `failed`. The doctor's session page polls the summary endpoint every three seconds while it is pending.

### Prompt payload

The prompt never includes raw landmarks. It contains:

- System prompt: role and guardrails (below). Placed first and marked with a cache breakpoint.
- Exercise library in plain language: name, target, what good form looks like, for all five exercises. Placed inside the cached prefix.
- Current session metrics: everything in `session_analysis` except `per_rep`, plus a condensed per-rep table (rep number, peak ROM, violations).
- Last five sessions of the same exercise as a table of the same summary metrics.
- Current plan item (prescribed sets, reps, days per week).
- The most recent clinical note, if any.

### Output schema

Validated with structured outputs through `client.messages.parse()` and a Pydantic model:

```
SessionSummary
  summary: str                        3 to 5 sentences for the doctor
  progress_note: str                  1 to 2 sentences on trend vs history
  concerns: list[Concern]             may be empty
    flag_code: str                    must be one of the analyzer's flag codes present in the payload
    explanation: str
  suggested_next_steps: list[Suggestion]
    action: Literal["increase_reps", "decrease_reps", "add_exercise", "hold", "review_form", "contact_patient"]
    exercise_id: str
    sets: int | None
    reps: int | None
    rationale: str
```

The progress summary (`kind = progress`) uses a smaller schema: `narrative: str` and `trend: Literal["improving", "stable", "declining", "insufficient_data"]`.

### Model and request settings

- Model: `claude-opus-5`.
- Thinking: adaptive (default for this model), effort `low`.
- `max_tokens` around 2000.
- Prompt caching: `cache_control` breakpoint after the exercise library block.
- Each summary stores `model` and `prompt_version`. Prompt text lives in `backend/app/ai/prompts.py` with a version constant that must be bumped on any change.

### Guardrails in the system prompt

- You are drafting for a licensed clinician who makes all decisions.
- Do not diagnose.
- Reference only metrics and flags present in the payload. If a concern is outside the data, recommend `contact_patient` rather than inventing a clinical action.
- Use plain clinical language. No hedging filler.

### Failure handling

- API errors, timeouts, and schema validation failures mark the summary `failed` with the error text.
- The doctor UI shows metrics and charts regardless and offers a "regenerate summary" button that re-enqueues the task.
- If no API key is configured, the summary service is disabled and the UI hides the summary panel. All other features work.

## 7. API surface

All under `/api/v1`. JSON. Bearer JWT.

Auth
- `POST /auth/register` (role fixed to `patient` for self-registration; doctors are seeded or created by an admin script)
- `POST /auth/login`
- `GET /auth/me`

Exercises
- `GET /exercises` (catalog plus the full definition JSON)

Patients (doctor)
- `GET /patients` (assigned patients with status chip and last session date)
- `GET /patients/{id}` (profile, active plan, adherence, per-exercise summary stats)
- `GET /patients/{id}/sessions`
- `GET /patients/{id}/progress-summary`
- `GET|POST /patients/{id}/notes`

Plans (doctor)
- `GET /patients/{id}/plan`
- `PUT /patients/{id}/plan` (replaces the active plan and its items)

Sessions
- `POST /sessions` (patient upload, returns session id and analysis)
- `GET /sessions/{id}` (session, analysis, summary status)
- `GET /sessions/{id}/summary`
- `POST /sessions/{id}/summary/regenerate` (doctor)

Patient home
- `GET /me/today` (plan items for today with completion state)
- `GET /me/sessions`

Ownership rules: patients may only read their own sessions and plan. Doctors may only read patients in `doctor_patients`. Every handler checks this; tests cover both directions.

## 8. Error handling

- Camera permission denied or no camera: clear message with instructions, never a blank screen.
- Low frame rate (below 12 fps for 3 seconds): show a hint, keep working.
- Tracking loss: pause counting, amber frame border, "step back into frame". Reps never count while paused.
- Upload: payload held in IndexedDB until success. Retry with backoff three times, then a manual retry button. The session is only cleared from IndexedDB after a 2xx.
- Analyzer: malformed payloads are stored as `failed` with a reason. Never silently dropped.
- LLM: see Section 6.
- Auth: expired tokens redirect to login and preserve the return path.

## 9. Testing

- Python analyzer: the highest-value tests. Recorded landmark fixtures in `shared/fixtures/` per exercise (a clean set, a shallow set, a set with a form fault, a set with tracking dropout) with asserted rep counts, ROM ranges, and expected flags. Synthetic fixtures for zero reps, a single frame, and all-invisible landmarks.
- TypeScript angle math and rep state machine: unit tests using the same fixtures. Both suites read the same files, so the two implementations are checked against the same truth.
- API: pytest against a Dockerized Postgres. Auth, ownership in both directions, upload-to-analysis path, plan replacement.
- AI layer: prompt builder tested for payload shape and cache breakpoint placement without calling the API. One integration test hits the real API and validates the schema; skipped when no key is set.
- Frontend: component tests for the session state machine with a mocked pose source. No browser end-to-end tests in v1.

## 10. Build phases

Each phase ends in something demoable.

1. Foundation: monorepo, Docker Compose, FastAPI with auth and models, Alembic, React shell with login and role routing, seed script with users only.
2. Pose and rep counting: camera, MediaPipe, angle math, rep state machine, the squat end to end including upload and the Python analyzer with fixtures.
3. Exercise library: remaining four exercises, form rules, fixtures and tests for each.
4. Doctor dashboard: patient list, patient detail with charts, session review, plan editor, notes.
5. AI summaries: prompt builder, structured output, background task, regenerate flow, progress summary, flag explanations.
6. Polish and deploy: patient history, responsive pass, realistic seed history, deployment, README with screenshots and an architecture diagram.

## 11. Implementation notes

- The orchestrating session runs on Opus 4.8 at high effort. Subagent tasks run on Sonnet 5 at medium effort.
- Follow the `claude-api` skill's Python README when writing the summary service. Do not use recalled SDK patterns.
- Keep files small and single-purpose. The analyzer in particular should be split into `angles.py`, `smoothing.py`, `reps.py`, `metrics.py`, and `flags.py`.
