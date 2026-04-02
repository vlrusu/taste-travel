import uuid

from sqlalchemy import Enum, ForeignKey, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin
from app.models.enums import FeedbackType


class Feedback(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "feedback"

    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("recommendations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type: Mapped[FeedbackType] = mapped_column(
        Enum(FeedbackType, name="feedback_type", native_enum=False),
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    recommendation = relationship("Recommendation", back_populates="feedback_entries")
    user = relationship("User", back_populates="feedback_entries")
