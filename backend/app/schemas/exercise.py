import json
from functools import lru_cache
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.config import settings


@lru_cache
def _landmark_names() -> frozenset[str]:
    with open(settings.shared_dir / "landmarks.json", encoding="utf-8") as f:
        return frozenset(json.load(f).keys())


class AngleDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    points: list[str] = Field(min_length=2, max_length=3)
    reference: Literal["vertical", "horizontal"] | None = None

    @model_validator(mode="after")
    def _check(self) -> "AngleDef":
        unknown = [p for p in self.points if p not in _landmark_names()]
        if unknown:
            raise ValueError(f"unknown landmark names: {unknown}")
        if len(self.points) == 2 and self.reference is None:
            raise ValueError("two-point angles need a reference axis")
        if len(self.points) == 3 and self.reference is not None:
            raise ValueError("three-point angles do not take a reference axis")
        return self


class DetectionDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    down_threshold: float
    up_threshold: float
    min_hold_frames: int = Field(ge=1, default=3)


class SmoothingDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["ema"]
    alpha: float = Field(gt=0, le=1)


class FormRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    angle: str
    max: float | None = None
    min: float | None = None
    rep_min_must_be_below: float | None = None
    frames: int = Field(ge=1, default=5)
    cue: str

    @model_validator(mode="after")
    def _check(self) -> "FormRule":
        if self.max is None and self.min is None and self.rep_min_must_be_below is None:
            raise ValueError(f"form rule {self.id} has no condition")
        return self


class ExerciseDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    description: str
    camera_view: Literal["front", "side"]
    side: Literal["left", "right", "both"]
    required_landmarks: list[str] = Field(min_length=1)
    angles: dict[str, AngleDef]
    primary_angle: str
    detection: DetectionDef
    smoothing: SmoothingDef
    form_rules: list[FormRule] = []
    illustration: str

    @model_validator(mode="after")
    def _check(self) -> "ExerciseDefinition":
        unknown = [p for p in self.required_landmarks if p not in _landmark_names()]
        if unknown:
            raise ValueError(f"unknown required landmarks: {unknown}")
        if self.primary_angle not in self.angles:
            raise ValueError(f"primary_angle {self.primary_angle!r} not defined in angles")
        for rule in self.form_rules:
            if rule.angle not in self.angles:
                raise ValueError(f"form rule {rule.id} references unknown angle {rule.angle!r}")
        return self


class ExerciseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    camera_view: str
    illustration_url: str | None
    definition: ExerciseDefinition
