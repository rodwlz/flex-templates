"""
StView Class

A custom View class for creating a structured view with a sidebar and main content area.

Parameters:
- page (ft.Page): The main page object.
- url (str): The route URL for the view.
- content (list): A list of Flet components to be included in the main content area orderded in a column form.
- top_color (str, optional): The background color of the top bar. Default is '#161616'.

Attributes:
- top_color (str): The background color of the top bar with some opacity.
- sidebar (ft.Container): The container representing the sidebar.
- navbar (ft.Container): The container representing the navigation bar.
- main_content (ft.Container): The container representing the main content area.

Example Usage:
    st_view = StView(page, '/example', [ft.Text("Hello, Flet!")])

Note: This class extends the ft.View class and includes a sidebar and a navigation bar.
"""
import flet as ft
import src.templates.components as c

class StView(ft.View):
    def __init__(self,page,url:str,content:list,top_color='#161616',):

        self.top_color = ft.colors.with_opacity(0.7,top_color)
        self.sidebar = c.nav.SideBar(page).container()
        self.navbar =  c.nav.NavBar(page).container()
        self.sidebar.bgcolor = self.top_color
        self.navbar.bgcolor = self.top_color

        super().__init__(route=url,
                         padding=0,
                         spacing=0,
                         appbar=self.navbar)
        
        self.main_content = ft.Container(
            ft.Column(content, expand=True, spacing=25,scroll=ft.ScrollMode.ADAPTIVE,),
            expand=True,
            margin=0,
            padding=15,
            alignment=ft.alignment.top_center
        )

        self.controls = [ft.Row([self.sidebar,self.main_content], expand=1,alignment=ft.MainAxisAlignment.CENTER,spacing=0),]
