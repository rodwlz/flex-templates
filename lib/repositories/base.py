from typing import TypeVar, Generic
from lib.core.interfaces import IRepository
from lib.database.session import SessionFactory

T = TypeVar("T")


class AbstractRepository(IRepository, Generic[T]):
    model: type[T]

    def __init__(self, factory: SessionFactory):
        self._factory = factory

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
            obj = self.model(**data)
            s.add(obj)
            s.flush()
            return obj

    def update(self, id, data: dict) -> T | None:
        with self._factory.session() as s:
            obj = s.get(self.model, id)
            if obj is None:
                return None
            for k, v in data.items():
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
                "items":     list of ORM objects for this page,
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
            items = q.offset((page - 1) * page_size).limit(page_size).all()
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": max(1, (total + page_size - 1) // page_size),
            }

    def filter_by(self, **specs) -> list:
        raise NotImplementedError("filter_by not yet implemented")
