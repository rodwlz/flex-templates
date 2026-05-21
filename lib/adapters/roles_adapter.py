from __future__ import annotations

import uuid
from abc import ABC, abstractmethod

from lib.adapters._utils import _str_uuids
from lib.database.session import SessionFactory
from lib.repositories.role_repository import RoleRepository
from lib.repositories.user_repository import UserRepository


class IRoleAdapter(ABC):
    @abstractmethod
    def list(self) -> list[dict]: ...

    @abstractmethod
    def create(self, name: str) -> dict: ...

    @abstractmethod
    def delete(self, role_id: str) -> bool: ...

    @abstractmethod
    def assign(self, user_id: str, role_id: str) -> bool: ...

    @abstractmethod
    def remove(self, user_id: str, role_id: str) -> bool: ...


class ServiceRoleAdapter(IRoleAdapter):
    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def list(self) -> list[dict]:
        repo = RoleRepository(self._factory)
        return [_str_uuids(r) for r in repo.filter_by()]

    def create(self, name: str) -> dict:
        repo = RoleRepository(self._factory)
        role = repo.create({"name": name})
        return {"id": str(role.id), "name": role.name}

    def delete(self, role_id: str) -> bool:
        repo = RoleRepository(self._factory)
        return repo.delete(uuid.UUID(role_id))

    def assign(self, user_id: str, role_id: str) -> bool:
        repo = UserRepository(self._factory)
        return repo.add_role(uuid.UUID(user_id), uuid.UUID(role_id))

    def remove(self, user_id: str, role_id: str) -> bool:
        repo = UserRepository(self._factory)
        return repo.remove_role(uuid.UUID(user_id), uuid.UUID(role_id))
