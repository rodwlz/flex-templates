"""
BackendServer — runs Uvicorn in a daemon thread alongside Flet.

Both share the same Python process and ConnectionRegistry, so the HTTP API
sees the same database connections as the UI. `daemon=True` means the thread
exits automatically when Flet (the main thread) exits — `stop()` is only
needed for clean shutdown during dev/tests.
"""
from __future__ import annotations

import threading
import uvicorn
from fastapi import FastAPI

from lib.api.router_registry import mount_routes


def create_app() -> FastAPI:
    """Create and return a FastAPI application with all routes mounted."""
    app = FastAPI()
    mount_routes(app)
    return app


class BackendServer:
    def __init__(self, app: FastAPI, host: str = "127.0.0.1", port: int = 8080):
        self._config = uvicorn.Config(app, host=host, port=port, log_level="warning")
        self._server = uvicorn.Server(self._config)
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)

    def wait(self) -> None:
        """Block until the server thread exits. Use instead of server._thread.join()."""
        if self._thread:
            self._thread.join()
