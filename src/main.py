import flet as ft
from src.templates import apps

def app(page: ft.Page):
    apps.multi_view("Flet App",page)
 
def main():
    ft.app(target=app)

if __name__ == '__main__':
    main()
