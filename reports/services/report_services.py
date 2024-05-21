# myapp/sql_service.py
import os
import pyodbc
from dotenv import load_dotenv
from datetime import datetime, timedelta

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


def get_previous_date(end_date):
    """
    This function returns the previous date based on the given date and end date.
    If the end_date month is not the current month, it returns the day after today.
    If today is Sunday, it returns the preceding Saturday.
    
    Args:
    today_date (datetime.date): The given date as a datetime.date object.
    end_date (datetime.date): The end date as a datetime.date object.

    Returns:
    datetime.date: The previous date as a datetime.date object.
    """
    # Check if the end_date month is not the current month
    today_date = datetime.today().date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if end_date.month != today_date.month:
        # Return the day after today
        pre_date =  today_date + timedelta(days=1)
    else:
        # Check if the given date is Sunday
        if today_date.weekday() == 6:  # Sunday is represented by 6
            # Subtract one day to get Saturday
            pre_date =  today_date - timedelta(days=1)
        else:
            # Subtract one day to get the previous day
            pre_date =  today_date - timedelta(days=1)
    return pre_date.strftime('%Y-%m-%d')
