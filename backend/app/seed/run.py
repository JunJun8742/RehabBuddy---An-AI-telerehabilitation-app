"""Seed demo users and the exercise catalog. Idempotent. Run: python -m app.seed.run"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import SessionLocal
from app.core.exercise_library import load_exercise_library
from app.core.security import hash_password
from app.models import DoctorPatient, Exercise, User

DEMO_PASSWORD = "demo1234"
DOCTOR_EMAIL = "doctor@rehabbuddy.dev"
PATIENT_EMAILS = [f"patient{i}@rehabbuddy.dev" for i in (1, 2, 3)]
PATIENT_NAMES = ["Alex Rivera", "Sam Chen", "Jordan Okafor"]


def _get_or_create_user(db: Session, email: str, role: str, display_name: str) -> User:
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, password_hash=hash_password(DEMO_PASSWORD), role=role, display_name=display_name)
        db.add(user)
        db.flush()
    return user


def seed(db: Session) -> None:
    doctor = _get_or_create_user(db, DOCTOR_EMAIL, "doctor", "Dr. Maya Patel")
    for email, name in zip(PATIENT_EMAILS, PATIENT_NAMES):
        patient = _get_or_create_user(db, email, "patient", name)
        link = db.get(DoctorPatient, (doctor.id, patient.id))
        if link is None:
            db.add(DoctorPatient(doctor_id=doctor.id, patient_id=patient.id))

    for definition in load_exercise_library().values():
        if db.get(Exercise, definition.id) is None:
            db.add(
                Exercise(
                    id=definition.id,
                    name=definition.name,
                    description=definition.description,
                    camera_view=definition.camera_view,
                    illustration_url=f"/illustrations/{definition.illustration}",
                )
            )
    db.commit()


if __name__ == "__main__":
    with SessionLocal() as session:
        seed(session)
    print("Seeded demo doctor, three patients, and the exercise catalog.")
