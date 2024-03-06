# views/store.py
import flet as ft
from src.utils import navigation
from src.templates.layouts import base_view
import src.templates.components as c

def view2(page):
    aux = ft.Container(content=ft.Text("hoal"),expand=1,bgcolor='white')

    return ft.View('/joker_lix',[aux])


def view(page):
    aux = ft.Container(content=ft.Text("hoal"),expand=1,bgcolor='white')

    return ft.View('/joker_lix',[aux])
