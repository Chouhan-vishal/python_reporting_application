# myapp/sql_service.py
import os
import pyodbc
from dotenv import load_dotenv
from datetime import datetime, timedelta
from users.models import UserActivityLog
from rest_framework.permissions import BasePermission
from rest_framework.exceptions import PermissionDenied
from .report_queries import * 
from .report_user_rules import *

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


def create_log(user, report_name):
    activity_log = UserActivityLog.objects.create(user=user, report=report_name, log=f'{report_name} is viewed')
    activity_log.save()

class HasReportPermission(BasePermission):
    message = "You do not have permission to view this report."
    def has_permission(self, request, view):
        report_name_to_permission_map = {
            "Sales Summary Report": "sales_summary",
            "Sales Collection Outstanding Report": "sales_collection_outstanding",
            "Product Wise Sales Summary": "product_wise_sales_summary",
            "Weekly Summary": "weekly_summary",
            "Collection Report": "collection",
            "Customer Wise Outstanding": "customer_wise_outstanding",
            "Cr Utilization Report": "cr_utilization",
            "Salesman And Product Wise Report": "salesman_and_product_wise",
            "Target And Achieved Report": "target_and_achieved",
            "Welding Electrode Product Sales Reports": "welding_electrode",
            "Durastrong Tmt Product Sales Report": "durastrong_tmt_product_sales",
            "Sales Register Report": "sales_register",
            "Block Customers List Report": "block_customers_list",
            "Target Customer Sales Report": "target_customer_sales",
            "Product Wise Month On Month Report": "product_wise_month_sales",
            "Review Product Wise Report": "review_product_wise",
            "All Customers Mom Report": "all_customers_sales",
            "Review Salesman Wise Data": "review_salesman_wise"
        }
    
        report_permission = report_name_to_permission_map.get(view.get_view_name())
        if report_permission and hasattr(request.user, 'permitted_reports'):
            return request.user.permitted_reports.reports_permission.get(report_permission, False)
        raise PermissionDenied(self.message)
