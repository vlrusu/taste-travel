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

    def create(
        self,
        *,
        user_id: UUID,
        name: str,
        city: str,
        sentiment,
        notes: str | None,
        source: str | None = None,
        source_place_id: str | None = None,
        formatted_address: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        price_level: str | None = None,
        rating: float | None = None,
        user_ratings_total: int | None = None,
        raw_types: list[str] | None = None,
        review_summary_text: str | None = None,
        editorial_summary_text: str | None = None,
        menu_summary_text: str | None = None,
        raw_seed_note_text: str | None = None,
        raw_place_metadata_json: dict | None = None,
        raw_review_text: str | None = None,
        derived_traits_json: dict | None = None,
        ai_summary_text: str | None = None,
        enrichment_status: str | None = None,
        enriched_at=None,
        place_traits_json: dict | None = None,
        is_verified_place: bool = False,
    ) -> SeedRestaurant:
        seed = SeedRestaurant(
            user_id=user_id,
            name=name,
            city=city,
            sentiment=sentiment,
            notes=notes,
            source=source,
            source_place_id=source_place_id,
            formatted_address=formatted_address,
            lat=lat,
            lon=lon,
            price_level=price_level,
            rating=rating,
            user_ratings_total=user_ratings_total,
            raw_types=raw_types,
            review_summary_text=review_summary_text,
            editorial_summary_text=editorial_summary_text,
            menu_summary_text=menu_summary_text,
            raw_seed_note_text=raw_seed_note_text,
            raw_place_metadata_json=raw_place_metadata_json,
            raw_review_text=raw_review_text,
            derived_traits_json=derived_traits_json,
            ai_summary_text=ai_summary_text,
            enrichment_status=enrichment_status,
            enriched_at=enriched_at,
            place_traits_json=place_traits_json,
            is_verified_place=is_verified_place,
        )
        self.db.add(seed)
        self.db.flush()
        self.db.refresh(seed)
        return seed

    def get_by_user_name_city(self, *, user_id: UUID, name: str, city: str) -> SeedRestaurant | None:
        stmt = select(SeedRestaurant).where(
            SeedRestaurant.user_id == user_id,
            SeedRestaurant.name == name,
            SeedRestaurant.city == city,
        )
        return self.db.scalar(stmt)

    def get_for_user(self, *, user_id: UUID, seed_id: UUID) -> SeedRestaurant | None:
        return self.db.scalar(select(SeedRestaurant).where(SeedRestaurant.id == seed_id, SeedRestaurant.user_id == user_id))

    def delete(self, seed: SeedRestaurant) -> None:
        self.db.delete(seed)
        self.db.flush()


SeedRestaurantRepository = TasteSeedRepository
