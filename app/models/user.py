from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    home_city: Mapped[str | None] = mapped_column(String(255), index=True, nullable=True)
    onboarding_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    seed_restaurants = relationship("SeedRestaurant", back_populates="user", cascade="all, delete-orphan")
    taste_profile = relationship("TasteProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
    feedback_entries = relationship("Feedback", back_populates="user", cascade="all, delete-orphan")
