"""HTTP implementation of IRoleAdapter."""
from __future__ import annotations

from lib.adapters.roles_adapter import IRoleAdapter
from lib.adapters.http_session import _HttpSession


class HttpRoleAdapter(IRoleAdapter):
    def __init__(self, session: _HttpSession):
        self._session = session

    def list(self) -> list[dict]:
        resp = self._session.request("GET", "/v1/roles/")
        resp.raise_for_status()
        return resp.json().get("roles", [])

    def create(self, name: str) -> dict:
        resp = self._session.request("POST", "/v1/roles/", json={"name": name})
        resp.raise_for_status()
        return resp.json()

    def delete(self, role_id: str) -> bool:
        resp = self._session.request("DELETE", f"/v1/roles/{role_id}")
        return resp.status_code == 200

    def assign(self, user_id: str, role_id: str) -> bool:
        resp = self._session.request(
            "POST", "/v1/roles/assign",
            json={"user_id": user_id, "role_id": role_id},
        )
        return resp.status_code == 200

    def remove(self, user_id: str, role_id: str) -> bool:
        resp = self._session.request(
            "DELETE", "/v1/roles/remove",
            json={"user_id": user_id, "role_id": role_id},
        )
        return resp.status_code == 200
