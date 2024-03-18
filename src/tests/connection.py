import asyncio
from src.database.connection import Connection

async def test_connection():
    # Create a connection to PostgreSQL
    pg_connection = Connection(db_type='postgres',sslmode=True)
    
    try:
        # Connect to the database
        await pg_connection.connect()
        print("Connection successful!")

        # Disconnect from the database
        await pg_connection.disconnect()
        print("Disconnected from the database.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Run the test function
asyncio.run(test_connection())
