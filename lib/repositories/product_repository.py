import uuid
from lib.models.product import Product
from lib.repositories.base import AbstractRepository


class ProductRepository(AbstractRepository[Product]):
    model = Product

    def _serialize(self, obj) -> dict:
        d = super()._serialize(obj)
        d["id"] = str(d["id"])
        d["price"] = float(d["price"])
        return d

    def _deserialize(self, data: dict) -> dict:
        d = super()._deserialize(data)
        if "id" in d and isinstance(d["id"], str):
            d["id"] = uuid.UUID(d["id"])
        return d

    def create(self, data: dict) -> dict:
        obj = super().create(data)
        return self._serialize(obj)

    def get(self, id) -> dict | None:
        obj = super().get(uuid.UUID(id) if isinstance(id, str) else id)
        return self._serialize(obj) if obj else None

    def update(self, id, data: dict) -> dict | None:
        obj = super().update(uuid.UUID(id) if isinstance(id, str) else id, data)
        return self._serialize(obj) if obj else None

    def delete(self, id) -> bool:
        return super().delete(uuid.UUID(id) if isinstance(id, str) else id)
