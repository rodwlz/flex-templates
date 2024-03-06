from src.models.ViewHistory import view_history
from src.middleware import routing


def router(page):
    view_history.visit(page.route)
    routing.route_change(page)
    #view_history.print_stack()

def go_back(page):
    view_history.back = True
    view_history.forward = False
    page.go(view_history.get_prev())
    

def go_forward(page):
    view_history.forward = True
    view_history.back = False
    page.go(view_history.get_next())
    
    
def visit(page,url):
    page.go(url)