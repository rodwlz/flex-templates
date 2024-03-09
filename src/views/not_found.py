import flet as ft
from src.templates.layouts import base_view
import src.templates.components as c
import src.templates.layouts as l

def view(page):

    title = ft.Container(
        ft.Text("404 Not Found", size=24, weight="bold", color=ft.colors.ON_BACKGROUND),
        alignment=ft.alignment.center
        )

    sub_text = ft.Container(
        ft.Text("Sorry, the page you are looking for might be in another universe.", color=ft.colors.ON_BACKGROUND),
        alignment=ft.alignment.center
        )

    home_button = c.nav.NavButton(page, url='/', text='take me home').container()
    svg_image = c.basics.Image('page-not-found.svg').container()
    
    screen = [
        title,
        sub_text,
        svg_image,
        home_button,
    ]

    return l.StView(page,'/not_found',screen)
