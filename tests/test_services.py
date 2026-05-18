from lib.services.role_service import RoleService
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
