
from sqlalchemy.orm import Session

from src.models.user import User

from src.middleware.security import Security

class UserController:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def add_user(self, username: str, email: str, password: str) -> User:
        salt = Security.generate_salt()
        password_hash = Security.hash_password(password,salt)
        user = User(username=username, email=email, password_hash=password_hash, salt=salt)
        self.db_session.add(user)
        self.db_session.commit()
        return user

