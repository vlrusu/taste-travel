from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.taste_profile import TasteProfile


class TasteProfileRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_for_user(self, user_id: UUID) -> TasteProfile | None:
        return self.db.scalar(select(TasteProfile).where(TasteProfile.user_id == user_id))

    def upsert(
        self,
        *,
        user_id: UUID,
        summary: str,
        vibe: str,
        cuisine_preferences: list[str],
        destination_preferences: list[str],
    ) -> TasteProfile:
        profile = self.get_for_user(user_id)
        if profile is None:
            profile = TasteProfile(
                user_id=user_id,
                summary=summary,
                vibe=vibe,
                cuisine_preferences=cuisine_preferences,
                destination_preferences=destination_preferences,
            )
            self.db.add(profile)
        else:
            profile.summary = summary
            profile.vibe = vibe
            profile.cuisine_preferences = cuisine_preferences
            profile.destination_preferences = destination_preferences

        self.db.flush()
        self.db.refresh(profile)
        return profile
