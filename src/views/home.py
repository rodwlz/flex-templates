import flet as ft
from src.templates.layouts import base_view
import src.templates.components as c

def view(page):

    title = ft.Container(
        ft.Text("Welcome Home", size=24, weight="bold", color=ft.colors.ON_BACKGROUND),
        alignment=ft.alignment.center
        )

    sub_text = ft.Container(
        ft.Text("Let's get to work", color=ft.colors.ON_BACKGROUND),
        alignment=ft.alignment.center
        )

    home_button = c.nav.NavButton(page, url='/login', text='log in').container()

    screen = [
        title,
        sub_text,
        home_button,
    ]

   

    return base_view.build(page, '/not_found', screen_content=screen,alignment=ft.alignment.top_center,bgimage='bg.png')
