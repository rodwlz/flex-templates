import uuid

from lib.contracts.base import ActionRequest
from lib.core.interfaces import StagingService
from lib.database.session import SessionFactory
from lib.repositories.role_repository import RoleRepository
from lib.repositories.user_repository import UserRepository


class UserService(StagingService):
    """Supports both immediate and staged operations.

    Immediate (SimpleService-style): get, list, create, delete — one shot, no preview.
    Staged (StagingService-style): stage → confirm/cancel for multi-step operations
    that need a preview (e.g. creating a user and assigning roles in one transaction).
    """

    def __init__(self, factory: SessionFactory):
        super().__init__(factory)

    # ===== IMMEDIATE OPERATIONS (SimpleService style) =====

    def get(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        user = repo.get(uuid.UUID(data["id"]))
        if user is None:
            raise ValueError(f"User {data['id']} not found")
        return {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "roles": [{"id": str(r.id), "name": r.name} for r in user.roles],
        }

    def list(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        users = repo.list()
        return {
            "users": [
                {
                    "id": str(u.id),
                    "username": u.username,
                    "email": u.email,
                    "role_count": len(u.roles),
                }
                for u in users
            ]
        }

    def create(self, data: dict) -> dict:
        """Simple immediate create, no roles."""
        repo = UserRepository(self._factory)
        user = repo.create({
            "username": data["username"],
            "email": data["email"],
            "password_hash": data.get("password_hash", ""),
            "salt": data.get("salt", ""),
        })
        return {"id": str(user.id), "username": user.username, "email": user.email}

    def delete(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        deleted = repo.delete(uuid.UUID(data["id"]))
        if not deleted:
            raise ValueError(f"User {data['id']} not found")
        return {"deleted": True}

    # ===== STAGED OPERATION (StagingService style) =====

    def _stage_impl(self, uow, data: dict) -> dict:
        """Stage creation with roles — complex operation needs preview."""
        repo = uow.repo(UserRepository)
        role_repo = uow.repo(RoleRepository)

        user = repo.create({
            "username": data["username"],
            "email": data["email"],
            "password_hash": data.get("password_hash", ""),
            "salt": data.get("salt", ""),
        })

        if role_ids := data.get("role_ids"):
            for role_id in role_ids:
                role = role_repo.get(uuid.UUID(role_id) if isinstance(role_id, str) else role_id)
                if role:
                    user.roles.append(role)

        return {"user_id": str(user.id), "role_count": len(user.roles)}

    # ===== CONVENIENCE WRAPPERS (no ActionRequest needed) =====

    def get_user(self, user_id: str | uuid.UUID) -> dict:
        user_id_str = str(user_id)
        return self.execute(ActionRequest(action="get", data={"id": user_id_str})).data

    def list_users(self) -> list[dict]:
        result = self.execute(ActionRequest(action="list", data={}))
        return result.data.get("users", [])

    def create_user(self, username: str, email: str, password_hash: str = "", salt: str = "") -> dict:
        result = self.execute(ActionRequest(action="create", data={
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "salt": salt,
        }))
        return result.data

    def delete_user(self, user_id: str | uuid.UUID) -> bool:
        user_id_str = str(user_id)
        result = self.execute(ActionRequest(action="delete", data={"id": user_id_str}))
        return result.success

    def stage_user_with_roles(self, username: str, email: str, role_ids: list[str | uuid.UUID]) -> dict:
        """Stage user creation with roles for preview before confirm."""
        role_ids_str = [str(rid) for rid in role_ids]
        result = self.execute(ActionRequest(action="stage", data={
            "username": username,
            "email": email,
            "role_ids": role_ids_str,
        }))
        return result.data

    def confirm_staged(self) -> bool:
        """Confirm the staged user creation with roles."""
        result = self.execute(ActionRequest(action="confirm", data={}))
        return result.success

    def cancel_staged(self) -> bool:
        """Cancel the staged user creation."""
        result = self.execute(ActionRequest(action="cancel", data={}))
        return result.success
