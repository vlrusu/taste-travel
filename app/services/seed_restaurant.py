from app.models.seed_restaurant import SeedRestaurant
from app.repositories.taste_seed import TasteSeedRepository
from app.services.seed_enrichment import SeedEnrichmentService


class DuplicateSeedRestaurantError(ValueError):
    pass


class InvalidVerifiedSeedError(ValueError):
    pass


class SeedRestaurantService:
    def __init__(self, repository: TasteSeedRepository) -> None:
        self.repository = repository

    def create_seed(
        self,
        *,
        user_id,
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
        place_traits_json: dict | None = None,
        is_verified_place: bool = False,
    ) -> SeedRestaurant:
        existing = self.repository.get_by_user_name_city(user_id=user_id, name=name, city=city)
        if existing is not None:
            raise DuplicateSeedRestaurantError("A seed restaurant with that name and city already exists")
        if is_verified_place and (source != "google_places" or not source_place_id):
            raise InvalidVerifiedSeedError("Verified seed restaurants must include a selected Google place")

        raw_place_metadata_json = raw_place_metadata_json or (
            {
                "name": name,
                "city": city,
                "formatted_address": formatted_address,
                "price_level": price_level,
                "rating": rating,
                "user_ratings_total": user_ratings_total,
                "raw_types": raw_types,
                "source_place_id": source_place_id,
                "lat": lat,
                "lon": lon,
            }
            if is_verified_place
            else None
        )

        enrichment = SeedEnrichmentService.enrich_seed_payload(
            source=source,
            is_verified_place=is_verified_place,
            price_level=price_level,
            rating=rating,
            user_ratings_total=user_ratings_total,
            raw_types=raw_types,
            review_summary_text=review_summary_text,
            editorial_summary_text=editorial_summary_text,
            menu_summary_text=menu_summary_text,
            seed_notes=notes,
            raw_seed_note_text=raw_seed_note_text,
            raw_place_metadata_json=raw_place_metadata_json,
            raw_review_text=raw_review_text,
            derived_traits_json=derived_traits_json,
        )

        return self.repository.create(
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
            raw_seed_note_text=enrichment["raw_seed_note_text"],
            raw_place_metadata_json=enrichment["raw_place_metadata_json"],
            raw_review_text=enrichment["raw_review_text"],
            derived_traits_json=enrichment["derived_traits_json"],
            ai_summary_text=ai_summary_text or enrichment["ai_summary_text"],
            enrichment_status=enrichment["enrichment_status"],
            enriched_at=enrichment["enriched_at"],
            place_traits_json=place_traits_json,
            is_verified_place=is_verified_place,
        )
