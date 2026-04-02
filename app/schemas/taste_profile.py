from pydantic import BaseModel

from app.schemas.common import TimestampedResponse


class TasteProfileResponse(TimestampedResponse):
    summary: str
    vibe: str
    cuisine_preferences: list[str]
    destination_preferences: list[str]


class TasteProfileGenerateResponse(BaseModel):
    taste_profile: TasteProfileResponse
