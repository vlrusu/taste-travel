from uuid import UUID
from typing import Any

from pydantic import BaseModel

from app.schemas.common import TimestampedResponse


class TasteProfileResponse(TimestampedResponse):
    user_id: UUID
    summary: str
    attributes_json: dict[str, Any]


class TasteProfileGenerateResponse(BaseModel):
    taste_profile: TasteProfileResponse
