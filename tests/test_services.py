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
