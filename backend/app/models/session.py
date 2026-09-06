import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class ExerciseSession(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    patient_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    exercise_id: Mapped[str] = mapped_column(ForeignKey("exercises.id"))
    plan_item_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("plan_items.id", ondelete="SET NULL"), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    client_rep_count: Mapped[int] = mapped_column(Integer, default=0)
    client_reps: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    status: Mapped[str] = mapped_column(String(16), default="uploaded")  # uploaded | analyzed | failed
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SessionLandmarks(Base):
    __tablename__ = "session_landmarks"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    fps: Mapped[int] = mapped_column(Integer)
    data: Mapped[list[Any]] = mapped_column(JSONB)


class SessionAnalysis(Base):
    __tablename__ = "session_analysis"

    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    analyzer_version: Mapped[str] = mapped_column(String(32))
    rep_count: Mapped[int] = mapped_column(Integer)
    rep_count_mismatch: Mapped[bool] = mapped_column(Boolean, default=False)
    mean_rom: Mapped[float] = mapped_column(Float)
    best_rom: Mapped[float] = mapped_column(Float)
    form_consistency: Mapped[float] = mapped_column(Float)
    symmetry: Mapped[float | None] = mapped_column(Float, nullable=True)
    rom_trend_slope: Mapped[float] = mapped_column(Float)
    valid_frame_ratio: Mapped[float] = mapped_column(Float)
    mean_visibility: Mapped[float] = mapped_column(Float)
    fps: Mapped[int] = mapped_column(Integer)
    paused_seconds: Mapped[float] = mapped_column(Float)
    low_quality: Mapped[bool] = mapped_column(Boolean, default=False)
    per_rep: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    violations: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    flags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
