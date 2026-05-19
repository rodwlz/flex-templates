import uuid

from lib.contracts.base import ActionRequest
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

    # ===== CONVENIENCE WRAPPERS (no ActionRequest needed) =====

    def create_role(self, name: str, description: str = "") -> dict:
        return self.execute(ActionRequest(action="create", data={"name": name, "description": description})).data

    def get_role(self, role_id: str | uuid.UUID) -> dict:
        role_id_str = str(role_id)
        return self.execute(ActionRequest(action="get", data={"id": role_id_str})).data

    def list_roles(self) -> list[dict]:
        result = self.execute(ActionRequest(action="list", data={}))
        return result.data.get("roles", [])

    def delete_role(self, role_id: str | uuid.UUID) -> bool:
        role_id_str = str(role_id)
        result = self.execute(ActionRequest(action="delete", data={"id": role_id_str}))
        return result.success
