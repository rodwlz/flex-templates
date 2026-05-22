"""HTTP implementation of IUserAdapter."""
from __future__ import annotations

from lib.adapters.users_adapter import IUserAdapter
from lib.adapters.http_session import _HttpSession


class HttpUserAdapter(IUserAdapter):
    def __init__(self, session: _HttpSession):
        self._session = session

    def list(self, page: int = 1, page_size: int = 20) -> dict:
        skip = (page - 1) * page_size
        resp = self._session.request(
            "GET", "/v1/users/",
            params={"skip": skip, "limit": page_size},
        )
        resp.raise_for_status()
        body = resp.json()
        users = body.get("users", [])
        total = body.get("total", len(users))
        pages = max(1, (total + page_size - 1) // page_size)
        return {
            "items": users,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages,
        }

    def create(self, data: dict) -> dict:
        resp = self._session.request("POST", "/v1/users/", json=data)
        resp.raise_for_status()
        return resp.json()

    def delete(self, user_id: str) -> bool:
        resp = self._session.request("DELETE", f"/v1/users/{user_id}")
        return resp.status_code == 200
