import flet as ft
from pydantic import BaseModel

from lib.ui.layouts.base_view import BaseView
from lib.ui.components.card import Card
from lib.ui.components.back_button import BackButton


CATALOG = {
    1: {"name": "Modular Mug", "price": 12.0, "stock": 42},
    2: {"name": "Reusable Lego", "price": 25.0, "stock": 7},
    3: {"name": "Standardized Sticker", "price": 3.5, "stock": 999},
}


class ProductDetailView(BaseView):
    title = "Product"

    class Params(BaseModel):
        id: int                       # from URL path:  /products/{id}
        tab: str = "overview"         # from query string:  ?tab=stock

    def build_content(self):
        p = self.params
        product = CATALOG.get(p.id)

        if product is None:
            return ft.Text(f"No product with id={p.id}", color=ft.Colors.RED_400)

        body = self._tab_body(p.tab, product)

        return ft.Column(
            [
                ft.Text(product["name"], size=28, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        self._tab_link("overview", p.id),
                        self._tab_link("stock", p.id),
                    ],
                    spacing=15,
                ),
                Card(title=p.tab.capitalize(), body=body),
                BackButton(self.nav_service),
            ],
            spacing=15,
        )

    def _tab_body(self, tab: str, product: dict):
        if tab == "stock":
            return ft.Text(f"In stock: {product['stock']} units")
        return ft.Text(f"Price: ${product['price']:.2f}")

    def _tab_link(self, tab: str, product_id: int):
        from lib.contracts.base import ActionRequest

        return ft.TextButton(
            tab.capitalize(),
            on_click=lambda _: self.nav_service.execute(
                ActionRequest(
                    action="visit", data={"url": f"/products/{product_id}?tab={tab}"}
                )
            ),
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return ProductDetailView(page, props).render()
