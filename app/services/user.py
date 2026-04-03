from uuid import UUID

from app.core.config import get_settings
from app.models.user import User
from app.repositories.user import UserRepository


class UserService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository
        self.settings = get_settings()

    def get_or_create_default_user(self) -> User:
        user = self.user_repository.get_by_email(self.settings.default_user_email)
        if user is None:
            user = self.user_repository.create(email=self.settings.default_user_email)
        return user

    def get_or_create_temporary_user(self, user_id: UUID) -> User:
        user = self.user_repository.get_by_id(user_id)
        if user is None:
            user = self.user_repository.create(user_id=user_id, email=None)
        return user

    def update_user(self, user: User, **changes: object) -> User:
        if not changes:
            return user
        return self.user_repository.update(user, **changes)
