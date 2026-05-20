# tests/test_rbac.py
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from lib.auth.jwt_handler import create_token


def _app_with(dependency):
    app = FastAPI()

    @app.get("/protected")
    def protected(user=Depends(dependency)):
        return {"user_id": user["id"], "roles": user["roles"]}

    return app


def test_get_current_user_valid_token():
    from lib.auth.dependencies import get_current_user
    app = _app_with(get_current_user)
    token = create_token({"sub": "uid-1", "roles": ["admin"]})
    resp = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["user_id"] == "uid-1"
    assert resp.json()["roles"] == ["admin"]


def test_get_current_user_no_token_returns_401():
    from lib.auth.dependencies import get_current_user
    app = _app_with(get_current_user)
    resp = TestClient(app).get("/protected")
    assert resp.status_code == 401  # OAuth2PasswordBearer returns 401 (not 403)


def test_get_current_user_bad_token_returns_401():
    from lib.auth.dependencies import get_current_user
    app = _app_with(get_current_user)
    resp = TestClient(app).get("/protected", headers={"Authorization": "Bearer garbage"})
    assert resp.status_code == 401


def test_require_roles_passes_matching_role():
    from lib.auth.dependencies import require_roles
    app = _app_with(require_roles("admin"))
    token = create_token({"sub": "uid-2", "roles": ["admin", "viewer"]})
    resp = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_require_roles_rejects_wrong_role():
    from lib.auth.dependencies import require_roles
    app = _app_with(require_roles("superadmin"))
    token = create_token({"sub": "uid-3", "roles": ["admin"]})
    resp = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_require_roles_accepts_any_of_multiple():
    from lib.auth.dependencies import require_roles
    app = _app_with(require_roles("superadmin", "admin"))
    token = create_token({"sub": "uid-4", "roles": ["admin"]})
    resp = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_get_current_user_token_missing_sub_returns_401():
    from lib.auth.jwt_handler import create_token
    from lib.auth.dependencies import get_current_user
    app = _app_with(get_current_user)
    # A valid signed token that has no 'sub' claim
    token = create_token({"roles": ["admin"]})  # no 'sub'
    resp = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
