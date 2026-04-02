from pydantic import BaseModel, Field

from app.schemas.common import TimestampedResponse


class UserResponse(TimestampedResponse):
    email: str
    full_name: str
    home_city: str | None
    dietary_preferences: list[str]


class UserUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, max_length=255)
    home_city: str | None = Field(default=None, max_length=255)
    dietary_preferences: list[str] | None = None
