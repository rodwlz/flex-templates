from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def _engine_kwargs(url: str, echo: bool) -> dict:
    """Build create_engine kwargs — adds connect_timeout for network DBs."""
    kwargs: dict = {"echo": echo}
    if url.startswith(("postgresql", "postgres", "mysql")):
        kwargs["connect_args"] = {"connect_timeout": 5}
    return kwargs


class SessionFactory:
    def __init__(self, url: str, echo: bool = False):
        self._engine = create_engine(url, **_engine_kwargs(url, echo))
        self._Session = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=self._engine)

    @contextmanager
    def session(self):
        s = self._Session()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    def create_tables(self, base):
        base.metadata.create_all(bind=self._engine)

    def unit_of_work(self):
        from lib.database.uow import UnitOfWork
        return UnitOfWork(self._Session())


class ConnectionRegistry:
    _factories: dict[str, SessionFactory] = {}

    @classmethod
    def register(cls, url: str, name: str = "postgres", echo: bool = False):
        cls._factories[name] = SessionFactory(url, echo=echo)

    @classmethod
    def get(cls, name: str = "postgres") -> SessionFactory:
        if name not in cls._factories:
            raise RuntimeError(f"No database registered as {name!r}")
        return cls._factories[name]

    @classmethod
    def list(cls) -> list[str]:
        return list(cls._factories.keys())
