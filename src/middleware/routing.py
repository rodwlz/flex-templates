from src.views import home,not_found
import importlib


'''
    The route needs to have the exact name of the file in a java-ish convention this is to standarize a routing method
        views_name.py == route_name
    '''

def route_change(page):
    route_name = page.route.replace("/","")
    
    try:    
        page.views.clear()
        view_mod = importlib.import_module("src.views")
        view_function = view_mod.view
        mod = importlib.import_module(f"src.views.{route_name}")
        func = getattr(mod, "view")
        view_function = func(page)
        page.views.append(view_function)

    #Launched when it didnt found the view.py      
    except ModuleNotFoundError as X:
         
         #Special cases such as home and not found
         match page.route: 
            case '/' | '':
                page.views.append(home.view(page))

            case _: #Error 404
                page.views.append(not_found.view(page))
                #raise NotImplementedError(f'route: "{page.route}"\n is missing from views')
             
    #view.py needs to have a method named view or this happens
    except AttributeError as X:
        print(X,": the method should be called view")
    
    except ReferenceError as X:
        print(X)
        
    finally:
        page.update()

        
