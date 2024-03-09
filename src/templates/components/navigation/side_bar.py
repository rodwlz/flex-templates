import flet as ft
from src.utils import navigation

class SideBar(ft.Column):
    def __init__(self, page, icon_color=ft.colors.GREY_300):
        super().__init__()

        self.icon_color = icon_color
        self.controls = self._create_navigation_controls(page)
        self.alignment = ft.MainAxisAlignment.SPACE_EVENLY

    def _create_navigation_controls(self, page):
        home_icon = ft.IconButton(
            icon=ft.icons.HOME_ROUNDED,
            tooltip="Home",
            on_click=lambda _: navigation.visit(page, "/"),
            icon_color=self.icon_color,
        )

        settings_icon = ft.IconButton(
            icon=ft.icons.SETTINGS,
            tooltip="Settings",
            on_click=lambda _: navigation.visit(page, "/settings"),
            icon_color=self.icon_color,
        )

        menu_icon = ft.IconButton(
            icon=ft.icons.MENU,
            tooltip="Menu",
            on_click=lambda _: navigation.visit(page, "/menu"),
            icon_color=self.icon_color,
        )

        return [home_icon, settings_icon, menu_icon]
    
    def container(self)->ft.Container:
        return ft.Container(self)

# Example usage:
# sidebar = SideBar(page)
# # Add the sidebar to your layout or container
