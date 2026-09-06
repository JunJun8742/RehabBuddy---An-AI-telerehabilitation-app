import uuid

from sqlalchemy import select

from app.models import (
    AiSummary,
    ClinicalNote,
    DoctorPatient,
    Exercise,
    ExerciseSession,
    Plan,
    PlanItem,
    SessionAnalysis,
    SessionLandmarks,
    User,
)


def test_full_graph_round_trips(db):
    doctor = User(email="d@x.dev", password_hash="h", role="doctor", display_name="Dr")
    patient = User(email="p@x.dev", password_hash="h", role="patient", display_name="Pat")
    db.add_all([doctor, patient])
    db.flush()
    db.add(DoctorPatient(doctor_id=doctor.id, patient_id=patient.id))
    db.add(Exercise(id="squat", name="Squat", description="d", camera_view="side"))
    plan = Plan(patient_id=patient.id, doctor_id=doctor.id, active=True)
    db.add(plan)
    db.flush()
    item = PlanItem(plan_id=plan.id, exercise_id="squat", sets=3, reps=10, days_per_week=3)
    db.add(item)
    db.flush()
    session = ExerciseSession(
        patient_id=patient.id, exercise_id="squat", plan_item_id=item.id,
        client_rep_count=9, client_reps=[], status="uploaded",
    )
    db.add(session)
    db.flush()
    db.add(SessionLandmarks(session_id=session.id, fps=30, data=[[[0.1, 0.2, 0.0, 0.9]] * 33]))
    db.add(SessionAnalysis(
        session_id=session.id, analyzer_version="0.1.0", rep_count=9, rep_count_mismatch=False,
        mean_rom=80.0, best_rom=85.0, form_consistency=100.0, symmetry=0.95, rom_trend_slope=-0.3,
        valid_frame_ratio=0.98, mean_visibility=0.9, fps=30, paused_seconds=0.0, low_quality=False,
        per_rep=[], violations=[], flags=[],
    ))
    db.add(AiSummary(session_id=session.id, patient_id=patient.id, kind="session", status="pending",
                     content=None, model=None, prompt_version=None))
    db.add(ClinicalNote(patient_id=patient.id, doctor_id=doctor.id, body="note"))
    db.commit()

    loaded = db.scalar(select(ExerciseSession).where(ExerciseSession.id == session.id))
    assert loaded is not None
    assert isinstance(loaded.id, uuid.UUID)
    assert loaded.created_at is not None
    assert db.scalar(select(SessionAnalysis).where(SessionAnalysis.session_id == session.id)).rep_count == 9


def test_only_one_active_plan_per_patient(db):
    import pytest
    from sqlalchemy.exc import IntegrityError

    doctor = User(email="d2@x.dev", password_hash="h", role="doctor", display_name="Dr")
    patient = User(email="p2@x.dev", password_hash="h", role="patient", display_name="Pat")
    db.add_all([doctor, patient])
    db.flush()
    db.add(Plan(patient_id=patient.id, doctor_id=doctor.id, active=True))
    db.flush()
    db.add(Plan(patient_id=patient.id, doctor_id=doctor.id, active=True))
    with pytest.raises(IntegrityError):
        db.flush()
