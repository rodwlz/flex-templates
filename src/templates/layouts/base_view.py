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
