import flet as ft


def app(title: str ,page: ft.Page):
    page.title = title
    page.go(page.route)