import uuid
from typing import Any

from sqlalchemy import JSON, ForeignKey, Text, Uuid
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


jsonb_type = JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql")


class TasteProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "taste_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    attributes_json: Mapped[dict[str, Any]] = mapped_column(jsonb_type, nullable=False, default=dict)

    user = relationship("User", back_populates="taste_profile")
