import flet as ft
from pydantic import BaseModel

from lib.contracts.base import ActionRequest
from lib.ui.layouts.base_view import BaseView
from lib.ui.components.card import Card
from lib.ui.components.back_button import BackButton


class ProductDetailView(BaseView):
    title = "Product"

    class Params(BaseModel):
        id: str
        tab: str = "overview"

    def __init__(self, page: ft.Page, props: dict):
        super().__init__(page, props)
        self._service = props.get("product_service")
        backend = props.get("backend")
        self._is_admin = backend is not None and backend.auth.current_user() is not None
        self._edit_name: ft.TextField | None = None
        self._edit_price: ft.TextField | None = None
        self._edit_stock: ft.TextField | None = None
        self._edit_active: ft.Checkbox | None = None
        self._edit_status: ft.Text | None = None

    def _on_save(self, _e):
        try:
            data = {
                "id": self.params.id,
                "name": self._edit_name.value.strip(),
                "price": float(self._edit_price.value),
                "stock_qty": int(self._edit_stock.value),
                "is_active": self._edit_active.value,
            }
        except (ValueError, AttributeError) as exc:
            self._edit_status.value = f"Invalid input: {exc}"
            self._edit_status.color = ft.Colors.RED_400
            self.page.update()
            return

        result = self._service.execute(ActionRequest(action="update", data=data))
        if result.success:
            self._edit_status.value = "Saved."
            self._edit_status.color = ft.Colors.GREEN_400
        else:
            self._edit_status.value = f"Error: {result.error}"
            self._edit_status.color = ft.Colors.RED_400
        self.page.update()

    def _build_edit_section(self, p: dict) -> ft.Control:
        self._edit_name = ft.TextField(label="Name", value=p["name"], width=280)
        self._edit_price = ft.TextField(label="Price", value=str(p["price"]), width=130)
        self._edit_stock = ft.TextField(label="Stock qty", value=str(p["stock_qty"]), width=130)
        self._edit_active = ft.Checkbox(label="Active", value=p["is_active"])
        self._edit_status = ft.Text("", size=12)

        return ft.Column(
            [
                ft.Text("Edit", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(
                    [self._edit_name, self._edit_price, self._edit_stock, self._edit_active],
                    spacing=15,
                    wrap=True,
                ),
                ft.Row(
                    [
                        ft.ElevatedButton(content=ft.Text("Save"), on_click=self._on_save),
                        self._edit_status,
                    ],
                    spacing=10,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            spacing=10,
        )

    def build_content(self):
        if self._service is None:
            return ft.Text("Product service unavailable", color=ft.Colors.RED_400)

        result = self._service.execute(ActionRequest(action="get", data={"id": self.params.id}))
        if not result.success:
            return ft.Text("Product not found", color=ft.Colors.RED_400)

        p = result.data
        body = self._tab_body(self.params.tab, p)

        controls = [
            ft.Text(p["name"], size=28, weight=ft.FontWeight.BOLD),
            ft.Row(
                [
                    self._tab_link("overview", self.params.id),
                    self._tab_link("stock", self.params.id),
                ],
                spacing=15,
            ),
            Card(title=self.params.tab.capitalize(), body=body),
        ]

        if self._is_admin:
            controls.append(ft.Divider())
            controls.append(self._build_edit_section(p))

        controls.append(BackButton(self.nav_service))
        return ft.Column(controls, spacing=15)

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
