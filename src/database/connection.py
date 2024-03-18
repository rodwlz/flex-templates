import asyncpg
import mysql.connector
from src.secrets.vault import vault

class Connection:
    
    '''
    The connection class is responsible for managing the connection to a database, such as MySQL, PostgreSQL, etc. It provides methods for establishing a connection, executing queries, and handling transactions. Here's a basic explanation of the connection class:

    Initialization: The connection class typically takes the database credentials as parameters during initialization. These credentials include the database host, port, username, password, and database name.

    Establishing Connection: After initialization, the connection class establishes a connection to the database using the provided credentials. This is typically done using a library specific to the database, such as mysql.connector for MySQL or psycopg2 for PostgreSQL.

    Executing Queries: Once the connection is established, the connection class provides methods for executing SQL queries against the database. These methods allow users to perform operations such as SELECT, INSERT, UPDATE, DELETE, etc.

    Handling Transactions: The connection class may also provide methods for managing transactions, which allow users to group multiple SQL queries into a single atomic operation. This ensures data consistency and integrity.

    Closing Connection: Finally, the connection class should provide a method for closing the connection to the database once it's no longer needed. This helps free up resources and prevents memory leaks.

    Here's an example of how the connection class might be used:

    # Example usage
    import asyncio

    async def main():
        # Create a connection to PostgreSQL
        pg_connection = Connection('postgresql', 'localhost', 5432, 'user', 'password', 'dbname')
        await pg_connection.connect()
        result = await pg_connection.execute('SELECT * FROM table_name')
        print(result)
        await pg_connection.disconnect()

        # Create a connection to MySQL
        mysql_connection = Connection('mysql', 'localhost', 3306, 'user', 'password', 'dbname')
        mysql_connection.connect()
        result = mysql_connection.execute('SELECT * FROM table_name')
        print(result)
        mysql_connection.disconnect()

    # Run the main function
    asyncio.run(main())
    '''

    
    def __init__(self, db_type:str,
                 sslmode=False,
                 host=vault.get_secret('DB-HOST'), 
                 port=vault.get_secret('DB-PORT'), 
                 user=vault.get_secret('DB-USER'), 
                 password=vault.get_secret('DB-PASSWORD'), 
                 database=vault.get_secret('DB-NAME')):
        
        self.db_type = db_type
        self.ssl = sslmode
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.conn = None

    async def connect(self):
        if self.db_type == 'postgres':
            self.conn = await asyncpg.connect(
                user=self.user,
                password=self.password,
                database=self.database,
                host=self.host,
                port=self.port,
                ssl=self.ssl,
            )


        elif self.db_type == 'mysql':
            self.conn = mysql.connector.connect(
                user=self.user,
                password=self.password,
                database=self.database,
                host=self.host,
                port=self.port
            )
        else:
            raise ValueError("Unsupported database type")

    async def disconnect(self):
        await self.conn.close()

    def execute(self, query):
        if self.db_type == 'postgresql':
            return self.conn.execute(query)
        elif self.db_type == 'mysql':
            cursor = self.conn.cursor()
            cursor.execute(query)
            return cursor.fetchall()
        else:
            raise ValueError("Unsupported database type")
