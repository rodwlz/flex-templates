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


class StagingService(SimpleService):
    """Base for services that need preview-before-commit (multi-step forms, order confirmations).

    Views always call the same three actions regardless of which service:
        action="stage"   → stages changes, returns {"preview": diff, **custom_data}
        action="confirm" → commits
        action="cancel"  → rolls back (idempotent)

    Services only override _stage_impl(uow, data) which returns a dict.

    Example:
        class UserService(StagingService):
            def _stage_impl(self, uow, data):
                repo = uow.repo(UserRepository)
                user = repo.create(data)
                return {"user": {"id": user.id}}

    All exceptions raised by _stage_impl, commit(), or rollback() become
    ActionResult(success=False, error=...) automatically.
    """

    def __init__(self, factory):
        self._factory = factory
        self._pending = None

    def _stage_impl(self, uow, data: dict) -> dict:
        """Override this. Use uow.repo(MyRepo) to stage work.
        Returned dict is merged into ActionResult.data."""
        raise NotImplementedError

    def stage(self, data: dict) -> dict:
        if self._pending:
            self._pending.rollback()
            self._pending.close()
            self._pending = None
        uow = self._factory.unit_of_work()
        result = self._stage_impl(uow, data)
        diff = uow.stage()
        self._pending = uow
        return {"preview": diff, **result}

    def confirm(self, data: dict) -> dict:
        if self._pending is None:
            raise RuntimeError("Nothing to confirm — call stage first")
        try:
            self._pending.commit()
            return {"confirmed": True}
        except Exception as e:
            self._pending.rollback()
            raise RuntimeError(f"Commit failed: {e}") from e
        finally:
            self._pending.close()
            self._pending = None

    def cancel(self, data: dict) -> dict:
        if self._pending:
            self._pending.rollback()
            self._pending.close()
            self._pending = None
        return {"cancelled": True}


class IRepository(ABC):
    @abstractmethod
    def get(self, id): ...

    @abstractmethod
    def list(self, **filters): ...

    @abstractmethod
    def create(self, data: dict): ...

    @abstractmethod
    def update(self, id, data: dict): ...

    @abstractmethod
    def delete(self, id) -> bool: ...

    @abstractmethod
    def paginate(self, page: int = 1, page_size: int = 20, **filters) -> dict: ...

    @abstractmethod
    def filter_by(self, **specs) -> list: ...


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
