from uuid import UUID
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import SeedRestaurantSentiment
from app.schemas.common import TimestampedResponse


class SeedRestaurantResponse(TimestampedResponse):
    user_id: UUID
    name: str
    city: str
    sentiment: SeedRestaurantSentiment
    notes: str | None
    source: str | None
    source_place_id: str | None
    formatted_address: str | None
    lat: float | None
    lon: float | None
    price_level: str | None
    rating: float | None
    user_ratings_total: int | None
    raw_types: list[str] | None
    review_summary_text: str | None
    editorial_summary_text: str | None
    menu_summary_text: str | None
    raw_seed_note_text: str | None
    raw_place_metadata_json: dict | None
    raw_review_text: str | None
    derived_traits_json: dict | None
    ai_summary_text: str | None
    enrichment_status: str | None
    enriched_at: datetime | None
    place_traits_json: dict | None
    is_verified_place: bool


class SeedRestaurantCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    city: str = Field(..., max_length=255)
    sentiment: SeedRestaurantSentiment
    notes: str | None = None
    source: str | None = Field(default=None, max_length=50)
    source_place_id: str | None = Field(default=None, max_length=255)
    formatted_address: str | None = None
    lat: float | None = None
    lon: float | None = None
    price_level: str | None = Field(default=None, max_length=10)
    rating: float | None = None
    user_ratings_total: int | None = None
    raw_types: list[str] | None = None
    review_summary_text: str | None = None
    editorial_summary_text: str | None = None
    menu_summary_text: str | None = None
    raw_seed_note_text: str | None = None
    raw_place_metadata_json: dict | None = None
    raw_review_text: str | None = None
    derived_traits_json: dict | None = None
    ai_summary_text: str | None = None
    enrichment_status: str | None = None
    place_traits_json: dict | None = None
    is_verified_place: bool = False


class SeedRestaurantSearchResponse(BaseModel):
    name: str
    city: str
    formatted_address: str | None
    source: str
    source_place_id: str
    lat: float | None
    lon: float | None
    price_level: str | None
    rating: float | None
    user_ratings_total: int | None
    raw_types: list[str] | None
    review_summary_text: str | None = None
    editorial_summary_text: str | None = None
    menu_summary_text: str | None = None
    raw_seed_note_text: str | None = None
    raw_place_metadata_json: dict | None = None
    raw_review_text: str | None = None
    derived_traits_json: dict | None = None
    ai_summary_text: str | None = None
    place_traits_json: dict | None


TasteSeedResponse = SeedRestaurantResponse
TasteSeedCreateRequest = SeedRestaurantCreateRequest
