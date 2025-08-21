import mysql.connector
from mysql.connector import Error

db_config = {
    'user': 'root',
    'password': '',
    'host': 'localhost',
    'database': 'db_genreator'
}

connection = None  # Initialize connection globally

def get_db_conn():
    global connection
    if connection is None or not connection.is_connected():  # Ensure fresh connection
        try:
            connection = mysql.connector.connect(**db_config)
            # print("Database connected successfully!")
        except Error as e:
            print(f"Error connecting to database: {e}")
            return None  # Return None if connection fails
    return connection  # Always return the connection

def close_db_conn(exception):
    global connection
    if connection:
        connection.close()
        connection = None
        print("Database connection closed")
