from decimal import Decimal

from lib.core.interfaces import SimpleService
from lib.database.session import SessionFactory
from lib.repositories.product_repository import ProductRepository


_PRODUCT_LIST_FIELDS = frozenset({"id", "name", "price", "stock_qty", "is_active"})


class ProductService(SimpleService):

    def __init__(self, factory: SessionFactory):
        self._factory = factory

    def create(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        name = data.get("name", "")
        if not name:
            raise ValueError("name is required")
        price = data.get("price")
        if price is None:
            raise ValueError("price is required")
        create_data = {
            "name": name,
            "price": Decimal(str(price)),
            "stock_qty": data.get("stock_qty", 0),
            "is_active": data.get("is_active", True),
        }
        return repo.create(create_data)

    def get(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        product = repo.get(data["id"])
        if product is None:
            raise ValueError(f"Product {data['id']} not found")
        return product

    def list(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        page = data.get("page", 1)
        page_size = data.get("page_size", 20)
        result = repo.paginate(page=page, page_size=page_size)
        result["items"] = [
            {k: v for k, v in item.items() if k in _PRODUCT_LIST_FIELDS}
            for item in result["items"]
        ]
        return result

    def update(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        product_id = data["id"]
        update_data = {k: v for k, v in data.items() if k != "id"}
        if "price" in update_data:
            update_data["price"] = Decimal(str(update_data["price"]))
        product = repo.update(product_id, update_data)
        if product is None:
            raise ValueError(f"Product {data['id']} not found")
        return product

    def delete(self, data: dict) -> dict:
        repo = ProductRepository(self._factory)
        deleted = repo.delete(data["id"])
        if not deleted:
            raise ValueError(f"Product {data['id']} not found")
        return {"deleted": True}
