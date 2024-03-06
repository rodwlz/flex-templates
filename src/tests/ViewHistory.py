from src.models.ViewHistory import view_history
from src.middleware import routing

def main():
    names = ['/store', '/kaira', '/esnofi', '/ps5', '/wii', '/potato']
    clear(names)
    test()
   
def clear(names):
    view_history.clear_history()
    
    for name in names:
        view_history.visit(name)
        
    view_history.go_back(steps=2)  

def test():

    print('\n Test')
    view_history.print_stack()
    
    test1 = view_history.get_current_view()
    test0 = view_history.go_back(steps=1)
    test2 = view_history.go_forward(steps=2)
    print("Can go back:",view_history.can_go_back())
    print("Can go next:",view_history.can_go_forward())
    print(test0, test1, test2, sep="\n")
    view_history.visit('/last')
    view_history.print_stack()
    print('Wii = ',view_history.go_back(steps=2)) 


if __name__ == '__main__':
    main()
