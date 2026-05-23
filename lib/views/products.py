import flet as ft

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView
from lib.ui.components.card import Card
from lib.ui.components.nav_button import NavButton


class ProductsView(BaseView):
    title = "Products"

    def build_content(self):
        service = self.props.get("product_service")
        if service is None:
            return ft.Text("Product service unavailable", color=ft.Colors.RED_400)

        result = service.execute(ActionRequest(action="list", data={}))
        if not result.success:
            return ft.Text(f"Error loading products: {result.error}", color=ft.Colors.RED_400)

        items = result.data.get("items", [])
        if not items:
            return ft.Text("No products available")

        cards = [
            Card(
                title=p["name"],
                body=ft.Column(
                    [
                        ft.Text(f"${p['price']:.2f}"),
                        NavButton(
                            "View Details", f"/products/{p['id']}", self.nav_service
                        ),
                    ],
                    spacing=10,
                ),
            )
            for p in items
        ]
        return ft.Column(
            [ft.Text("Products", size=28, weight=ft.FontWeight.BOLD), *cards],
            spacing=15,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return ProductsView(page, props).render()
