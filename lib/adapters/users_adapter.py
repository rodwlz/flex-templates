from __future__ import annotations

from abc import ABC, abstractmethod

from lib.adapters._utils import _str_uuids
from lib.database.session import SessionFactory
from lib.repositories.user_repository import UserRepository
from lib.services.user_service import UserService

_SENSITIVE = frozenset({"password_hash", "salt"})


class IUserAdapter(ABC):
    @abstractmethod
    def list(self, page: int = 1, page_size: int = 20) -> dict:
        """Returns paginate() shape: {items, total, page, page_size, pages}.
        Items are dicts with string UUIDs, no password_hash."""

    @abstractmethod
    def create(self, data: dict) -> dict: ...

    @abstractmethod
    def delete(self, user_id: str) -> bool: ...


class ServiceUserAdapter(IUserAdapter):
    def __init__(self, factory: SessionFactory, user_service: UserService):
        self._factory = factory
        self._user_service = user_service

    def list(self, page: int = 1, page_size: int = 20) -> dict:
        repo = UserRepository(self._factory)
        result = repo.paginate(page=page, page_size=page_size)
        result["items"] = [
            {k: v for k, v in _str_uuids(item).items() if k not in _SENSITIVE}
            for item in result["items"]
        ]
        return result

    def create(self, data: dict) -> dict:
        return self._user_service.create_user(
            username=data["username"],
            email=data["email"],
            password=data.get("password", ""),
        )

    def delete(self, user_id: str) -> bool:
        return self._user_service.delete_user(user_id)
