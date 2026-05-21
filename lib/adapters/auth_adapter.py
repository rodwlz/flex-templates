from __future__ import annotations

from abc import ABC, abstractmethod

from lib.services.user_service import UserService


class IAuthAdapter(ABC):
    @abstractmethod
    def login(self, username: str, password: str) -> dict:
        """Returns {"user": {id, username, email, roles}} on success.
        Raises ValueError on bad credentials."""

    @abstractmethod
    def logout(self) -> None: ...

    @abstractmethod
    def current_user(self) -> dict | None:
        """Returns logged-in user dict or None if not authenticated."""


class ServiceAuthAdapter(IAuthAdapter):
    def __init__(self, user_service: UserService):
        self._user_service = user_service
        self._session: dict | None = None

    def login(self, username: str, password: str) -> dict:
        user = self._user_service.authenticate_user(username, password)
        self._session = user
        return {"user": user}

    def logout(self) -> None:
        self._session = None

    def current_user(self) -> dict | None:
        return self._session
