from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedResponse


class RecommendationItem(BaseModel):
    restaurant_name: str
    neighborhood: str
    cuisine: str
    why_it_matches: str
    price_tier: str


class RecommendationResponse(TimestampedResponse):
    destination_city: str
    destination_country: str
    summary: str
    status: str
    items: list[RecommendationItem]
    feedback_rating: int | None
    feedback_notes: str | None
    feedback_submitted_at: datetime | None


class RecommendationGenerateRequest(BaseModel):
    destination_city: str = Field(..., max_length=255)
    destination_country: str = Field(..., max_length=255)


class RecommendationGenerateResponse(BaseModel):
    recommendation: RecommendationResponse


class RecommendationFeedbackRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    notes: str | None = None
