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
        titles = [seed.title for seed in seeds]
        categories = [seed.category for seed in seeds]
        category_counts = Counter(categories)

        cuisine_preferences = [name for name, _ in category_counts.most_common(3)] or ["regional"]
        destination_preferences = titles[:3] or ["walkable food neighborhoods", "chef-led local favorites"]
        vibe = "Curious, design-aware diner"
        if "street-food" in category_counts:
            vibe = "Adventurous street-food hunter"
        elif "fine-dining" in category_counts:
            vibe = "High-touch reservation planner"

        summary = (
            f"{user.full_name} prefers {', '.join(cuisine_preferences)} experiences and is drawn to "
            f"{', '.join(destination_preferences)}."
        )
        if user.home_city:
            summary += f" Home base: {user.home_city}."
        if user.dietary_preferences:
            summary += f" Dietary preferences: {', '.join(user.dietary_preferences)}."

        return self.taste_profile_repository.upsert(
            user_id=user.id,
            summary=summary,
            vibe=vibe,
            cuisine_preferences=cuisine_preferences,
            destination_preferences=destination_preferences,
        )
