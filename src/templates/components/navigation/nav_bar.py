import flet as ft
from src.utils import navigation
from src.utils.view_history import view_history
import src.templates.components as c

class NavBar(ft.Row):
    def __init__(self, page,icon_color=ft.colors.GREY_300):
        super().__init__(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            spacing=10,
            
        )

        self.icon_color = icon_color
        logo = 'logo-white.svg'
        svg_image = c.basics.Image(logo,width=45,height=45).container()
        svg_image.padding = 5
        svg_image.tooltip = 'www.quantumwolf.org'

        # Create buttons with initial states and tooltips
        back_button = ft.IconButton(
            icon=ft.icons.ARROW_BACK_IOS,
            tooltip=view_history.get_prev(),
            on_click=lambda _: navigation.go_back(page),  # Set the event handler for go back
            disabled=not view_history.can_go_back(),
            icon_color= self.icon_color
        )

        reload_button = ft.IconButton(
            icon=ft.icons.REFRESH_ROUNDED,
            tooltip="Refresh",
            on_click=lambda _: view_history.clear_history(),
            icon_color= self.icon_color
        )

        forward_button = ft.IconButton(
            icon=ft.icons.ARROW_FORWARD_IOS,
            tooltip=view_history.get_next(),
            on_click=lambda _: navigation.go_forward(page),  # Set the event handler for go forward
            disabled=not view_history.can_go_forward(),
            icon_color= self.icon_color
        )

        # Text input for the URL
        url_input = ft.TextField(
            expand=1,
            border='none',
            hint_text="/URL",
            autofocus=True,
            on_submit=lambda _: navigation.visit(page, url=url_input.value),
        )

        search_button = ft.IconButton(
            icon=ft.icons.SEARCH_ROUNDED,
            tooltip='Search',
            on_click=lambda _: navigation.visit(page, url=url_input.value),
            icon_color= self.icon_color
        )

        # Add buttons and input to the row
        self.controls = [svg_image,back_button, forward_button, reload_button, url_input, search_button]

    def container(self)->ft.Container:
        '''
        Returns the component into a ft.Container
        '''
        return ft.Container(self)