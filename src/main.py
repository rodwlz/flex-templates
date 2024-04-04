import flet as ft
from src.templates import apps
from src.api.backend import backend
import threading

def app(page: ft.Page):
    page.scroll = ft.ScrollMode.ALWAYS
    apps.multi_view("Flex App", page)
 
def main():
    threading.Thread(target=backend.launch).start() #Launch the back end on its own thread
    ft.app(target=app) #Launch the front end
    backend.shutdown() #Stop The backend when the app is closed

if __name__ == '__main__':
    main()
