import flet as ft
import src.templates.components.navigation as nav
import src.templates.components as c


class WebView(ft.View):
    def __init__(self,url:str):
        super().__init__()
        self.route = url
        self.padding = 0
        self.margin = 0
        

def build(page,url:str, screen_content: list,
          alignment = ft.alignment.top_left, 
          top_color='#161616',
          screen_color='',
          bgimage:str = ''):

    top_color = ft.colors.with_opacity(0.7,top_color)

    sidebar = ft.Container(
        nav.SideBar(page), 
        bgcolor=top_color,)
    
    navbar = ft.Container(
        nav.NavBar(page),
    bgcolor=top_color,)


    # Your main content goes here
    main_content = ft.Container(
        ft.Column(screen_content, expand=True, spacing=25,scroll=ft.ScrollMode.ALWAYS),
        expand=True,
        margin=0
    )

    main_content.padding = 15
    main_content.alignment = alignment

    
    return ft.View(
        url,
        [
            ft.Row([sidebar, main_content], expand=1,alignment=ft.MainAxisAlignment.CENTER,spacing=0),
        ],
        padding=0,spacing=0,
        bgcolor=screen_color,
        appbar=navbar,
    )
