import uuid

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SeedRestaurantSentiment


class SeedRestaurant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "seed_restaurants"
    __table_args__ = (
        UniqueConstraint("user_id", "name", "city", name="uq_seed_restaurants_user_name_city"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sentiment: Mapped[SeedRestaurantSentiment] = mapped_column(
        Enum(SeedRestaurantSentiment, name="seed_restaurant_sentiment", native_enum=False),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    source: Mapped[str | None] = mapped_column(String(50), nullable=True)
    source_place_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    formatted_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)
    price_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    user_ratings_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    raw_types: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    review_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    editorial_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    menu_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_seed_note_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_place_metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    raw_review_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    derived_traits_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_summary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    enrichment_status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    enriched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    place_traits_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    is_verified_place: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")

    user = relationship("User", back_populates="seed_restaurants")
