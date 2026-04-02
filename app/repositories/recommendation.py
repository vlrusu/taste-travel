from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.recommendation import Recommendation


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        destination_city: str,
        destination_country: str,
        summary: str,
        items: list[dict],
    ) -> Recommendation:
        recommendation = Recommendation(
            user_id=user_id,
            destination_city=destination_city,
            destination_country=destination_country,
            summary=summary,
            items=items,
            status="generated",
        )
        self.db.add(recommendation)
        self.db.flush()
        self.db.refresh(recommendation)
        return recommendation

    def get_for_user(self, *, user_id: UUID, recommendation_id: UUID) -> Recommendation | None:
        return self.db.scalar(
            select(Recommendation).where(
                Recommendation.id == recommendation_id,
                Recommendation.user_id == user_id,
            )
        )

    def update_feedback(self, recommendation: Recommendation, *, rating: int, notes: str | None, submitted_at) -> Recommendation:
        recommendation.feedback_rating = rating
        recommendation.feedback_notes = notes
        recommendation.feedback_submitted_at = submitted_at
        self.db.add(recommendation)
        self.db.flush()
        self.db.refresh(recommendation)
        return recommendation
