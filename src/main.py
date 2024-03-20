import flet as ft
from src.templates import apps
from src.api.backend import backend
import uvicorn
import threading

def run_uvicorn():
    uvicorn.run(backend, host="127.0.0.1", port=8080)

def app(page: ft.Page):
    page.scroll = ft.ScrollMode.ALWAYS
    apps.multi_view("Flet App", page)
 
def main():
    threading.Thread(target=run_uvicorn).start()
    ft.app(target=app)

if __name__ == '__main__':
    main()
