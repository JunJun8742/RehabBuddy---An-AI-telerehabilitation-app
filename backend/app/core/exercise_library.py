import json
from functools import lru_cache

from app.core.config import settings
from app.schemas.exercise import ExerciseDefinition


@lru_cache
def load_landmark_lookup() -> dict[str, int | dict[str, int]]:
    with open(settings.shared_dir / "landmarks.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def load_exercise_library() -> dict[str, ExerciseDefinition]:
    library: dict[str, ExerciseDefinition] = {}
    for path in sorted((settings.shared_dir / "exercises").glob("*.json")):
        with open(path, encoding="utf-8") as f:
            definition = ExerciseDefinition.model_validate(json.load(f))
        if definition.id != path.stem:
            raise ValueError(f"{path.name}: id {definition.id!r} must match the file name")
        library[definition.id] = definition
    return library
