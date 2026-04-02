from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import SeedRestaurantSentiment
from app.schemas.common import TimestampedResponse


class SeedRestaurantResponse(TimestampedResponse):
    user_id: UUID
    name: str
    city: str
    sentiment: SeedRestaurantSentiment
    notes: str | None


class SeedRestaurantCreateRequest(BaseModel):
    name: str = Field(..., max_length=255)
    city: str = Field(..., max_length=255)
    sentiment: SeedRestaurantSentiment
    notes: str | None = None


TasteSeedResponse = SeedRestaurantResponse
TasteSeedCreateRequest = SeedRestaurantCreateRequest
