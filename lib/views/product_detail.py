import flet as ft
from pydantic import BaseModel

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView
from lib.ui.components.card import Card
from lib.ui.components.back_button import BackButton


class ProductDetailView(BaseView):
    title = "Product"

    class Params(BaseModel):
        id: str                       # from URL path:  /products/{id}
        tab: str = "overview"         # from query string:  ?tab=stock

    def build_content(self):
        service = self.props.get("product_service")
        if service is None:
            return ft.Text("Product service unavailable", color=ft.Colors.RED_400)

        result = service.execute(ActionRequest(action="get", data={"id": self.params.id}))
        if not result.success:
            return ft.Text("Product not found", color=ft.Colors.RED_400)

        p = result.data
        body = self._tab_body(self.params.tab, p)

        return ft.Column(
            [
                ft.Text(p["name"], size=28, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [
                        self._tab_link("overview", self.params.id),
                        self._tab_link("stock", self.params.id),
                    ],
                    spacing=15,
                ),
                Card(title=self.params.tab.capitalize(), body=body),
                BackButton(self.nav_service),
            ],
            spacing=15,
        )

    def _tab_body(self, tab: str, product: dict):
        if tab == "stock":
            return ft.Text(f"In stock: {product['stock_qty']} units")
        return ft.Text(f"Price: ${product['price']:.2f}")

    def _tab_link(self, tab: str, product_id: str):
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
