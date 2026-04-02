import uuid

from sqlalchemy import Enum, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SeedRestaurantSentiment


class SeedRestaurant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "seed_restaurants"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    sentiment: Mapped[SeedRestaurantSentiment] = mapped_column(
        Enum(SeedRestaurantSentiment, name="seed_restaurant_sentiment"),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="seed_restaurants")
