from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.base_class import Base
from src.vault_secrets.vault import vault

class DatabaseManager:
    def __init__(self):
        self.DATABASE_URL = "postgresql"+vault.get_secret('DB-URL')
        self.engine = create_engine(self.DATABASE_URL)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

    def get_session(self):
        return self.SessionLocal()

def main():
    db_manager = DatabaseManager()
    session = db_manager.get_session()
    # Perform database operations using the session
    session.close()

if __name__ == "__main__":
    main()
