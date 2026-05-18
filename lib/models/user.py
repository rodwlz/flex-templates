import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import Column, ForeignKey, String, Table, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.database.base import Base

if TYPE_CHECKING:
    from lib.models.role import Role


# Association table for the User ↔ Role many-to-many relationship.
# Must be defined at module level, before the User class.
user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Uuid, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", Uuid, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=True)
    salt: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="base-user")

    # Many-to-many: a user can have multiple roles
    roles: Mapped[List["Role"]] = relationship(
        "Role",
        back_populates="users",
        secondary="user_roles",
        cascade="all, delete",
        lazy="joined",
    )
