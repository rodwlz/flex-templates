from lib.models.product import Product


def test_product_model_has_expected_fields():
    p = Product(name="Widget", price=9.99, stock_qty=10, is_active=True)
    assert p.name == "Widget"
    assert p.__tablename__ == "products"
