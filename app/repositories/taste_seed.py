from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.taste_seed import TasteSeed


class TasteSeedRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_user(self, user_id: UUID) -> list[TasteSeed]:
        return list(self.db.scalars(select(TasteSeed).where(TasteSeed.user_id == user_id).order_by(TasteSeed.created_at.desc())))

    def create(self, *, user_id: UUID, title: str, category: str, notes: str | None) -> TasteSeed:
        seed = TasteSeed(user_id=user_id, title=title, category=category, notes=notes)
        self.db.add(seed)
        self.db.flush()
        self.db.refresh(seed)
        return seed

    def get_for_user(self, *, user_id: UUID, seed_id: UUID) -> TasteSeed | None:
        return self.db.scalar(select(TasteSeed).where(TasteSeed.id == seed_id, TasteSeed.user_id == user_id))

    def delete(self, seed: TasteSeed) -> None:
        self.db.delete(seed)
        self.db.flush()
