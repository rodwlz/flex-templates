from typing import TypeVar, Generic
from sqlalchemy import inspect as sa_inspect
from lib.core.interfaces import IRepository
from lib.database.session import SessionFactory

T = TypeVar("T")

_FILTER_OPS = frozenset({"like", "gte", "lte", "gt", "lt", "in", "ne"})


class AbstractRepository(IRepository, Generic[T]):
    model: type[T]

    def __init__(self, factory: SessionFactory):
        self._factory = factory

    # ── Serialization hooks ───────────────────────────────────────────────────

    def _serialize(self, obj: T) -> dict:
        """Outbound: ORM object → dict. Override to add relationship fields."""
        return {c.key: getattr(obj, c.key)
                for c in sa_inspect(obj).mapper.column_attrs}

    def _deserialize(self, data: dict) -> dict:
        """Inbound: strip unknown keys. Override to add type coercion on top."""
        known = {c.key for c in sa_inspect(self.model).mapper.column_attrs}
        return {k: v for k, v in data.items() if k in known}

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def get(self, id) -> T | None:
        with self._factory.session() as s:
            return s.get(self.model, id)

    def list(self, **filters) -> list[T]:
        with self._factory.session() as s:
            q = s.query(self.model)
            for k, v in filters.items():
                q = q.filter(getattr(self.model, k) == v)
            return q.all()

    def create(self, data: dict) -> T:
        with self._factory.session() as s:
            obj = self.model(**self._deserialize(data))
            s.add(obj)
            s.flush()
            return obj

    def update(self, id, data: dict) -> T | None:
        with self._factory.session() as s:
            obj = s.get(self.model, id)
            if obj is None:
                return None
            for k, v in self._deserialize(data).items():
                setattr(obj, k, v)
            s.flush()
            return obj

    def delete(self, id) -> bool:
        with self._factory.session() as s:
            obj = s.get(self.model, id)
            if obj is None:
                return False
            s.delete(obj)
            return True

    def paginate(self, page: int = 1, page_size: int = 20, **filters) -> dict:
        """Return one page of results with metadata.

        Returns:
            {
                "items":     list of serialized dicts for this page,
                "total":     total matching rows (ignoring pagination),
                "page":      current page number (1-based),
                "page_size": rows per page,
                "pages":     total number of pages,
            }
        """
        with self._factory.session() as s:
            q = s.query(self.model)
            for k, v in filters.items():
                q = q.filter(getattr(self.model, k) == v)
            total = q.count()
            rows = q.offset((page - 1) * page_size).limit(page_size).all()
            items = [self._serialize(r) for r in rows]
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            }

    def filter_by(self, **specs) -> list:
        """Query with Django-style lookup operators.

        Supported suffixes (after __):
            like  — SQL LIKE pattern  (e.g. username__like="ali%")
            gte   — >=               (e.g. created_at__gte=some_date)
            lte   — <=
            gt    — >
            lt    — <
            in    — IN list          (e.g. status__in=["active", "pending"])
            ne    — !=

        Plain kwargs remain exact-match (e.g. username="alice").

        Raises ValueError for unknown operators.
        """
        with self._factory.session() as s:
            q = s.query(self.model)
            for spec, value in specs.items():
                if "__" in spec:
                    field_name, _, op = spec.rpartition("__")
                    if op not in _FILTER_OPS:
                        raise ValueError(
                            f"Unknown filter operator {op!r}. "
                            f"Use one of: {', '.join(sorted(_FILTER_OPS))}"
                        )
                    col = getattr(self.model, field_name)
                    if op == "like":
                        q = q.filter(col.like(value))
                    elif op == "gte":
                        q = q.filter(col >= value)
                    elif op == "lte":
                        q = q.filter(col <= value)
                    elif op == "gt":
                        q = q.filter(col > value)
                    elif op == "lt":
                        q = q.filter(col < value)
                    elif op == "in":
                        q = q.filter(col.in_(value))
                    elif op == "ne":
                        q = q.filter(col != value)
                else:
                    q = q.filter(getattr(self.model, spec) == value)
            return [self._serialize(r) for r in q.all()]
