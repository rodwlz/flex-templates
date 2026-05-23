import uuid

from sqlalchemy.exc import IntegrityError

from lib.contracts.base import ActionRequest
from lib.core.interfaces import StagingService
from lib.database.session import SessionFactory
from lib.repositories.password_reset_token_repository import PasswordResetTokenRepository
from lib.repositories.role_repository import RoleRepository
from lib.repositories.user_repository import UserRepository
from lib.security.password import hash_password, verify_password


_USER_LIST_FIELDS = frozenset({"id", "username", "email", "status", "is_active", "roles"})


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
        page = data.get("page", 1)
        page_size = data.get("page_size", 20)
        result = repo.paginate(page=page, page_size=page_size)
        result["items"] = [
            {k: (str(v) if k == "id" else v) for k, v in item.items() if k in _USER_LIST_FIELDS}
            for item in result["items"]
        ]
        return result

    def create(self, data: dict) -> dict:
        """Immediate create. Accepts either 'password' (plain) or 'password_hash'+'salt'."""
        plain = data.get("password", "")
        if plain:
            password_hash, salt = hash_password(plain)
        else:
            password_hash = data.get("password_hash", "")
            salt = data.get("salt", "")
        repo = UserRepository(self._factory)
        user = repo.create({
            "username": data["username"],
            "email": data["email"],
            "password_hash": password_hash,
            "salt": salt,
        })
        return {"id": str(user.id), "username": user.username, "email": user.email}

    def delete(self, data: dict) -> dict:
        repo = UserRepository(self._factory)
        deleted = repo.delete(uuid.UUID(data["id"]))
        if not deleted:
            raise ValueError(f"User {data['id']} not found")
        return {"deleted": True}

    def authenticate(self, data: dict) -> dict:
        """Verify login + password. Returns user dict on success, raises ValueError on failure."""
        login = data.get("username", "")
        password = data.get("password", "")
        repo = UserRepository(self._factory)
        user = repo.find_for_auth(login)
        if user is None or not verify_password(password, user["password_hash"]):
            raise ValueError("Invalid credentials")
        if not user["is_active"]:
            raise ValueError("Account is disabled")
        return {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "roles": user["roles"],
        }

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
        return result.data.get("items", [])

    def create_user(self, username: str, email: str, password: str = "", password_hash: str = "", salt: str = "") -> dict:
        result = self.execute(ActionRequest(action="create", data={
            "username": username,
            "email": email,
            "password": password,
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

    def authenticate_user(self, username: str, password: str) -> dict:
        """Wrapper: raise ValueError on bad credentials, return user dict on success."""
        result = self.execute(ActionRequest(
            action="authenticate",
            data={"username": username, "password": password},
        ))
        if not result.success:
            raise ValueError(result.error)
        return result.data

    def register(self, data: dict) -> dict:
        """Public registration. Raises ValueError on duplicate username or email."""
        try:
            return self.create(data)
        except IntegrityError as exc:
            # Use orig (the raw DB error) for precise column detection; the full
            # SQLAlchemy message always includes the INSERT column list, which
            # makes "username" appear even for email-constraint violations.
            orig = str(exc.orig).lower()
            if "email" in orig:
                raise ValueError("Email already registered") from exc
            if "username" in orig:
                raise ValueError("Username already registered") from exc
            raise

    def request_reset(self, data: dict) -> dict:
        """Request a password reset token. Returns generic message for unknown emails."""
        email = data.get("email", "")
        if not email:
            raise ValueError("email is required")

        repo = UserRepository(self._factory)
        token_repo = PasswordResetTokenRepository(self._factory)

        users = repo.filter_by(email=email)
        if not users:
            return {"message": "If that email is registered, a reset token has been issued"}

        user_id = users[0]["id"]   # uuid.UUID directly from _serialize — do NOT wrap in uuid.UUID()
        token_str = token_repo.create_for_user(user_id)
        return {"token": token_str, "expires_in": 900}

    def reset_password(self, data: dict) -> dict:
        """Reset a user's password using a valid reset token. Raises ValueError if invalid/expired."""
        token_repo = PasswordResetTokenRepository(self._factory)
        token_row = token_repo.find_valid(data["token"])
        if token_row is None:
            raise ValueError("Invalid or expired reset token")

        if not data.get("new_password"):
            raise ValueError("new_password is required")

        # Mark token used FIRST — prevents reuse even if password update fails
        token_repo.mark_used(uuid.UUID(token_row["id"]))

        password_hash, salt = hash_password(data["new_password"])
        user_repo = UserRepository(self._factory)
        user_repo.update(uuid.UUID(token_row["user_id"]), {
            "password_hash": password_hash,
            "salt": salt,
        })
        return {"success": True}
