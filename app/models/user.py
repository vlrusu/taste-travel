from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    home_city: Mapped[str | None] = mapped_column(String(255), nullable=True)
    dietary_preferences: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)

    seeds = relationship("TasteSeed", back_populates="user", cascade="all, delete-orphan")
    taste_profile = relationship("TasteProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    recommendations = relationship("Recommendation", back_populates="user", cascade="all, delete-orphan")
