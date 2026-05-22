"""HTTP implementation of ISchedulerAdapter."""
from __future__ import annotations

from lib.adapters.scheduler_adapter import ISchedulerAdapter
from lib.adapters.http_session import _HttpSession


class HttpSchedulerAdapter(ISchedulerAdapter):
    def __init__(self, session: _HttpSession):
        self._session = session

    def list(self) -> list[dict]:
        resp = self._session.request("GET", "/v1/scheduler/jobs")
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        return resp.json()
