"""ORM model tests — Role model and User-Role many-to-many relationship."""
from lib.models.role import Role
from lib.models.user import User


def test_role_model_creation():
    role = Role(name="admin", description="Administrator role")
    assert role.name == "admin"
    assert role.description == "Administrator role"


def test_user_has_many_roles():
    user = User(username="alice", email="alice@example.com")
    role1 = Role(name="admin", description="Admin role")
    role2 = Role(name="editor", description="Editor role")
    user.roles.append(role1)
    user.roles.append(role2)
    assert len(user.roles) == 2
