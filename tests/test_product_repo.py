from decimal import Decimal
import pytest
from lib.models.product import Product
from lib.repositories.product_repository import ProductRepository


def test_product_model_has_expected_fields():
    p = Product(name="Widget", price=9.99, stock_qty=10, is_active=True)
    assert p.name == "Widget"
    assert p.__tablename__ == "products"


@pytest.fixture
def product_repo(db_factory):
    return ProductRepository(db_factory)


def test_product_create_and_get(product_repo):
    created = product_repo.create({"name": "Widget", "price": Decimal("9.99"), "stock_qty": 5, "is_active": True})
    assert created["name"] == "Widget"
    assert created["price"] == 9.99   # float after _serialize
    assert isinstance(created["id"], str)  # stringified UUID

    fetched = product_repo.get(created["id"])
    assert fetched["name"] == "Widget"
    assert fetched["price"] == 9.99


def test_product_update(product_repo):
    created = product_repo.create({"name": "Gadget", "price": Decimal("19.99"), "stock_qty": 3, "is_active": True})
    updated = product_repo.update(created["id"], {"price": Decimal("24.99"), "stock_qty": 10})
    assert updated["price"] == 24.99
    assert updated["stock_qty"] == 10
    assert updated["name"] == "Gadget"


def test_product_delete(product_repo):
    created = product_repo.create({"name": "Thingamajig", "price": Decimal("4.99"), "stock_qty": 1, "is_active": True})
    deleted = product_repo.delete(created["id"])
    assert deleted is True
    assert product_repo.get(created["id"]) is None


def test_product_paginate(product_repo):
    for i in range(3):
        product_repo.create({"name": f"Item-{i}", "price": Decimal("1.00"), "stock_qty": i, "is_active": True})
    result = product_repo.paginate(page=1, page_size=2)
    assert result["total"] >= 3
    assert len(result["items"]) == 2
    assert result["page"] == 1
    assert result["pages"] >= 2
