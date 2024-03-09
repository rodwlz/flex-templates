import flet as ft
import src.templates.components as c
import src.templates.layouts as l

def view(page):
   
    text = ft.Text("Login", size=24, weight="bold", color=ft.colors.ON_BACKGROUND)
    username_input = ft.TextField(hint_text="Username", autofocus=True)
    password_input = ft.TextField(hint_text="Password", password=True)
    login_button = c.nav.NavButton(page,url='/dashboard',text='Login')

    # Your login page content goes here
    login_content = [
        text,
        username_input,
        password_input,
        login_button,
    ]

    # Use the build function from base_view
    return l.StView(page,url="/login",content=login_content)
