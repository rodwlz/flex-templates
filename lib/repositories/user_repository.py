import uuid

from lib.repositories.base import AbstractRepository
from lib.models.user import User
from lib.models.role import Role


class UserRepository(AbstractRepository[User]):
    model = User

    def add_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Add a role to a user. Returns True if added, False if user/role not found or already assigned."""
        with self._factory.session() as s:
            user = s.get(self.model, user_id)
            role = s.get(Role, role_id)
            if not (user and role):
                return False
            if role not in user.roles:
                user.roles.append(role)
                return True
            return False  # Already assigned

    def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Remove a role from a user. Returns True if removed, False if user not found or role wasn't assigned."""
        with self._factory.session() as s:
            user = s.get(self.model, user_id)
            if not user:
                return False
            before_count = len(user.roles)
            user.roles = [r for r in user.roles if r.id != role_id]
            return len(user.roles) < before_count  # True only if a role was actually removed

    def find_for_auth(self, login: str) -> dict | None:
        """Find user by username or email, return dict for auth (no detached ORM objects)."""
        with self._factory.session() as s:
            user = s.query(User).filter(User.username == login).first()
            if user is None:
                user = s.query(User).filter(User.email == login).first()
            if user is None:
                return None
            return {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "password_hash": user.password_hash,
                "roles": [r.name for r in user.roles],
            }

    def list_by_role(self, role_name: str) -> list[User]:
        """List all users with a specific role."""
        with self._factory.session() as s:
            return s.query(self.model).join(Role, self.model.roles).filter(Role.name == role_name).all()
