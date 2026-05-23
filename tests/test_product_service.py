import uuid
import pytest
from decimal import Decimal
from lib.services.product_service import ProductService


@pytest.fixture
def product_service(db_factory):
    return ProductService(db_factory)


def test_product_service_create(product_service):
    result = product_service.create({"name": "Widget", "price": 9.99})
    assert result["name"] == "Widget"
    assert result["price"] == 9.99
    assert isinstance(result["id"], str)
    assert result["is_active"] is True
    assert result["stock_qty"] == 0


def test_product_service_get(product_service):
    created = product_service.create({"name": "Gadget", "price": 19.99})
    fetched = product_service.get({"id": created["id"]})
    assert fetched["name"] == "Gadget"
    assert fetched["price"] == 19.99


def test_product_service_get_missing_raises(product_service):
    with pytest.raises(ValueError, match="not found"):
        product_service.get({"id": str(uuid.uuid4())})


def test_product_service_list_paginated(product_service):
    for i in range(5):
        product_service.create({"name": f"Item-{i}", "price": float(i + 1)})
    result = product_service.list({"page": 1, "page_size": 3})
    assert len(result["items"]) == 3
    assert result["total"] >= 5
    assert result["pages"] >= 2
    # items must only contain allowed fields
    for item in result["items"]:
        assert set(item.keys()) <= {"id", "name", "price", "stock_qty", "is_active"}


def test_product_service_update_partial(product_service):
    created = product_service.create({"name": "Thing", "price": 5.00})
    updated = product_service.update({"id": created["id"], "price": 7.50, "stock_qty": 3})
    assert updated["price"] == 7.50
    assert updated["stock_qty"] == 3
    assert updated["name"] == "Thing"  # unchanged


def test_product_service_delete(product_service):
    created = product_service.create({"name": "Disposable", "price": 1.00})
    result = product_service.delete({"id": created["id"]})
    assert result == {"deleted": True}
    with pytest.raises(ValueError, match="not found"):
        product_service.get({"id": created["id"]})
