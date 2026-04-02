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

    def generate_for_user(
        self,
        *,
        user: User,
        destination_city: str,
        destination_country: str,
        dining_context: str | None,
    ) -> list[Recommendation]:
        profile = self.taste_profile_repository.get_for_user(user.id)
        attributes = profile.attributes_json if profile else {}
        payloads = build_mock_recommendations(
            destination_city=destination_city,
            destination_country=destination_country,
            dining_context=dining_context,
            preferred_cities=attributes.get("preferred_cities", []),
            preferred_keywords=attributes.get("preferred_keywords", []),
            loved_restaurants=attributes.get("loved_restaurants", []),
        )
        recommendations: list[Recommendation] = []
        for payload in payloads:
            recommendations.append(
                self.recommendation_repository.create(
                    user_id=user.id,
                    request_context_json=payload["request_context_json"],
                    restaurant_json=payload["restaurant_json"],
                    score=payload["score"],
                    why=payload["why"],
                    anchors_json=payload["anchors_json"],
                )
            )
        return recommendations
