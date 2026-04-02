from datetime import datetime, timezone

from app.integrations.mock_recommendations import build_mock_recommendations
from app.models.recommendation import Recommendation
from app.models.user import User
from app.repositories.recommendation import RecommendationRepository
from app.repositories.taste_profile import TasteProfileRepository


class RecommendationService:
    def __init__(
        self,
        recommendation_repository: RecommendationRepository,
        taste_profile_repository: TasteProfileRepository,
    ) -> None:
        self.recommendation_repository = recommendation_repository
        self.taste_profile_repository = taste_profile_repository

    def generate_for_user(self, *, user: User, destination_city: str, destination_country: str) -> Recommendation:
        profile = self.taste_profile_repository.get_for_user(user.id)
        cuisines = profile.cuisine_preferences if profile else []
        vibe = profile.vibe if profile else "Flexible city explorer"
        payload = build_mock_recommendations(
            destination_city=destination_city,
            destination_country=destination_country,
            taste_vibe=vibe,
            cuisines=cuisines,
        )
        return self.recommendation_repository.create(
            user_id=user.id,
            destination_city=destination_city,
            destination_country=destination_country,
            summary=payload["summary"],
            items=payload["items"],
        )

    def submit_feedback(self, recommendation: Recommendation, *, rating: int, notes: str | None) -> Recommendation:
        return self.recommendation_repository.update_feedback(
            recommendation,
            rating=rating,
            notes=notes,
            submitted_at=datetime.now(timezone.utc),
        )
