from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base


class Exercise(Base):
    """Catalog row only. Detection rules live in shared/exercises/<id>.json."""

    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text)
    camera_view: Mapped[str] = mapped_column(String(8))  # "front" | "side"
    illustration_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
