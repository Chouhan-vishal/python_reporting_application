# myapp/sql_service.py
import os
import pyodbc
from .report_queries import * 
from dotenv import load_dotenv
from datetime import datetime, timedelta
from reporting_application.utils import *
from users.models import UserActivityLog, Reports
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied

load_dotenv()

database = os.environ["SSLS_DATABASE_NAME"]
username = os.environ["SSLS_DATABASE_USER"]
password = os.environ["SSLS_DATABASE_PASSWORD"]
server = os.environ["SSLS_DATABASE_HOST"]

def create_sql_server_connection():
    try:
        # Establish connection to SQL Server
        conn_str = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password}'
        conn = pyodbc.connect(conn_str)

        return conn

    except pyodbc.Error as e:
        raise Exception(f'error accessing SQL Server')


def get_previous_date(end_date):
    """
    This function returns the previous date based on the given date and end date.
    If the end_date month is not the current month, it returns the day after today.
    If today is Monday, it returns the preceding Saturday.
    If today is Sunday, it returns the preceding Saturday.
    
    Args:
    end_date (str): The end date as a string in the format 'YYYY-MM-DD'.

    Returns:
    datetime.date: The previous date as a datetime.date string.
    """
    today_date = datetime.today().date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    if end_date.month != today_date.month:
        # Return the day after today
        pre_date = today_date + timedelta(days=1)
    else:
        # Check if today is Sunday
        if today_date.weekday() == 6:  # Sunday is represented by 6
            # Subtract one day to get Saturday
            pre_date = today_date - timedelta(days=1)
        # Check if today is Monday
        elif today_date.weekday() == 0:  # Monday is represented by 0
            # Subtract two days to get Saturday
            pre_date = today_date - timedelta(days=2)
        else:
            # Subtract one day to get the previous day
            pre_date = today_date - timedelta(days=1)
    
    return pre_date.strftime('%Y-%m-%d')

def get_monthly_date_ranges(num_months):
    date_ranges = []
    today = datetime.today()
    current_month = today.month
    current_year = today.year

    for i in range(num_months):
        month = current_month - i
        year = current_year
        if month <= 0:
            month += 12
            year -= 1
        
        start_date = datetime(year, month, 1).strftime('%Y-%m-%d')
        end_date = (datetime(year, month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        end_date = end_date.strftime('%Y-%m-%d')

        date_ranges.append({'month': datetime(year, month, 1).strftime('%B'), 'start_date': start_date, 'end_date': end_date})

    return date_ranges

def get_teamnames_for_user(user, team_name = None):
    try:
        if is_manager(user):
            conn = create_sql_server_connection()
            cursor = conn.cursor()
            full_name = user.full_name.lower()
            query = get_team_names(full_name)
            cursor.execute(query)
            results = cursor.fetchall()
            team_names = [row[0] for row in results]
            if team_name:
                if team_name in team_names:
                    team_names = f"'{team_name}'"
                else:
                    raise Exception("This Team Name is not related to the Manager")
                return team_names

            if not team_names or len(team_names) == 0:
                raise Exception("This Manager name is not related to any Team")
            else:
                team_names = ', '.join(f"'{team}'" for team in team_names)
            cursor.close()
            conn.close()
        else:
            team_names = None
        return team_names
    except Exception as e:
        raise e
    
    
def get_salesmans_for_user(user, team_name = None, salesman=None):
    try:
        conn = create_sql_server_connection()
        cursor = conn.cursor()
        emp_id = 'SLS0001'#user.emp_code
        if True:
            query = get_salesman_names(emp_id, True, team_name)
        else:
            query = get_salesman_names(emp_id, False)
            
        cursor.execute(query)
        results = cursor.fetchall()
        salesman_names = [row[0] for row in results]
        if not salesman_names or len(salesman_names) == 0:
            raise Exception("Invalid Employee ID or team name")
        else:
            if salesman and not salesman in salesman_names:
                raise Exception("This salesman is not available under this manager")
            elif salesman:
                 salesman_names = [salesman]
            salesman_names = ', '.join(f"'{salesman}'" for salesman in salesman_names)
        cursor.close()
        conn.close()
        return salesman_names
    except Exception as e:
        raise e

def count_months(start_date, end_date):
    """
    This function calculates the number of months between two dates.
    
    Parameters:
    start_date (str): The start date in the format 'YYYY-MM-DD'.
    end_date (str): The end date in the format 'YYYY-MM-DD'.
    
    Returns:
    int: The number of months between the start and end dates.
    """
    # Convert string dates to datetime objects
    start_date = datetime.strptime(start_date, '%Y-%m-%d')
    end_date = datetime.strptime(end_date, '%Y-%m-%d')
    
    # Calculate the number of months between the two dates
    month_count = (end_date.year - start_date.year) * 12 + end_date.month - start_date.month + 1
    
    return month_count

def get_previous_month_and_year():
    today = datetime.today()
    last_month_year = today.year - (today.month == 1)
    last_month_month = today.month - 1 if today.month > 1 else 12

    return last_month_month, last_month_year

def create_log(user, report_name):
    activity_log = UserActivityLog.objects.create(user=user, action_type= "viewed", object = "Report", log=f'Viewed {report_name}')
    activity_log.save()

class HasReportPermission(BasePermission):
    message = "You do not have permission to view this report."
    def has_permission(self, request, view):
        report_view = view.get_view_name()
        all_reports = Reports.objects.all()
        report_name_to_permission_map = {
            report.reports_name: report.keys
            for report in all_reports
        }
        report_permission = report_name_to_permission_map.get(report_view)
        if report_permission and hasattr(request.user, 'permitted_reports'):
            return request.user.permitted_reports.reports_permission.get(report_permission, False)
        raise PermissionDenied(self.message)

def get_last_n_months_names(n):
    current_date = datetime.now()
    months = []
    for i in range(n):
        months.insert(i,current_date.strftime('%B'))
        current_date = current_date - timedelta(days=current_date.day)
    months = list(reversed(months))
    return months

def is_month_last_week():
    today = datetime.today()

    # Get the current month and year
    current_year = today.year
    current_month = today.month

    # Find the last day of the current month
    if current_month == 12:
        last_day = datetime(current_year, current_month, 31)
    else:
        next_month = current_month + 1
        last_day = datetime(current_year, next_month, 1) - timedelta(days=1)

    # Find the week number of the last day of the month
    last_week_number = last_day.isocalendar()[1]

    # Find the week number of today's date
    current_week_number = today.isocalendar()[1]

    # Check if the current week is the last week of the month
    is_last_week = (current_week_number == last_week_number)

    return is_last_week