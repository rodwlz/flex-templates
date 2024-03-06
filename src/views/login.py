import flet as ft
from src.utils import navigation
from src.templates.layouts import base_view
import src.templates.components as c

def view(page):
   
    username_input = ft.TextField(hint_text="Username", autofocus=True)
    password_input = ft.TextField(hint_text="Password", password=True)
    login_button = c.nav.NavButton(page,url='/dashboard',text='Login')
    
    # Your login page content goes here
    login_content = ft.Column([

        ft.Text("Login", size=24, weight="bold", color=ft.colors.ON_BACKGROUND),
        username_input,
        password_input,
        login_button

    ], expand=1,spacing=10)

    # Use the build function from base_view
    return  base_view.build(page,"/login",screen_content=[login_content])


# Example usage:
# login_page = view2(page)
# # Add the login_page to your layout or container
