from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.feedback import Feedback
from app.models.recommendation import Recommendation


class RecommendationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        request_context_json: dict[str, Any],
        restaurant_json: dict[str, Any],
        score: float,
        why: str,
        anchors_json: dict[str, Any],
    ) -> Recommendation:
        recommendation = Recommendation(
            user_id=user_id,
            request_context_json=request_context_json,
            restaurant_json=restaurant_json,
            score=score,
            why=why,
            anchors_json=anchors_json,
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


class FeedbackRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, *, recommendation_id: UUID, user_id: UUID, feedback_type, notes: str | None) -> Feedback:
        feedback = Feedback(
            recommendation_id=recommendation_id,
            user_id=user_id,
            feedback_type=feedback_type,
            notes=notes,
        )
        self.db.add(feedback)
        self.db.flush()
        self.db.refresh(feedback)
        return feedback
