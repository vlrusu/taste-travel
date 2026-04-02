from collections import Counter

from app.models.taste_profile import TasteProfile
from app.models.user import User
from app.repositories.taste_profile import TasteProfileRepository
from app.repositories.taste_seed import TasteSeedRepository


class TasteProfileService:
    def __init__(
        self,
        taste_seed_repository: TasteSeedRepository,
        taste_profile_repository: TasteProfileRepository,
    ) -> None:
        self.taste_seed_repository = taste_seed_repository
        self.taste_profile_repository = taste_profile_repository

    def generate_for_user(self, user: User) -> TasteProfile:
        seeds = self.taste_seed_repository.list_for_user(user.id)
        loved = [seed for seed in seeds if seed.sentiment == "love"]
        disliked = [seed for seed in seeds if seed.sentiment == "dislike"]
        top_cities = [city for city, _ in Counter(seed.city for seed in loved).most_common(3)]

        summary = "User taste profile generated from saved seed restaurants."
        if top_cities:
            summary = f"User consistently responds well to restaurants in {', '.join(top_cities)}."

        attributes_json = {
            "loved_restaurants": [seed.name for seed in loved],
            "disliked_restaurants": [seed.name for seed in disliked],
            "top_cities": top_cities,
            "onboarding_complete": user.onboarding_complete,
        }

        return self.taste_profile_repository.upsert(
            user_id=user.id,
            summary=summary,
            attributes_json=attributes_json,
        )
