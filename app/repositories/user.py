from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_by_email(self, email: str) -> User | None:
        return self.db.scalar(select(User).where(User.email == email))

    def create(self, *, email: str | None) -> User:
        user = User(email=email)
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user

    def update(self, user: User, **changes: object) -> User:
        for key, value in changes.items():
            setattr(user, key, value)
        self.db.add(user)
        self.db.flush()
        self.db.refresh(user)
        return user
