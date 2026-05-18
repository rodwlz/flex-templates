import uuid

from lib.contracts.base import ActionRequest, ActionResult
from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory
from lib.repositories.role_repository import RoleRepository


class RoleService(SimpleService):
    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def create(self, data: dict) -> dict:
        repo = RoleRepository(self._factory)
        role = repo.create(data)
        return {"id": str(role.id), "name": role.name, "description": role.description}

    def get(self, data: dict) -> dict:
        repo = RoleRepository(self._factory)
        role = repo.get(uuid.UUID(data["id"]))
        if role is None:
            raise ValueError(f"Role {data['id']} not found")
        return {"id": str(role.id), "name": role.name, "description": role.description}

    def list(self, data: dict) -> dict:
        repo = RoleRepository(self._factory)
        roles = repo.list()
        return {
            "roles": [
                {"id": str(r.id), "name": r.name, "description": r.description}
                for r in roles
            ]
        }

    def delete(self, data: dict) -> dict:
        repo = RoleRepository(self._factory)
        deleted = repo.delete(uuid.UUID(data["id"]))
        if not deleted:
            raise ValueError(f"Role {data['id']} not found")
        return {"deleted": True}
