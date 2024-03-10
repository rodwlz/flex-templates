import flet as ft
from src.utils import navigation
from src.middleware import error_handling

def app(title: str, page: ft.Page):
    
    page.title = title
    page.window_min_width = 1000
    page.on_route_change = lambda _: navigation.router(page)

    #page.on_error = lambda e: error_handling(page,e)
    navigation.visit(page,page.route) #Render homepage = '/'
