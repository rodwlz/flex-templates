import flet as ft
from src.utils import navigation

#-------------------------------------
class NavButton(ft.ElevatedButton):
    def __init__(self,page,url='',text=''):
        super().__init__()
        self.text = text
        self.on_click = lambda _: navigation.visit(page,url)
    
    def container(self):
        return ft.Container(self)
#-------------------------------------
