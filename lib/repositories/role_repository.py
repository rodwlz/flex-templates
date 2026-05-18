from lib.models.role import Role
from lib.repositories.base import AbstractRepository


class RoleRepository(AbstractRepository[Role]):
    model = Role
