import flet as ft

def Image(file_name: str, width: int = 200, height: int = 200,alignment=ft.alignment.center,expand=False) -> ft.Container:
    try:
        # Get the file extension
        extension = file_name.split(sep=".")[1]
        file_path = f'src/assets/{extension}/{file_name}'

        # Create and return the container with the centered image
        return ft.Container(
            ft.Image(
                src=file_path, 
                width=width, 
                height=height),
                alignment=alignment,
                bgcolor='',
                expand=expand,
                image_fit=ft.ImageFit.FILL
        )

    except FileNotFoundError:
        # Return a container with an error message
        return ft.Container(
            ft.Text(f"Error: File '{file_name}' not found.", color=ft.colors.ERROR),
            alignment=ft.alignment.center,
        )
'''
Example usage:
    import src.templates.components as c
    c.basics.Image('page-not-found.svg')

'''
