"""Backend adapter layer — decouples Flet views from services/HTTP.

IBackendAdapter maps four domain sub-adapters:
  backend.auth       → IAuthAdapter
  backend.users      → IUserAdapter
  backend.roles      → IRoleAdapter
  backend.scheduler  → ISchedulerAdapter

Today: ServiceBackendAdapter wires to Python services directly.
Tomorrow: swap for HttpBackendAdapter in main.py — zero view changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from lib.adapters.auth_adapter import IAuthAdapter, ServiceAuthAdapter
from lib.adapters.users_adapter import IUserAdapter, ServiceUserAdapter
from lib.adapters.roles_adapter import IRoleAdapter, ServiceRoleAdapter
from lib.adapters.scheduler_adapter import ISchedulerAdapter, ServiceSchedulerAdapter
from lib.database.session import SessionFactory
from lib.services.user_service import UserService


class IBackendAdapter(ABC):
    """System map: one property per domain. Add a new entity = one new property here."""

    @property
    @abstractmethod
    def auth(self) -> IAuthAdapter: ...

    @property
    @abstractmethod
    def users(self) -> IUserAdapter: ...

    @property
    @abstractmethod
    def roles(self) -> IRoleAdapter: ...

    @property
    @abstractmethod
    def scheduler(self) -> ISchedulerAdapter: ...


class ServiceBackendAdapter(IBackendAdapter):
    """Concrete adapter: wires domain sub-adapters to Python services/repos.

    Swap for HttpBackendAdapter in main.py — views are unaffected.
    """

    def __init__(self, factory: SessionFactory, user_service: UserService, scheduler=None):
        self._auth      = ServiceAuthAdapter(user_service)
        self._users     = ServiceUserAdapter(factory, user_service)
        self._roles     = ServiceRoleAdapter(factory)
        self._scheduler = ServiceSchedulerAdapter(scheduler)

    @property
    def auth(self) -> IAuthAdapter:
        return self._auth

    @property
    def users(self) -> IUserAdapter:
        return self._users

    @property
    def roles(self) -> IRoleAdapter:
        return self._roles

    @property
    def scheduler(self) -> ISchedulerAdapter:
        return self._scheduler
