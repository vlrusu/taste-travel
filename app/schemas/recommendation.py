from uuid import UUID
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import FeedbackType
from app.schemas.common import CreatedResponse, TimestampedResponse


class RecommendationResponse(TimestampedResponse):
    user_id: UUID
    request_context_json: dict[str, Any]
    restaurant_json: dict[str, Any]
    score: float
    why: str
    anchors_json: dict[str, Any]


class RecommendationLocationRequest(BaseModel):
    city: str = Field(..., max_length=255)
    lat: float | None = None
    lon: float | None = None


class RecommendationContextRequest(BaseModel):
    budget: str | None = Field(default=None, max_length=10)
    max_distance_meters: int | None = Field(default=None, ge=1)
    special_request: str | None = Field(default=None, max_length=500)


class RecommendationGenerateRequest(BaseModel):
    location: RecommendationLocationRequest
    context: RecommendationContextRequest


class RecommendationGenerateResponse(BaseModel):
    recommendations: list[RecommendationResponse]


class RecommendationFeedbackRequest(BaseModel):
    feedback_type: FeedbackType
    notes: str | None = None


class FeedbackResponse(CreatedResponse):
    recommendation_id: UUID
    user_id: UUID
    feedback_type: FeedbackType
    notes: str | None
