import src.templates.patterns as p

class ViewHistory(metaclass=p.Singleton):
    def __init__(self, homepage='/'):
        self.back_stack = [homepage]
        self.forward_stack = []
        self.homepage = homepage
        self.back = False
        self.forward = False

    def clear_history(self) -> None:
        """Clears the view history, preserving the homepage and the current view."""
        self.back_stack = [self.get_current_view()]  # Preserve the homepage
        self.forward_stack = []
        self.print_stack()

    def visit(self, url="") -> None:
        """Visits a new URL, updating the history accordingly. If its the same it will jsut keep the history untouched

        Args:
            url: The URL to visit.
        """
        if url != self.get_current_view():
            if not (self.back or self.forward):
                self.back_stack.extend(self.forward_stack)
                self.back_stack.append(url)
                self.forward_stack.clear()
            elif self.forward:
                self.go_forward()
                self.forward = False
            elif self.back:
                self.go_back()
                self.back = False
        else:
            pass

    def go_back(self, steps=1) -> str:
        """Navigates back in history.

        Args:
            steps: Number of steps to go back.

        Returns:
            The current URL after navigation.
        """
        if self.can_go_back():
            steps = min(steps, len(self.back_stack) - 1)
            for _ in range(steps):
                popped_url = self.back_stack.pop()
                self.forward_stack.append(popped_url)
            return self.back_stack[-1]
        else:
            return 'Disabled'

    def go_forward(self, steps=1) -> str:
        """Navigates forward in history.

        Args:
            steps: Number of steps to go forward.

        Returns:
            The current URL after navigation.
        """
        if self.can_go_forward():
            steps = min(steps, len(self.forward_stack))
            for _ in range(steps):
                popped_url = self.forward_stack.pop()
                self.back_stack.append(popped_url)
            return self.back_stack[-1]
        else:
            return 'Disabled'

    def can_go_back(self) -> bool:
        """Checks if it's possible to go back in history."""
        return len(self.back_stack) > 1

    def can_go_forward(self) -> bool:
        """Checks if it's possible to go forward in history."""
        return len(self.forward_stack) > 0

    def get_current_view(self):
        """Returns the current viewed URL."""
        return self.back_stack[-1]

    def print_stack(self):
        """Prints the current state of the view history."""
        print('--------------')
        print("Back Stack:", self.back_stack)
        print("Can go back:", self.can_go_back())
        print("Forward Stack:", self.forward_stack)
        print("Can go forward:", self.can_go_forward())

    def get_prev(self):
        """Returns the previous view URL."""
        if self.can_go_back():
            return self.back_stack[-2]
        else:
            return "No previous view"

    def get_next(self):
        """Returns the next view URL."""
        if self.can_go_forward():
            return self.forward_stack[-1]
        else:
            return "No next view"

# Create a global instance of ViewHistory
view_history = ViewHistory()
