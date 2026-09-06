from sqlalchemy import func, select

from app.core.security import verify_password
from app.models import DoctorPatient, Exercise, User
from app.seed.run import seed


def test_seed_creates_demo_users_and_catalog(db):
    seed(db)
    doctor = db.scalar(select(User).where(User.email == "doctor@rehabbuddy.dev"))
    assert doctor is not None and doctor.role == "doctor"
    assert verify_password("demo1234", doctor.password_hash)
    patients = db.scalars(select(User).where(User.role == "patient")).all()
    assert {p.email for p in patients} == {f"patient{i}@rehabbuddy.dev" for i in (1, 2, 3)}
    assert db.scalar(select(func.count()).select_from(DoctorPatient).where(DoctorPatient.doctor_id == doctor.id)) == 3
    assert db.scalar(select(Exercise).where(Exercise.id == "squat")) is not None


def test_seed_is_idempotent(db):
    seed(db)
    seed(db)
    assert db.scalar(select(func.count()).select_from(User)) == 4
    assert db.scalar(select(func.count()).select_from(Exercise)) == 1
