import uuid

from sqlalchemy import JSON, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class TasteProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "taste_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False, unique=True)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    vibe: Mapped[str] = mapped_column(String(120), nullable=False)
    cuisine_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    destination_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    user = relationship("User", back_populates="taste_profile")
