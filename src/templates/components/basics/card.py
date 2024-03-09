import flet as ft

class ReportCard(ft.Card):
    '''
    This component works a bit different in order to handle the event needed.
    
    Example use:
        report_card = c.basics.ReportCard()
        report_card.Button.on_click = lambda _: event()
        report_card_container = report_card.container()
    '''

    def __init__(self,title:str = "Title",subtitle:str = "Subtitle"):
        super().__init__()

        self.ListTile = ft.ListTile(
                                    leading=ft.Icon(ft.icons.EVENT),
                                    title=ft.Text(title),
                                    subtitle=ft.Text(subtitle),
                                )
        
        self.Button = ft.ElevatedButton("execute")
        
        self.content=ft.Container(ft.Column([self.ListTile,
                                             ft.Container(self.Button,alignment=ft.alignment.center)]),
                                             padding=10,
                                             alignment=ft.alignment.top_center)

    def container(self):
        return ft.Container(self,width=200,padding=15,alignment=ft.alignment.center)
    
