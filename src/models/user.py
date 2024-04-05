import secrets
from sqlalchemy import Column, Integer, String
from src.database.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    salt = Column(String(4), nullable=False, default=lambda: secrets.token_hex(2))

