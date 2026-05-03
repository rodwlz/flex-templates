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
            s.commit()
            return obj

    def update(self, id, data: dict) -> T | None:
        with self._factory.session() as s:
            obj = s.get(self.model, id)
            if obj is None:
                return None
            for k, v in data.items():
                setattr(obj, k, v)
            s.flush()
            s.commit()
            return obj

    def delete(self, id) -> bool:
        with self._factory.session() as s:
            obj = s.get(self.model, id)
            if obj is None:
                return False
            s.delete(obj)
            return True
