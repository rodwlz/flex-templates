from lib.services.role_service import RoleService
from lib.services.user_service import UserService
from lib.contracts.base import ActionRequest


def test_role_service_create(db_factory):
    service = RoleService(db_factory)
    result = service.execute(ActionRequest(
        action="create",
        data={"name": "admin", "description": "Administrator"}
    ))
    assert result.success is True
    assert result.data["name"] == "admin"


def test_role_service_get(db_factory):
    service = RoleService(db_factory)
    create_result = service.execute(ActionRequest(
        action="create",
        data={"name": "editor", "description": "Editor"}
    ))
    role_id = create_result.data["id"]

    get_result = service.execute(ActionRequest(
        action="get",
        data={"id": role_id}
    ))
    assert get_result.success is True
    assert get_result.data["name"] == "editor"


def test_role_service_list(db_factory):
    service = RoleService(db_factory)
    service.execute(ActionRequest(action="create", data={"name": "admin", "description": "Admin"}))
    service.execute(ActionRequest(action="create", data={"name": "editor", "description": "Editor"}))

    result = service.execute(ActionRequest(action="list", data={}))
    assert result.success is True
    assert len(result.data["roles"]) == 2


def test_role_service_delete(db_factory):
    service = RoleService(db_factory)
    create_result = service.execute(ActionRequest(
        action="create",
        data={"name": "viewer", "description": "Viewer"}
    ))
    role_id = create_result.data["id"]

    delete_result = service.execute(ActionRequest(
        action="delete",
        data={"id": role_id}
    ))
    assert delete_result.success is True


def test_user_service_simple_create(db_factory):
    """Simple create - immediate commit, no preview."""
    service = UserService(db_factory)
    result = service.execute(ActionRequest(
        action="create",
        data={"username": "alice", "email": "alice@example.com", "password_hash": "hash", "salt": "salt"}
    ))
    assert result.success is True
    assert result.data["username"] == "alice"


def test_user_service_create_with_roles_staged(db_factory):
    """Staged create - preview before commit, with relationships."""
    service = UserService(db_factory)

    # Create roles first
    role_service = RoleService(db_factory)
    admin_result = role_service.execute(ActionRequest(
        action="create",
        data={"name": "admin", "description": "Admin"}
    ))
    admin_id = admin_result.data["id"]

    # Stage create with roles
    result = service.execute(ActionRequest(
        action="stage",
        data={
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": "hash",
            "salt": "salt",
            "role_ids": [admin_id]
        }
    ))
    assert result.success is True
    assert "preview" in result.data
    assert "new" in result.data["preview"]

    # Confirm
    confirm_result = service.execute(ActionRequest(action="confirm", data={}))
    assert confirm_result.success is True

    # Verify it's in DB
    user_id = result.data["preview"]["new"][0]["id"]
    get_result = service.execute(ActionRequest(
        action="get",
        data={"id": str(user_id)}
    ))
    assert get_result.success is True
    assert len(get_result.data["roles"]) == 1


def test_user_service_stage_can_cancel(db_factory):
    """Cancel a staged operation."""
    service = UserService(db_factory)

    # Stage
    stage_result = service.execute(ActionRequest(
        action="stage",
        data={
            "username": "charlie",
            "email": "charlie@example.com",
            "password_hash": "hash",
            "salt": "salt",
            "role_ids": []
        }
    ))
    assert stage_result.success is True

    # Cancel
    cancel_result = service.execute(ActionRequest(action="cancel", data={}))
    assert cancel_result.success is True

    # Verify user not created
    list_result = service.execute(ActionRequest(action="list", data={}))
    assert len(list_result.data["users"]) == 0


def test_create_with_plain_password_hashes_it(db_factory):
    from lib.services.user_service import UserService
    from lib.contracts.base import ActionRequest
    from lib.security.password import verify_password

    service = UserService(db_factory)
    result = service.execute(ActionRequest(action="create", data={
        "username": "authuser1", "email": "authuser1@test.com", "password": "hunter2",
    }))
    assert result.success
    from lib.repositories.user_repository import UserRepository
    repo = UserRepository(db_factory)
    users = repo.list(username="authuser1")
    assert users and verify_password("hunter2", users[0].password_hash)


def test_authenticate_success(db_factory):
    from lib.services.user_service import UserService
    from lib.contracts.base import ActionRequest

    service = UserService(db_factory)
    service.execute(ActionRequest(action="create", data={
        "username": "authuser2", "email": "authuser2@test.com", "password": "secret",
    }))
    result = service.execute(ActionRequest(action="authenticate", data={
        "username": "authuser2", "password": "secret",
    }))
    assert result.success
    assert result.data["username"] == "authuser2"
    assert "roles" in result.data


def test_authenticate_wrong_password(db_factory):
    from lib.services.user_service import UserService
    from lib.contracts.base import ActionRequest

    service = UserService(db_factory)
    service.execute(ActionRequest(action="create", data={
        "username": "authuser3", "email": "authuser3@test.com", "password": "correct",
    }))
    result = service.execute(ActionRequest(action="authenticate", data={
        "username": "authuser3", "password": "wrong",
    }))
    assert not result.success
    assert "Invalid credentials" in result.error


def test_authenticate_unknown_user(db_factory):
    from lib.services.user_service import UserService
    from lib.contracts.base import ActionRequest

    service = UserService(db_factory)
    result = service.execute(ActionRequest(action="authenticate", data={
        "username": "nobody", "password": "secret",
    }))
    assert not result.success


def test_authenticate_by_email(db_factory):
    from lib.services.user_service import UserService
    from lib.contracts.base import ActionRequest

    service = UserService(db_factory)
    service.execute(ActionRequest(action="create", data={
        "username": "authuser5", "email": "authuser5@test.com", "password": "emailpass",
    }))
    result = service.execute(ActionRequest(action="authenticate", data={
        "username": "authuser5@test.com", "password": "emailpass",
    }))
    assert result.success
    assert result.data["username"] == "authuser5"


def test_authenticate_user_wrapper_raises_on_bad_creds(db_factory):
    import pytest
    from lib.services.user_service import UserService

    service = UserService(db_factory)
    with pytest.raises(ValueError, match="Invalid credentials"):
        service.authenticate_user("nobody_at_all", "wrong")
