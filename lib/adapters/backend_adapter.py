"""Backend adapter layer — decouples Flet views from services/HTTP.

Today: ServiceBackendAdapter calls services directly (no network hop).
Tomorrow: swap for HttpBackendAdapter in main.py — zero view changes.
"""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from lib.database.session import SessionFactory
from lib.repositories.role_repository import RoleRepository
from lib.repositories.user_repository import UserRepository
from lib.services.user_service import UserService


class IBackendAdapter(ABC):

    # ── Auth ──────────────────────────────────────────────────────────────
    @abstractmethod
    def login(self, username: str, password: str) -> dict:
        """Returns {"user": {id, username, email, roles}} on success.
        Raises ValueError on bad credentials."""

    @abstractmethod
    def logout(self) -> None: ...

    @abstractmethod
    def current_user(self) -> dict | None:
        """Returns logged-in user dict or None if not authenticated."""

    # ── Users ─────────────────────────────────────────────────────────────
    @abstractmethod
    def list_users(self, page: int = 1, page_size: int = 20, **filters) -> dict:
        """Returns paginate() shape: {items, total, page, page_size, pages}.
        Items are dicts with string UUIDs."""

    @abstractmethod
    def create_user(self, data: dict) -> dict: ...

    @abstractmethod
    def delete_user(self, user_id: str) -> bool: ...

    # ── Roles ─────────────────────────────────────────────────────────────
    @abstractmethod
    def list_roles(self) -> list[dict]: ...

    @abstractmethod
    def create_role(self, name: str) -> dict: ...

    @abstractmethod
    def delete_role(self, role_id: str) -> bool: ...

    @abstractmethod
    def assign_role(self, user_id: str, role_id: str) -> bool: ...

    @abstractmethod
    def remove_role(self, user_id: str, role_id: str) -> bool: ...

    # ── Scheduler ─────────────────────────────────────────────────────────
    @abstractmethod
    def list_jobs(self) -> list[dict]:
        """Returns [{id, name, trigger, next_run_time, func_name}, ...]"""


class ServiceBackendAdapter(IBackendAdapter):
    """Concrete adapter: calls Python services/repos directly.

    Swap for HttpBackendAdapter in main.py — views are unaffected.
    """

    def __init__(self, factory: SessionFactory, user_service: UserService, role_repo=None, scheduler=None):
        self._factory = factory
        self._user_service = user_service
        # role_repo is accepted for API compatibility but roles are created fresh per method
        self._scheduler = scheduler
        self._session: dict | None = None

    # ── Auth ──────────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict:
        user = self._user_service.authenticate_user(username, password)
        self._session = user
        return {"user": user}

    def logout(self) -> None:
        self._session = None

    def current_user(self) -> dict | None:
        return self._session

    # ── Users ─────────────────────────────────────────────────────────────

    def list_users(self, page: int = 1, page_size: int = 20, **filters) -> dict:
        repo = UserRepository(self._factory)
        result = repo.paginate(page=page, page_size=page_size)
        result["items"] = [_str_uuids(item) for item in result["items"]]
        return result

    def create_user(self, data: dict) -> dict:
        return self._user_service.create_user(
            username=data["username"],
            email=data["email"],
            password=data.get("password", ""),
        )

    def delete_user(self, user_id: str) -> bool:
        return self._user_service.delete_user(user_id)

    # ── Roles ─────────────────────────────────────────────────────────────

    def list_roles(self) -> list[dict]:
        repo = RoleRepository(self._factory)
        return [_str_uuids(r) for r in repo.filter_by()]

    def create_role(self, name: str) -> dict:
        repo = RoleRepository(self._factory)
        role = repo.create({"name": name})
        return {"id": str(role.id), "name": role.name}

    def delete_role(self, role_id: str) -> bool:
        repo = RoleRepository(self._factory)
        return repo.delete(uuid.UUID(role_id))

    def assign_role(self, user_id: str, role_id: str) -> bool:
        repo = UserRepository(self._factory)
        return repo.add_role(uuid.UUID(user_id), uuid.UUID(role_id))

    def remove_role(self, user_id: str, role_id: str) -> bool:
        repo = UserRepository(self._factory)
        return repo.remove_role(uuid.UUID(user_id), uuid.UUID(role_id))

    # ── Scheduler ─────────────────────────────────────────────────────────

    def list_jobs(self) -> list[dict]:
        if self._scheduler is None:
            return []
        jobs = self._scheduler.get_jobs()
        return [
            {
                "id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": str(job.next_run_time) if job.next_run_time else "—",
                "func_name": getattr(job.func, "__name__", str(job.func)),
            }
            for job in jobs
        ]


def _str_uuids(d: dict) -> dict:
    """Stringify any uuid.UUID values in *d* so views get plain strings."""
    return {k: str(v) if isinstance(v, uuid.UUID) else v for k, v in d.items()}
