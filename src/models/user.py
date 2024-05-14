from sqlalchemy import Column, Integer, String
from src.database.base_class import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True,autoincrement=True,unique=True)
    username = Column(String, unique=True, index=True,nullable=False)
    email = Column(String, unique=True, index=True,nullable=False)
    password_hash = Column(String,nullable=False)
    salt = Column(String(4), nullable=False)
    status = Column(String,default='base-user')

