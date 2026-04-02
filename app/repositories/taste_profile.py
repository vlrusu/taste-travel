from typing import Any
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
        attributes_json: dict[str, Any],
    ) -> TasteProfile:
        profile = self.get_for_user(user_id)
        if profile is None:
            profile = TasteProfile(
                user_id=user_id,
                summary=summary,
                attributes_json=attributes_json,
            )
            self.db.add(profile)
        else:
            profile.summary = summary
            profile.attributes_json = attributes_json

        self.db.flush()
        self.db.refresh(profile)
        return profile
