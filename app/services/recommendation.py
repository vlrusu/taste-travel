from app.integrations.mock_recommendations import build_mock_recommendation
from app.models.feedback import Feedback
from app.models.recommendation import Recommendation
from app.models.user import User
from app.repositories.recommendation import FeedbackRepository, RecommendationRepository
from app.repositories.taste_profile import TasteProfileRepository


class RecommendationService:
    def __init__(
        self,
        recommendation_repository: RecommendationRepository,
        taste_profile_repository: TasteProfileRepository,
        feedback_repository: FeedbackRepository | None = None,
    ) -> None:
        self.recommendation_repository = recommendation_repository
        self.taste_profile_repository = taste_profile_repository
        self.feedback_repository = feedback_repository

    def generate_for_user(self, *, user: User, destination_city: str, destination_country: str) -> Recommendation:
        profile = self.taste_profile_repository.get_for_user(user.id)
        attributes = profile.attributes_json if profile else {}
        payload = build_mock_recommendation(
            destination_city=destination_city,
            destination_country=destination_country,
            top_cities=attributes.get("top_cities", []),
            loved_restaurants=attributes.get("loved_restaurants", []),
        )
        return self.recommendation_repository.create(
            user_id=user.id,
            request_context_json=payload["request_context_json"],
            restaurant_json=payload["restaurant_json"],
            score=payload["score"],
            why=payload["why"],
            anchors_json=payload["anchors_json"],
        )

    def submit_feedback(self, recommendation: Recommendation, *, user: User, feedback_type, notes: str | None) -> Feedback:
        if self.feedback_repository is None:
            raise RuntimeError("feedback_repository is required to submit feedback")
        return self.feedback_repository.create(
            recommendation_id=recommendation.id,
            user_id=user.id,
            feedback_type=feedback_type,
            notes=notes,
        )
