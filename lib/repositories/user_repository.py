from lib.repositories.base import AbstractRepository
from lib.models.user import User


class UserRepository(AbstractRepository[User]):
    model = User
