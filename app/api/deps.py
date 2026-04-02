from collections.abc import Generator

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.user import UserService


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_current_user(db: Session = Depends(get_db)) -> User:
    service = UserService(UserRepository(db))
    user = service.get_or_create_default_user()
    db.commit()
    return user
