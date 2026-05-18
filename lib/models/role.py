import uuid
from typing import TYPE_CHECKING, List

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from lib.database.base import Base

if TYPE_CHECKING:
    from lib.models.user import User


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=True)

    # Relationship (inverse side)
    users: Mapped[List["User"]] = relationship(
        "User",
        back_populates="roles",
        secondary="user_roles",
        cascade="all, delete",
    )
