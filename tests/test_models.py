"""ORM model tests — Role model and User-Role many-to-many relationship."""
from lib.models.role import Role
from lib.models.user import User


def test_role_model_creation():
    role = Role(name="admin", description="Administrator role")
    assert role.name == "admin"
    assert role.description == "Administrator role"


def test_user_has_many_roles():
    user = User(
        username="alice",
        email="alice@example.com",
        password_hash="hashed_pwd",
        salt="salt123",
    )
    role1 = Role(name="admin", description="Admin role")
    role2 = Role(name="editor", description="Editor role")
    user.roles.append(role1)
    user.roles.append(role2)
    assert len(user.roles) == 2


def test_user_roles_persist_and_roundtrip(db_factory):
    """Verify user-role relationship persists and retrieves correctly."""
    with db_factory.session() as s:
        user = User(
            username="bob",
            email="bob@example.com",
            password_hash="pwd",
            salt="salt",
        )
        role = Role(name="admin", description="Admin role")
        user.roles.append(role)
        s.add(user)
        s.add(role)
        s.flush()
        user_id = user.id

    with db_factory.session() as s:
        user = s.get(User, user_id)
        assert user is not None
        assert len(user.roles) == 1
        assert user.roles[0].name == "admin"


def test_role_name_unique_constraint(db_factory):
    """Verify Role.name unique constraint is enforced."""
    from sqlalchemy.exc import IntegrityError

    # Persist the first role in its own committed session.
    with db_factory.session() as s:
        role1 = Role(name="admin", description="Admin role")
        s.add(role1)

    # Attempting to insert a duplicate name must raise IntegrityError.
    # Let the exception propagate so the session context manager's rollback
    # path fires cleanly (catching inside the `with` leaves the session in a
    # PendingRollback state that causes a second error on commit).
    raised = False
    try:
        with db_factory.session() as s:
            role2 = Role(name="admin", description="Another admin")
            s.add(role2)
            s.flush()
    except IntegrityError:
        raised = True

    assert raised, "Should have raised IntegrityError for duplicate Role.name"
