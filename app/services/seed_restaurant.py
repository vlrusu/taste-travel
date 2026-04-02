from app.models.seed_restaurant import SeedRestaurant
from app.repositories.taste_seed import TasteSeedRepository


class DuplicateSeedRestaurantError(ValueError):
    pass


class SeedRestaurantService:
    def __init__(self, repository: TasteSeedRepository) -> None:
        self.repository = repository

    def create_seed(self, *, user_id, name: str, city: str, sentiment, notes: str | None) -> SeedRestaurant:
        existing = self.repository.get_by_user_name_city(user_id=user_id, name=name, city=city)
        if existing is not None:
            raise DuplicateSeedRestaurantError("A seed restaurant with that name and city already exists")

        return self.repository.create(
            user_id=user_id,
            name=name,
            city=city,
            sentiment=sentiment,
            notes=notes,
        )
