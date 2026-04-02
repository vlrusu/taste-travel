from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.seed_restaurant import SeedRestaurant
from app.models.taste_seed import TasteSeed


class TasteSeedRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[SeedRestaurant]:
        stmt = (
            select(SeedRestaurant)
            .where(SeedRestaurant.user_id == user_id)
            .order_by(SeedRestaurant.created_at.desc())
        )
        return list(self.db.scalars(stmt))

    def create(self, *, user_id: UUID, name: str, city: str, sentiment, notes: str | None) -> SeedRestaurant:
        seed = SeedRestaurant(user_id=user_id, name=name, city=city, sentiment=sentiment, notes=notes)
        self.db.add(seed)
        self.db.flush()
        self.db.refresh(seed)
        return seed

    def get_for_user(self, *, user_id: UUID, seed_id: UUID) -> SeedRestaurant | None:
        return self.db.scalar(select(SeedRestaurant).where(SeedRestaurant.id == seed_id, SeedRestaurant.user_id == user_id))

    def delete(self, seed: SeedRestaurant) -> None:
        self.db.delete(seed)
        self.db.flush()


SeedRestaurantRepository = TasteSeedRepository
