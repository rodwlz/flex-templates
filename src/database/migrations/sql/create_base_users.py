from src.database.base_class import Base
from src.controllers.user import UserController
from src.database.db_manager import DatabaseManager

# Function to add users
def add_users(session):
    user_controller = UserController(session)
    users = [
        {"username": "admin", "email": "admin@qw.com", "password": "Admin01."},
        {"username": "user", "email": "user@qw.com", "password": "User02."},
        {"username": "tests", "email": "tests@qw.com", "password": "Tests03."},
    ]
    for user_data in users:
        user_controller.add_user(**user_data)

    print('Users Added')
# Main function

def main():
    # Create an instance of DatabaseManager
    db_manager = DatabaseManager()
    # Get a session from the DatabaseManager
    session = db_manager.get_session()
    # Add users using the session
    add_users(session)
    # Close the session
    session.close()

if __name__ == "__main__":
    main()
