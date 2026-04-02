from pydantic import BaseModel, Field

from app.schemas.common import TimestampedResponse


class UserResponse(TimestampedResponse):
    email: str | None
    home_city: str | None
    onboarding_complete: bool


class UserUpdateRequest(BaseModel):
    email: str | None = Field(default=None, max_length=255)
    home_city: str | None = Field(default=None, max_length=255)
    onboarding_complete: bool | None = None
