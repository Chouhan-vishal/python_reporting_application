# myapp/sql_service.py
import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

database = os.environ["SSLS_DATABASE_NAME"]
username = os.environ["SSLS_DATABASE_USER"]
password = os.environ["SSLS_DATABASE_PASSWORD"]
server = os.environ["SSLS_DATABASE_HOST"]

def create_sql_server_connection():
    try:
        # Establish connection to SQL Server
        conn_str = f'DRIVER={{Devart ODBC Driver for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(conn_str)

        return conn

    except pyodbc.Error as e:
        # Handle any errors
        print("Error accessing SQL Server:", e)
        return None
