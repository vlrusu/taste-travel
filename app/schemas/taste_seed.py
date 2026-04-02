from pydantic import BaseModel, Field

from app.schemas.common import TimestampedResponse


class TasteSeedResponse(TimestampedResponse):
    title: str
    category: str
    notes: str | None


class TasteSeedCreateRequest(BaseModel):
    title: str = Field(..., max_length=255)
    category: str = Field(..., max_length=50)
    notes: str | None = None
