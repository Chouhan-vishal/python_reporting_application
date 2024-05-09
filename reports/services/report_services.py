# myapp/sql_service.py

import pyodbc
server = "20.244.153.185,14332"
database = "SLSS_Datalake"
username = "SLSSread"
password = "SLSSread@1234"
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
