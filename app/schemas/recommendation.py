from uuid import UUID
from typing import Any

from pydantic import BaseModel

from app.models.enums import FeedbackType
from app.schemas.common import TimestampedResponse


class RecommendationResponse(TimestampedResponse):
    user_id: UUID
    request_context_json: dict[str, Any]
    restaurant_json: dict[str, Any]
    score: float
    why: str
    anchors_json: dict[str, Any]


class RecommendationGenerateRequest(BaseModel):
    destination_city: str
    destination_country: str


class RecommendationGenerateResponse(BaseModel):
    recommendation: RecommendationResponse


class RecommendationFeedbackRequest(BaseModel):
    feedback_type: FeedbackType
    notes: str | None = None


class FeedbackResponse(TimestampedResponse):
    recommendation_id: UUID
    user_id: UUID
    feedback_type: FeedbackType
    notes: str | None
