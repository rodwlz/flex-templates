import flet as ft
import os

class Image(ft.Image):

    def __init__(self, file_name: str, width=200, height=200):
        super().__init__()
        self.width = width
        self.height = height
        extension = file_name.split(sep=".")[1]
        self.src = f'src/assets/{extension}/{file_name}'

    def container(self) -> ft.Container:
        # Check if the file exists
        if os.path.exists(self.src):
            return ft.Container(
                self,
                alignment=ft.alignment.center,
                expand=False,
            )
        else:
            # Return a container with an error image
            return ft.Container(
                ft.Image(src='src/assets/png/error.png', width=self.width, height=self.height),
                alignment=ft.alignment.center,
                expand=False,
            )
