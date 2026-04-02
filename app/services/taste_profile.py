from collections import Counter
import re

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

    @staticmethod
    def _extract_keywords(notes: list[str]) -> list[str]:
        tokens: list[str] = []
        stopwords = {
            "with",
            "and",
            "the",
            "for",
            "that",
            "from",
            "late",
            "spots",
            "menus",
            "menu",
            "restaurant",
            "restaurants",
            "place",
            "places",
        }
        for note in notes:
            tokens.extend(re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", note.lower()))

        counts = Counter(token for token in tokens if token not in stopwords)
        return [token for token, _ in counts.most_common(6)]

    def generate_for_user(self, user: User) -> TasteProfile:
        seeds = self.taste_seed_repository.list_for_user(user.id)
        if not seeds:
            summary = "Open-minded diner profile inferred from no explicit seed restaurants yet."
            attributes_json = {
                "loved_restaurants": [],
                "disliked_restaurants": [],
                "preferred_cities": [user.home_city] if user.home_city else [],
                "preferred_keywords": ["local", "welcoming", "well-reviewed"],
                "avoided_keywords": [],
                "sentiment_breakdown": {"love": 0, "dislike": 0},
                "default_profile": True,
            }
            return self.taste_profile_repository.upsert(
                user_id=user.id,
                summary=summary,
                attributes_json=attributes_json,
            )

        loved = [seed for seed in seeds if seed.sentiment.value == "love"]
        disliked = [seed for seed in seeds if seed.sentiment.value == "dislike"]
        preferred_cities = [city for city, _ in Counter(seed.city for seed in loved or seeds).most_common(3)]
        preferred_keywords = self._extract_keywords([seed.notes for seed in loved if seed.notes])
        avoided_keywords = self._extract_keywords([seed.notes for seed in disliked if seed.notes])

        if loved:
            summary = (
                f"User leans toward {', '.join(preferred_cities) or 'destination-driven'} dining with strong signals for "
                f"{', '.join(preferred_keywords[:3]) or 'quality and comfort'}."
            )
        else:
            summary = (
                f"User has more explicit dislikes than likes, so recommendations should avoid "
                f"{', '.join(avoided_keywords[:3]) or 'high-friction dining experiences'}."
            )

        attributes_json = {
            "loved_restaurants": [seed.name for seed in loved],
            "disliked_restaurants": [seed.name for seed in disliked],
            "preferred_cities": preferred_cities,
            "preferred_keywords": preferred_keywords,
            "avoided_keywords": avoided_keywords,
            "sentiment_breakdown": {"love": len(loved), "dislike": len(disliked)},
            "default_profile": False,
        }

        return self.taste_profile_repository.upsert(
            user_id=user.id,
            summary=summary,
            attributes_json=attributes_json,
        )
