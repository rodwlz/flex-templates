from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy import inspect as sa_inspect, event as sa_event


class _SessionProxy:
    """Wraps a session, making commit/rollback/close no-ops so UoW controls them.
    flush() is allowed through so repos can get auto-assigned IDs within the transaction."""

    def __init__(self, session: Session):
        self._session = session

    def __getattr__(self, name):
        return getattr(self._session, name)

    def add(self, obj):
        self._session.add(obj)

    def commit(self):
        """No-op — UoW controls commit."""
        pass

    def rollback(self):
        """No-op — UoW controls rollback."""
        pass

    def close(self):
        """No-op — UoW controls close."""
        pass


class _BoundSession:
    """Duck-type SessionFactory wrapper — yields a proxied session where commit/rollback/close are no-ops."""

    def __init__(self, session: Session):
        self._session = session

    @contextmanager
    def session(self):
        yield _SessionProxy(self._session)


def _row_to_dict(obj) -> dict:
    """Convert an ORM object to a dict (all column values)."""
    insp = sa_inspect(obj)
    return {c.key: getattr(obj, c.key) for c in insp.mapper.column_attrs}


class UnitOfWork:
    """Long-lived transaction that repos can share. Caller controls commit/rollback."""

    def __init__(self, session: Session):
        self._s = session
        self._committed = False
        self._pending_new: list = []
        self._pending_dirty: list = []
        self._pending_deleted: list = []

        # Capture objects before each flush so they're tracked even if flush is
        # called by a repo (which moves them out of session.new afterward).
        @sa_event.listens_for(session, "before_flush")
        def _capture(sess, flush_ctx, instances):
            for o in sess.new:
                if o not in self._pending_new:
                    self._pending_new.append(o)
            for o in sess.dirty:
                if o not in self._pending_dirty:
                    self._pending_dirty.append(o)
            for o in sess.deleted:
                if o not in self._pending_deleted:
                    self._pending_deleted.append(o)

    def repo(self, repo_class: type):
        """Return an instance of repo_class wired to this transaction's session."""
        return repo_class(_BoundSession(self._s))

    def stage(self) -> dict:
        """Flush pending changes (assigns IDs) and return a diff for preview."""
        self._s.flush()
        return {
            "new": [_row_to_dict(o) for o in self._pending_new],
            "modified": [_row_to_dict(o) for o in self._pending_dirty],
            "deleted": [{"id": getattr(o, "id", None), "type": type(o).__name__}
                        for o in self._pending_deleted],
        }

    def commit(self):
        """Commit the transaction."""
        self._s.commit()
        self._committed = True

    def rollback(self):
        """Rollback the transaction."""
        self._s.rollback()

    def close(self):
        """Close the session (no commit/rollback)."""
        self._s.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, *_):
        if exc_type is not None or not self._committed:
            self._s.rollback()
        self._s.close()
