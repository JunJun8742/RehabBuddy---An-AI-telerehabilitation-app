import json

import pytest
from pydantic import ValidationError

from app.core.exercise_library import load_exercise_library, load_landmark_lookup
from app.schemas.exercise import ExerciseDefinition


def test_landmark_lookup_has_paired_and_single_entries():
    lookup = load_landmark_lookup()
    assert lookup["nose"] == 0
    assert lookup["hip"] == {"left": 23, "right": 24}


def test_library_loads_squat():
    lib = load_exercise_library()
    assert "squat" in lib
    squat = lib["squat"]
    assert squat.primary_angle == "knee"
    assert squat.detection.down_threshold == 100
    assert squat.smoothing.alpha == 0.3
    assert [r.id for r in squat.form_rules] == ["torso_lean", "shallow_depth"]


def test_definition_rejects_unknown_landmark_name():
    raw = load_exercise_library()["squat"].model_dump()
    raw["angles"]["knee"]["points"] = ["hip", "kneecap", "ankle"]
    with pytest.raises(ValidationError):
        ExerciseDefinition.model_validate(raw)


def test_definition_rejects_primary_angle_not_in_angles():
    raw = load_exercise_library()["squat"].model_dump()
    raw["primary_angle"] = "elbow"
    with pytest.raises(ValidationError):
        ExerciseDefinition.model_validate(raw)


def test_definition_rejects_form_rule_with_unknown_angle():
    raw = load_exercise_library()["squat"].model_dump()
    raw["form_rules"][0]["angle"] = "elbow"
    with pytest.raises(ValidationError):
        ExerciseDefinition.model_validate(raw)


def test_definition_rejects_legacy_rep_block():
    raw = load_exercise_library()["squat"].model_dump()
    raw["rep"] = raw.pop("detection")
    with pytest.raises(ValidationError):
        ExerciseDefinition.model_validate(raw)
