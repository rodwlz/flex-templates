# views/store.py
import flet as ft
from src.utils import navigation
from src.templates.layouts import base_view
import src.templates.components as c


def view(page):
    aux = ft.Container(content=ft.Text("holaaa mafer"),expand=1,bgcolor='')

    return ft.View('/mafer',[aux])
