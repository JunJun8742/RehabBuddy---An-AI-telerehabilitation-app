from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.core.exercise_library import load_exercise_library
from app.models import Exercise, User
from app.schemas.exercise import ExerciseOut

router = APIRouter(prefix="/exercises")


@router.get("", response_model=list[ExerciseOut])
def list_exercises(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[ExerciseOut]:
    library = load_exercise_library()
    rows = db.scalars(select(Exercise).order_by(Exercise.name)).all()
    out: list[ExerciseOut] = []
    for row in rows:
        definition = library.get(row.id)
        if definition is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"exercise {row.id!r} has a catalog row but no definition file",
            )
        out.append(
            ExerciseOut(
                id=row.id,
                name=row.name,
                description=row.description,
                camera_view=row.camera_view,
                illustration_url=row.illustration_url,
                definition=definition,
            )
        )
    return out
