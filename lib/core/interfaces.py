from abc import ABC, abstractmethod
from lib.contracts.base import ActionRequest, ActionResult


class IService(ABC):
    @abstractmethod
    def execute(self, request: ActionRequest) -> ActionResult: ...


class SimpleService(IService):
    """Route ActionRequests to same-named methods automatically.

    Define one method per action. Return a plain dict (auto-wrapped into
    ActionResult) or an ActionResult directly. Any exception becomes a
    failed ActionResult so callers never see raw tracebacks.

    Example:
        class OrderService(SimpleService):
            def create(self, data: dict) -> dict:
                return {"order_id": db.insert(data)}

            def cancel(self, data: dict) -> dict:
                db.delete(data["order_id"])
                return {}

        # Called exactly like any other IService:
        service.execute(ActionRequest(action="create", data={...}))
    """

    def execute(self, request: ActionRequest) -> ActionResult:
        if not request.action or request.action.startswith("_"):
            return ActionResult(success=False, error=f"Unknown action: {request.action}")

        handler = getattr(self, request.action, None)
        if not callable(handler):
            return ActionResult(success=False, error=f"Unknown action: {request.action}")

        try:
            result = handler(request.data)
            if isinstance(result, ActionResult):
                return result
            if isinstance(result, dict):
                return ActionResult(success=True, data=result)
            return ActionResult(success=True)
        except Exception as exc:
            return ActionResult(success=False, error=str(exc))


class IRepository(ABC):
    @abstractmethod
    def get(self, id: int): ...

    @abstractmethod
    def list(self, **filters): ...

    @abstractmethod
    def create(self, data: dict): ...

    @abstractmethod
    def update(self, id: int, data: dict): ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...


class INavigationAdapter(ABC):
    @abstractmethod
    def navigate_to(self, url: str) -> None: ...

    @abstractmethod
    def get_current_route(self) -> str: ...


class IErrorAdapter(ABC):
    @abstractmethod
    def show_error(self, message: str, fatal: bool = False) -> None: ...


class IFlexComponent(ABC):
    @abstractmethod
    def build(self) -> object: ...
