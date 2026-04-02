import uuid
from typing import Any

from sqlalchemy import JSON, Float, ForeignKey, Text, Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


jsonb_type = JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")


class Recommendation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "recommendations"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    request_context_json: Mapped[dict[str, Any]] = mapped_column(jsonb_type, nullable=False, default=dict)
    restaurant_json: Mapped[dict[str, Any]] = mapped_column(jsonb_type, nullable=False, default=dict)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    why: Mapped[str] = mapped_column(Text, nullable=False)
    anchors_json: Mapped[dict[str, Any]] = mapped_column(jsonb_type, nullable=False, default=dict)

    user = relationship("User", back_populates="recommendations")
    feedback_entries = relationship("Feedback", back_populates="recommendation", cascade="all, delete-orphan")
