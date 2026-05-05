"""SessionFactory and ConnectionRegistry contract.

The data layer's foundation: SessionFactory wraps a SQLAlchemy engine + session
maker, ConnectionRegistry stores named factories. Almost every other test
exercises this code through a fixture, but the registry's edge cases and the
session context manager's commit/rollback semantics deserve their own
dedicated tests — read these for the authoritative behaviour spec.
"""
import pytest

from lib.database.session import (
    ConnectionRegistry,
    SessionFactory,
    _CONNECT_TIMEOUT_SECONDS,
    _engine_kwargs,
)


@pytest.fixture(autouse=True)
def isolate_registry():
    """Each test runs against an empty registry, restored on exit."""
    saved = dict(ConnectionRegistry._factories)
    ConnectionRegistry._factories = {}
    yield
    ConnectionRegistry._factories = saved


# ── ConnectionRegistry — named-factory storage ────────────────────────────

def test_register_then_get_returns_same_factory():
    ConnectionRegistry.register("sqlite:///:memory:", name="alpha")
    assert isinstance(ConnectionRegistry.get("alpha"), SessionFactory)


def test_get_unknown_name_raises_runtime_error():
    with pytest.raises(RuntimeError, match="No database registered as 'ghost'"):
        ConnectionRegistry.get("ghost")


def test_register_with_same_name_overwrites():
    ConnectionRegistry.register("sqlite:///:memory:", name="dup")
    first = ConnectionRegistry.get("dup")
    ConnectionRegistry.register("sqlite:///:memory:", name="dup")
    second = ConnectionRegistry.get("dup")
    # Overwrite is the documented behaviour — re-registering replaces silently.
    assert second is not first


def test_list_returns_all_registered_names():
    ConnectionRegistry.register("sqlite:///:memory:", name="a")
    ConnectionRegistry.register("sqlite:///:memory:", name="b")
    ConnectionRegistry.register("sqlite:///:memory:", name="c")
    assert sorted(ConnectionRegistry.list()) == ["a", "b", "c"]


def test_list_empty_when_nothing_registered():
    assert ConnectionRegistry.list() == []


def test_default_name_is_postgres():
    """register() and get() both default to 'postgres' (the canonical app DB)."""
    ConnectionRegistry.register("sqlite:///:memory:")  # no name -> "postgres"
    assert "postgres" in ConnectionRegistry.list()
    assert ConnectionRegistry.get() is ConnectionRegistry.get("postgres")


# ── SessionFactory.session() — commit / rollback / close ──────────────────

def test_session_commits_on_clean_exit(db_factory):
    """Successful exit from the context manager triggers commit."""
    from lib.models.user import User

    with db_factory.session() as s:
        s.add(User(username="u1", email="u1@x", password_hash="h", salt="s"))
    # If commit didn't fire, this fresh session would see zero rows.
    with db_factory.session() as s:
        assert s.query(User).count() == 1


def test_session_rolls_back_on_exception(db_factory):
    """Exception inside the context manager triggers rollback and re-raises."""
    from lib.models.user import User

    with pytest.raises(RuntimeError, match="boom"):
        with db_factory.session() as s:
            s.add(User(username="u2", email="u2@x", password_hash="h", salt="s"))
            raise RuntimeError("boom")
    # Rollback ran -> zero rows.
    with db_factory.session() as s:
        assert s.query(User).count() == 0


def test_session_closes_even_on_exception(db_factory, monkeypatch):
    """The session must close in the finally branch regardless of outcome."""
    closed: list[bool] = []
    real_session_cls = db_factory._Session

    def spy_factory():
        s = real_session_cls()
        original_close = s.close

        def spy_close(*a, **kw):
            closed.append(True)
            return original_close(*a, **kw)

        s.close = spy_close
        return s

    monkeypatch.setattr(db_factory, "_Session", spy_factory)

    try:
        with db_factory.session():
            raise RuntimeError("x")
    except RuntimeError:
        pass
    assert closed == [True]


# ── _engine_kwargs — connect-timeout policy ───────────────────────────────

def test_engine_kwargs_adds_timeout_for_postgres():
    kw = _engine_kwargs("postgresql://u:p@host/db", echo=False)
    assert kw["connect_args"] == {"connect_timeout": _CONNECT_TIMEOUT_SECONDS}
    assert kw["echo"] is False


def test_engine_kwargs_adds_timeout_for_postgres_short_scheme():
    kw = _engine_kwargs("postgres://u:p@host/db", echo=False)
    assert kw["connect_args"] == {"connect_timeout": _CONNECT_TIMEOUT_SECONDS}


def test_engine_kwargs_adds_timeout_for_mysql():
    kw = _engine_kwargs("mysql+pymysql://u:p@host/db", echo=False)
    assert kw["connect_args"] == {"connect_timeout": _CONNECT_TIMEOUT_SECONDS}


def test_engine_kwargs_omits_timeout_for_sqlite():
    """SQLite has no socket — connect_timeout would be a SQLAlchemy error."""
    kw = _engine_kwargs("sqlite:///:memory:", echo=False)
    assert "connect_args" not in kw


def test_engine_kwargs_passes_echo_through():
    assert _engine_kwargs("sqlite:///:memory:", echo=True)["echo"] is True
    assert _engine_kwargs("sqlite:///:memory:", echo=False)["echo"] is False


def test_connect_timeout_constant_is_reasonable():
    """Sanity-pin: a too-long timeout would block the admin views."""
    assert 1 <= _CONNECT_TIMEOUT_SECONDS <= 30
