from app.models.feedback import Feedback
from app.models.recommendation import Recommendation
from app.models.user import User
from app.repositories.recommendation import FeedbackRepository


class FeedbackService:
    def __init__(self, feedback_repository: FeedbackRepository) -> None:
        self.feedback_repository = feedback_repository

    def save_feedback(
        self,
        *,
        recommendation: Recommendation,
        user: User,
        feedback_type,
        notes: str | None,
    ) -> Feedback:
        return self.feedback_repository.create(
            recommendation_id=recommendation.id,
            user_id=user.id,
            feedback_type=feedback_type,
            notes=notes,
        )
