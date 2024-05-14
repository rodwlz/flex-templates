import flet as ft
import src.templates.components as c
import src.templates.layouts as l
from src.middleware.security import Security

def view(page):
    
    text = ft.Container(
        ft.Text("Security Configuration", size=24, weight="bold", color=ft.colors.ON_BACKGROUND),
        alignment=ft.alignment.center,)
    
    password_input = ft.Container(
        ft.TextField(hint_text="Master Password", password=True,width=500,),
        alignment=ft.alignment.center,)
    
    login_button =  ft.Container(ft.IconButton(
            icon=ft.icons.SEARCH_ROUNDED,
            tooltip='Unlock',
            on_click=lambda _: Security.master_auth(password_input.content.value),
        ),
        alignment=ft.alignment.center)
    


    #login_button.expand = True

    # Your login page content goes here
    login_content = [
        text,
        password_input,
        login_button,
    ]



    # Use the build function from base_view
    return l.StView(page,url="/login",content=login_content)
