import flet as ft

from lib.ui.layouts.base_view import BaseView
from lib.ui.components.card import Card
from lib.ui.components.nav_button import NavButton


SAMPLE_PRODUCTS = [
    {"id": 1, "name": "Modular Mug", "price": 12.0},
    {"id": 2, "name": "Reusable Lego", "price": 25.0},
    {"id": 3, "name": "Standardized Sticker", "price": 3.5},
]


class ProductsView(BaseView):
    title = "Products"

    def build_content(self):
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
            for p in SAMPLE_PRODUCTS
        ]
        return ft.Column(
            [ft.Text("Products", size=28, weight=ft.FontWeight.BOLD), *cards],
            spacing=15,
        )


def view(page: ft.Page, props: dict) -> ft.View:
    return ProductsView(page, props).render()
