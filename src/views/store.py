# views/store.py
import flet as ft
from src.utils import navigation
from src.templates.layouts import base_view
import src.templates.components as c

def view(page):
    title = ft.Text("Welcome to the Store", size=24, weight="bold", color=ft.colors.ON_BACKGROUND)
    login_button = c.nav.NavButton(page,url='/login',text='Log In')
    
    
    store_content =  ft.Column([
        title,
       login_button,
    ], expand=True, spacing=10)

    return base_view.build(page,"/store",screen_content=[store_content])
