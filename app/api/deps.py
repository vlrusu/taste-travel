from collections.abc import Generator

from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.user import UserService


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


def get_current_user(
    db: Session = Depends(get_db),
    temp_user_id: str | None = Header(default=None, alias="X-Temp-User-Id"),
) -> User:
    service = UserService(UserRepository(db))
    if temp_user_id:
        try:
            user = service.get_or_create_temporary_user(UUID(temp_user_id))
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid X-Temp-User-Id header",
            ) from error
    else:
        user = service.get_or_create_default_user()
    db.commit()
    return user
