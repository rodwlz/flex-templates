import uuid

from lib.repositories.base import AbstractRepository
from lib.models.user import User
from lib.models.role import Role


class UserRepository(AbstractRepository[User]):
    model = User

    def add_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> None:
        """Add a role to a user."""
        with self._factory.session() as s:
            user = s.get(self.model, user_id)
            role = s.query(Role).filter(Role.id == role_id).first()
            if user and role:
                user.roles.append(role)

    def remove_role(self, user_id: uuid.UUID, role_id: uuid.UUID) -> bool:
        """Remove a role from a user. Returns True if removed, False if not found."""
        with self._factory.session() as s:
            user = s.get(self.model, user_id)
            if user:
                user.roles = [r for r in user.roles if r.id != role_id]
                return True
            return False

    def list_by_role(self, role_name: str) -> list[User]:
        """List all users with a specific role."""
        with self._factory.session() as s:
            return s.query(self.model).join(Role, self.model.roles).filter(Role.name == role_name).all()
