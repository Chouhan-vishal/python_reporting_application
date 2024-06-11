from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from reports.services import report_services, report_queries, report_user_rules
from reports.services.report_services import HasReportPermission
from django.db import connection, DatabaseError
from rest_framework.views import APIView
from users.services.utils import drf_schema, response
from collections import defaultdict
from reporting_application.constants import *
import logging
from users.models import UserActivityLog , User
from users.serializers import UserActivityLogSerializer
from rest_framework import serializers
from datetime import datetime, timedelta
logger = logging.getLogger('reports')


@drf_schema(serializer_name="DateSerializer")
@api_view(['POST'])
@permission_classes([IsAuthenticated, HasReportPermission])
def sales_summary_report(request):
    try:
        user = request.user
        team_names = None
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)
        
        REPORT_NAME = 'Sales Summary Report'
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)
        if not start_date or not end_date:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
        pre_date = report_services.get_previous_date(end_date)
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.sales_summary_query(start_date, end_date, pre_date, team_names)
        # Assuming you execute the query with the provided start_date and end_date values
        cursor.execute(sql_query)
        results = cursor.fetchall()
        team_sales_summary = {}
        team_sales_summary = defaultdict(lambda: {
            'team_target_qty': 0,
            'team_sales_quantity': 0,
            'team_achieved%': 0,
            'sales_persons': [],
            'TeamPreDaySalesValue': 0
        })
        for row in results:
            team_name = row[0]
            sales_person = row[1]
            sales_summary = {
                'sales_person': sales_person,
                'target_qty': row[2],
                'sales_quantity': row[3],
                'achieved%': row[4],
                'PreDaySalesValue':row[5],
            }
            team_sales_summary[team_name]['team_target_qty'] += sales_summary['target_qty']
            team_sales_summary[team_name]['team_sales_quantity'] += sales_summary['sales_quantity']
            team_sales_summary[team_name]['TeamPreDaySalesValue'] += sales_summary['PreDaySalesValue']
            team_sales_summary[team_name]['sales_persons'].append(sales_summary)
        response_data = []
        for team_name, team_summary in team_sales_summary.items():
            team_target_qty = team_summary['team_target_qty']
            team_sales_qty = team_summary['team_sales_quantity']
            if team_target_qty != 0:
                team_summary['team_achieved%'] = round((team_sales_qty / team_target_qty) * 100, 2)
            team_data = {
                'team_name': team_name,
                'team_target_qty': team_summary['team_target_qty'],
                'team_sales_quantity': team_summary['team_sales_quantity'],
                'team_achieved%': team_summary['team_achieved%'],
                'TeamPreDaySalesValue': team_summary['TeamPreDaySalesValue'],
                'sales_persons': team_summary['sales_persons'],
            }
            response_data.append(team_data)
        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, response_data, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@drf_schema(serializer_name="DateSerializer")
@api_view(['POST'])
@permission_classes([IsAuthenticated ,HasReportPermission])
def sales_collection_outstanding_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = 'Sales Collection Outstanding Report'
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)
        if not start_date or not end_date:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
    
        pre_date = report_services.get_previous_date(end_date)
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        query = report_queries.sales_collection_outstanding_summary(pre_date, user, team_names)
        cursor.execute(query)

        results = cursor.fetchall()
        team_sales_summary = defaultdict(lambda: {
            'team_pre_day_sales_mts': 0,
            'team_pre_day_collection': 0,
            'team_overall_outstanding_amt': 0,
            'team_above_25_days_os': 0,
            'team_above_45_days_os': 0,
            'team_above_90_days_os': 0,
            'team_sales_persons': []
        })

        for row in results:
            team_name = row[0]
            sales_person = row[1]
            sales_summary = {
                'sales_person': sales_person,
                'pre_day_sales_mts': row[2],
                'pre_day_collection': row[3],
                'overall_outstanding_amt': row[4],
                'above_25_days_os': row[5],
                'above_45_days_os': row[6],
                'above_90_days_os': row[7]
            }
            # Update team summary values
            team_sales_summary[team_name]['team_pre_day_sales_mts'] += row[2]
            team_sales_summary[team_name]['team_pre_day_collection'] += row[3]
            team_sales_summary[team_name]['team_overall_outstanding_amt'] += row[4]
            team_sales_summary[team_name]['team_above_25_days_os'] += row[5]
            team_sales_summary[team_name]['team_above_45_days_os'] += row[6]
            team_sales_summary[team_name]['team_above_90_days_os'] += row[7]

            # Append sales person summary to the team
            team_sales_summary[team_name]['team_sales_persons'].append(sales_summary)

        # Convert the team_sales_summary dictionary to the desired array of dictionaries format
        result = []
        for team_name, summary in team_sales_summary.items():
            team_dict = {
                'team_name': team_name,
                'team_pre_day_sales_mts': summary['team_pre_day_sales_mts'],
                'team_pre_day_collection': summary['team_pre_day_collection'],
                'team_overall_outstanding_amt': summary['team_overall_outstanding_amt'],
                'team_above_25_days_os': summary['team_above_25_days_os'],
                'team_above_45_days_os': summary['team_above_45_days_os'],
                'team_above_90_days_os': summary['team_above_90_days_os'],
                'team_sales_persons': summary['team_sales_persons']
            }
            result.append(team_dict)
        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, result, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)
    
@drf_schema(serializer_name="DateSerializer")
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def product_wise_sales_summary(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)
        REPORT_NAME = "Product Wise Sales Summary"
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)
        if not start_date or not end_date:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
        pre_date = report_services.get_previous_date(end_date)
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        query = report_queries.product_wise_sales_summary_query(start_date, end_date, pre_date, team_names)
        cursor.execute(query)

        results = cursor.fetchall()
        columns = [col[0] for col in cursor.description]

        data = []
        for row in results:
            record = dict(zip(columns, row))
            # Handling Nulls
            if record['pre_day_sales'] is None:
                record['pre_day_sales'] = 0
            if record['achievement_percentage'] is None:
                record['achievement_percentage'] = 0
            data.append(record)
        final_response = {"product_wise_sales": data}

        # Closing the cursor and connection
        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, final_response, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@drf_schema(serializer_name="DateSerializer")
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def weekly_summary(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "Weekly Summary Report"
        today_is_monday = datetime.today().weekday() == 0
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        query = report_queries.weekly_report_query(user, team_names)
        cursor.execute(query)
        results = cursor.fetchall()

        team_sales_list = []

        team_sales_summary = defaultdict(lambda: {
            'Target Qty(MTs)': 0,
            'Achvd Qty(MTs)': 0,
            'Pending Target': 0,
            'Weekly Target': 0,
            'Collection Target': 0,
            'Collection Achived': 0,
            'Salesmen': [],
            'Weekly Achved Qty(MTs)': 0
        })
        # Process query results
        for row in results:
            weekly_target = row[8] if today_is_monday else row[10]
            team_name = row[3]
            salesman = row[4]
            sales_summary = {
                'Salesman': salesman,
                'Target Qty(MTs)': row[5],
                'Achvd Qty(MTs)': row[6],
                'Pending Target': row[8],
                'Weekly Target': weekly_target,
                'Collection Target': row[11],
                'Collection Achived': row[12],
                'Weekly Achved Qty(MTs)': row[13]
            }

            # Update team summary values
            team_sales_summary[team_name]['Target Qty(MTs)'] += row[5]
            team_sales_summary[team_name]['Achvd Qty(MTs)'] += row[6]
            team_sales_summary[team_name]['Pending Target'] += row[8]
            team_sales_summary[team_name]['Weekly Target'] += weekly_target
            team_sales_summary[team_name]['Collection Target'] += row[11]
            team_sales_summary[team_name]['Collection Achived'] += row[12]
            team_sales_summary[team_name]['Weekly Achved Qty(MTs)'] += row[13]

            # Append salesmen summary to the team
            team_sales_summary[team_name]['Salesmen'].append(sales_summary)

        # Convert defaultdict to list of dictionaries
        for team_name, summary in team_sales_summary.items():
            team_sales_list.append({
                'Team Name': team_name,
                **summary
            })

        # Close cursor and connection
        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, team_sales_list, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@drf_schema(serializer_name="DateSerializer")
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def collection_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "Collection Report"
        start_date_str = request.data.get("start_date")
        end_date_str = request.data.get("end_date")
        
        if not start_date_str or not end_date_str:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
        
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
        
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        team_totals = defaultdict(lambda: defaultdict(lambda: {"TotalCollection": 0, "IndividualSales": {}}))
        
        current_date = start_date
        while current_date <= end_date:
            query = report_queries.collection_report_by_date_range(current_date, user, team_names)
            cursor.execute(query)
            data = cursor.fetchall()
            
            for row in data:
                team_name, sales_person, total_collection = row
                receipt_date = current_date.strftime('%Y-%m-%d')
                
                team_totals[team_name][receipt_date]["TotalCollection"] += total_collection
                team_totals[team_name][receipt_date]["IndividualSales"][sales_person] = total_collection
                
            current_date += timedelta(days=1)
        
        # Convert the team_totals dictionary to the desired array of dictionaries format
        result = []
        for team_name, date_data in team_totals.items():
            for receipt_date, collections in date_data.items():
                individual_sales_list = [{"SalesPerson": sp, "TotalCollection": tc} for sp, tc in collections["IndividualSales"].items()]
                result.append({
                    "TeamName": team_name,
                    "ReceiptDate": receipt_date,
                    "TotalCollection": collections["TotalCollection"],
                    "IndividualSales": individual_sales_list
                })
        
        # Closing the cursor and connection
        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, result, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)
    
@drf_schema(serializer_name="CustomerWiseOutstandingSerializer",
            serializer_fields={
                "outstanding_value": serializers.IntegerField(),
                "team_name": serializers.CharField(),
                "salesman": serializers.CharField()
            })
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def customer_wise_outstanding(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = 'Customer Wise Outstanding Report'
        outstanding_value = request.data.get("outstanding")
        team_name = request.data.get("team_name")
        salesman = request.data.get("salesman")
        outstanding_days = [0, 25, 45, 90]
        if outstanding_value not in outstanding_days:
            return Response({"error": "Please provide valid outstanding day value"}, status=400)
        # Define the raw SQL query

        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.customer_wise_outstanding_query(outstanding_value, user, team_names)
        cursor.execute(sql_query)

        # Fetch data
        data = cursor.fetchall()
        formatted_data = []
        for row in data:
            formatted_row = {
                "Branch Name": row[0],
                "Bill NO": row[1],
                "Customer Name": row[2],
                "Ageing": row[3],
                "Outstanding Amount": row[4]
            }
            formatted_data.append(formatted_row)

        # Calculate total outstanding sum
        total_outstanding_sum = sum(row[4] for row in data)

        # Close cursor and connection
        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        # Return response with fetched data and total outstanding sum
        return response(SUCCESS, {f"Customer wise {outstanding_value} Days O/S":formatted_data,"total_outstanding_sum": total_outstanding_sum}, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@drf_schema(serializer_name="CRUtilizationReportSerializer",
            serializer_fields={
                "team_name": serializers.CharField(),
                "salesman": serializers.CharField()
            })
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cr_utilization_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "CR Utilization Report"
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        team_name = request.data.get("team_name")
        salesman = request.data.get("salesman")
        sql_query = report_queries.cr_utilization_report_query(user, team_names)
        cursor.execute(sql_query)
    
        # Fetch data
        results = cursor.fetchall()
        
        # Initialize a nested dictionary to hold the grouped data
        data = [dict(zip([column[0] for column in cursor.description], row)) for row in results]
        
        # Closing the cursor and connection
        cursor.close()
        conn.close()
    
        return response(SUCCESS, data, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)
# ================================== Not including ================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def team_and_product_wise_report(request):
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    pre_date = report_services.get_previous_date(end_date)
    sql_query = report_queries.team_and_product_wise_query(start_date,end_date, pre_date)
    cursor.execute(sql_query)

    # Fetching all the rows
    rows = cursor.fetchall()

    # Organizing data by product cluster
    data_by_cluster = {}
    for row in rows:
        team_name, product_cluster, target_qty, achv_qty, achv_percent = row
        if product_cluster not in data_by_cluster:
            data_by_cluster[product_cluster] = {}
        data_by_cluster[product_cluster][team_name] = {
            'Target Qty': target_qty,
            'Achv Qty': achv_qty,
            'Achv %': achv_percent
        }
    
    # Closing the cursor and connection
    cursor.close()
    conn.close()
    return Response({"Team wise product wise report": data_by_cluster})


@drf_schema(serializer_name="SalesmanProductWiseReportSerializer",
            serializer_fields={
                "team_name": serializers.CharField(),
                "salesman": serializers.CharField()
            })
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def salesman_and_product_wise_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "Salesman and Product Wise Report"
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        team_name = request.data.get("team_name")
        salesman = request.data.get("salesman")

        sql_query = report_queries.salesman_and_product_wise_query(user, team_names)
        cursor.execute(sql_query)

        # Fetching all the rows
        rows = cursor.fetchall()

        # Grouping the data by product and salesman
        results = {}
        for row in rows:
            salesman_name, product_name, target_qty, achv_qty, achv_percent = row

            # Create product entry if not exist
            if product_name not in results:
                results[product_name] = {}

            # Create salesman entry under product if not exist
            if salesman_name not in results[product_name]:
                results[product_name][salesman_name] = {
                    'target': target_qty,
                    'achieved': achv_qty,
                    'achieved_percent': achv_percent
                }
        formatted_data = []
        for product_name, salesmen in results.items():
            product_data = {
                'Product Name': product_name,
                'Salesmen': []
            }
            for salesman_name, data in salesmen.items():
                salesman_data = {
                    'Salesman Name': salesman_name,
                    'Target': data['target'],
                    'Achieved': data['achieved'],
                    'Achieved Percent': data['achieved_percent']
                }
                product_data['Salesmen'].append(salesman_data)
            formatted_data.append(product_data)

        # Closing the cursor and connection
        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, formatted_data, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@drf_schema(serializer_name="DateSerializer")
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def target_and_achieved_report(request):
    try:
        user =  request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = 'Target and Achieved Report'
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)
        if not start_date or not end_date:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
        pre_date = report_services.get_previous_date(end_date)
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.target_and_achieved_query(start_date, end_date, pre_date, user, team_names)
        # Assuming you execute the query with the provided start_date and end_date values
        cursor.execute(sql_query)
        results = cursor.fetchall()
    
        # Initialize the team sales summary dictionary with default values
        team_sales_summary = defaultdict(lambda: {
            'team_target_qty': 0,
            'team_sales_quantity': 0,
            'team_achieved%': 0,
            'TeamPreDaySalesValue': 0,
            'sales_persons': [],
            'team_above_25_days_outstanding': 0,
            'team_target_customer_count': 0,
            'team_target_customer_reached': 0
        })
    
        # Process each row in the results
        for row in results:
            team_name = row[0]
            sales_person = row[1]
            sales_summary = {
                'sales_person': sales_person,
                'target_qty': row[2],
                'sales_quantity': row[3],
                'achieved%': row[4],
                'PreDaySalesValue': row[5],
                '25DaysOutstanding': row[6],
                'TargetCustomerCount': row[7],
                'TargetCustomerReached': row[8]
            }
    
            # Aggregate team-level data
            team_sales_summary[team_name]['team_target_qty'] += sales_summary['target_qty']
            team_sales_summary[team_name]['team_sales_quantity'] += sales_summary['sales_quantity']
            team_sales_summary[team_name]['TeamPreDaySalesValue'] += sales_summary['PreDaySalesValue']
            team_sales_summary[team_name]['team_above_25_days_outstanding'] += sales_summary['25DaysOutstanding']
            team_sales_summary[team_name]['team_target_customer_count'] += sales_summary['TargetCustomerCount']
            team_sales_summary[team_name]['team_target_customer_reached'] += sales_summary['TargetCustomerReached']
    
            # Append the sales person's data to the team's list of sales persons
            team_sales_summary[team_name]['sales_persons'].append(sales_summary)
    
        # Calculate the achievement percentage for each team
        for team_name, team_summary in team_sales_summary.items():
            team_target_qty = team_summary['team_target_qty']
            team_sales_qty = team_summary['team_sales_quantity']
            if team_target_qty != 0:
                team_summary['team_achieved%'] = round((team_sales_qty / team_target_qty) * 100, 2)
        
        team_sales_summary_list = []
    
        # Convert the dictionary to a list of dictionaries
        for team_name, team_summary in team_sales_summary.items():
            team_summary['team_name'] = team_name
            team_sales_summary_list.append(team_summary)
            # Convert the team sales summary to a dictionary and wrap it in a response dictionary
        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, team_sales_summary_list, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@drf_schema(serializer_name="DateSerializer")
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def welding_electrode_product_sales_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "Welding Electrode Product Sales Report"
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)
        if not start_date or not end_date:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)

        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.welding_electrode_product_sales_query(start_date, end_date, team_names)
        cursor.execute(sql_query)
        results = cursor.fetchall()

        team_sales_summary = defaultdict(lambda: {
            'team_target_qty': 0,
            'team_sales_quantity': 0,
            'team_achieved%': 0,
            'sales_persons': []
        })

        for row in results:
            team_name = row[0]
            sales_person = row[1]
            target_qty = row[2]
            sales_quantity = row[3]
            achieved_percentage = row[4]

            sales_summary = {
                'sales_person': sales_person,
                'target_qty': target_qty,
                'sales_quantity': sales_quantity,
                'achieved%': achieved_percentage
            }

            team_sales_summary[team_name]['team_target_qty'] += target_qty
            team_sales_summary[team_name]['team_sales_quantity'] += sales_quantity
            team_sales_summary[team_name]['sales_persons'].append(sales_summary)

        for team_name, team_summary in team_sales_summary.items():
            team_target_qty = team_summary['team_target_qty']
            team_sales_qty = team_summary['team_sales_quantity']
            if team_target_qty != 0:
                team_summary['team_achieved%'] = round((team_sales_qty / team_target_qty) * 100, 2)

        # Convert the summary dictionary to the desired list format
        response_data = []
        for team_name, team_summary in team_sales_summary.items():
            response_data.append({
                'team_name': team_name,
                'team_target_qty': team_summary['team_target_qty'],
                'team_sales_quantity': team_summary['team_sales_quantity'],
                'team_achieved%': team_summary['team_achieved%'],
                'sales_persons': team_summary['sales_persons']
            })

        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, response_data, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@drf_schema(serializer_name="DateSerializer")
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def durastrong_tmt_product_sales_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "Durastrong TMT Product Sales Report"
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)
        if not start_date or not end_date:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)

        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.durastrong_tmt_product_sales_query(start_date, end_date, team_names)
        cursor.execute(sql_query)
        results = cursor.fetchall()

        team_sales_summary = defaultdict(lambda: {
            'team_target_qty': 0,
            'team_sales_quantity': 0,
            'team_achieved%': 0,
            'sales_persons': []
        })

        for row in results:
            team_name = row[0]
            sales_person = row[1]
            target_qty = row[2]
            sales_quantity = row[3]
            achieved_percentage = row[4]

            sales_summary = {
                'sales_person': sales_person,
                'target_qty': target_qty,
                'sales_quantity': sales_quantity,
                'achieved%': achieved_percentage
            }

            team_sales_summary[team_name]['team_target_qty'] += target_qty
            team_sales_summary[team_name]['team_sales_quantity'] += sales_quantity
            team_sales_summary[team_name]['sales_persons'].append(sales_summary)

        for team_name, team_summary in team_sales_summary.items():
            team_target_qty = team_summary['team_target_qty']
            team_sales_qty = team_summary['team_sales_quantity']
            if team_target_qty != 0:
                team_summary['team_achieved%'] = round((team_sales_qty / team_target_qty) * 100, 2)

        # Convert the summary dictionary to the desired list format
        response_data = []
        for team_name, team_summary in team_sales_summary.items():
            response_data.append({
                'team_name': team_name,
                'team_target_qty': team_summary['team_target_qty'],
                'team_sales_quantity': team_summary['team_sales_quantity'],
                'team_achieved%': team_summary['team_achieved%'],
                'sales_persons': team_summary['sales_persons']
            })

        cursor.close()
        conn.close()
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, response_data, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@drf_schema(serializer_name="DateSerializer")
@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def sales_register_report(request):
    try:
        REPORT_NAME = "Sales Register Report"
        start_date = request.data.get("start_date", None)
        end_date = request.data.get("end_date", None)
        if not start_date or not end_date:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.sales_register_query(start_date, end_date)
        # Assuming you execute the query with the provided start_date and end_date values
        cursor.execute(sql_query)
        results = cursor.fetchall()
        data = [dict(zip([column[0] for column in cursor.description], row)) for row in results]
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, data, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def block_customers_list_report(request):
    try:
        REPORT_NAME = "Block Customers List Report"
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        # Assuming you execute the query with the provided start_date and end_date values
        sql_query = report_queries.block_customers_list_query()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        data = [dict(zip([column[0] for column in cursor.description], row)) for row in results]
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, data, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def all_customers_mom_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "All Customers Month on Month Report"
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        month_count = request.data.get("month_count", None)
        if not month_count:
            return Response({"error": "Please provide both Month count."}, status=400)
        date_ranges = report_services.get_monthly_date_ranges(month_count)

        # list to hold the aggregated data
        result = []

        for _, item in enumerate(date_ranges):
            # Assuming you execute the query with the provided start_date and end_date values
            sql_query = report_queries.all_customers_sales_query(item['start_date'], item['end_date'], user, team_names)
            cursor.execute(sql_query)
            results = cursor.fetchall()
            month = item['month']
            
            # Process the results
            for row in results:
                sales_person = row[0]
                customer_name = row[1]
                achv_qty = row[2]
                
                # Find the existing entry for the sales person and customer, if it exists
                entry = next((entry for entry in result if entry["Sales Person"] == sales_person and entry["Customer Name"] == customer_name), None)
                
                if not entry:
                    # Create a new entry if it doesn't exist
                    entry = {
                        "Sales Person": sales_person,
                        "Customer Name": customer_name,
                        "month_data": []
                    }
                    result.append(entry)
                
                # Append the monthly data
                entry["month_data"].append({
                    "month_name": month,
                    "achvd_qty": achv_qty
                })
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, result, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def product_wise_month_on_month_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "Product Wise Month On Month Report"
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        month_count = request.data.get("month_count", None)
        if not month_count:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
        date_ranges = report_services.get_monthly_date_ranges(month_count)
        intermediate_result = {}

        for _, item in enumerate(date_ranges):
            # Assuming you execute the query with the provided start_date and end_date values
            sql_query = report_queries.product_wise_month_on_month_query(item['start_date'], item['end_date'], team_names)
            cursor.execute(sql_query)
            results = cursor.fetchall()
            data = [dict(zip([column[0] for column in cursor.description], row)) for row in results]
            month = item['month']

            for record in data:
                item_category = record['item_category']
                achvd_qty = record['achvd_qty']
                
                if item_category not in intermediate_result:
                    intermediate_result[item_category] = {}
                
                intermediate_result[item_category][month] = achvd_qty

        final_result = []

        for item_category, months_data in intermediate_result.items():
            month_list = [{month: value} for month, value in months_data.items()]
            final_result.append({
                "item_category": item_category,
                "month_data": month_list
            })
        # report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, final_result, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def review_product_wise_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "Review Product Wise Report"
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        month_count = request.data.get("month_count", None)
        if not month_count:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
        sql_query = report_queries.review_product_wise_query(month_count, team_names)
        cursor.execute(sql_query)
        results = cursor.fetchall()
        data = defaultdict(lambda: defaultdict(lambda: {"Target Qty": 0, "Months": defaultdict(float)}))

        # Process the results
        for row in results:
            team_name, product_cluster, target_qty, achv_qty, year, month = row
            if achv_qty is None:
                achv_qty = 0.0
            if month is None:
                month = "No Month"
            data[team_name][product_cluster]["Target Qty"] = float(target_qty)
            data[team_name][product_cluster]["Months"][month] = float(achv_qty)

        # Convert the data to the desired format
        result = []
        for team, products in data.items():
            team_products = {}
            for product, product_data in products.items():
                product_dict = {
                    "Target Qty": product_data["Target Qty"],
                    "Months": dict(product_data["Months"])
                }
                team_products[product] = product_dict
            result.append({team: team_products})
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, result, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticated ,HasReportPermission])
def target_customer_sales_report(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "Target Customer Sales Report"
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        month_count = request.data.get("month_count", None)
        if not month_count:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
        date_ranges = report_services.get_monthly_date_ranges(month_count)

        # Dictionary to hold the aggregated data
        aggregated_result = {}

        for _, item in enumerate(date_ranges):
            # Assuming you execute the query with the provided start_date and end_date values
            sql_query = report_queries.target_customers_sales_query(item['start_date'], item['end_date'], user, team_names)
            cursor.execute(sql_query)
            results = cursor.fetchall()
            month = item['month']
            
            # Process the results
            for row in results:
                customer_name = row[0]  # Assuming Customer Name is the first column
                target_qty = row[1]     # Assuming Target Qty is the second column
                achv_qty = row[2]       # Assuming Achv Qty is the third column
                
                # Initialize the customer entry if not already present
                if customer_name not in aggregated_result:
                    aggregated_result[customer_name] = {
                        "Customer Name": customer_name,
                        "Target Qty": target_qty,
                        "month_data": []
                    }
                
                # Append the monthly data
                aggregated_result[customer_name]["month_data"].append({
                    "month_name": month,
                    "achvd_qty": achv_qty
                })

        # Convert aggregated result to the desired format
        final_result = list(aggregated_result.values())
        report_services.create_log(user=request.user,report_name=REPORT_NAME)
        return response(SUCCESS, final_result, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticated ])
def review_salesman_wise_data(request):
    try:
        user = request.user
        team_names = report_services.get_teamnames_for_user(user)
        if team_names == 'failed':
            return Response({"error": "This Manager name is not related to any Team"}, status=400)

        REPORT_NAME = "Review SalesMan Wise Report"
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        # Assuming you execute the query with the provided start_date and end_date values
        sql_query1 = report_queries.review_salesman_wise_query1(team_names)
        cursor.execute(sql_query1)
        results1 = cursor.fetchall()
        query1_data = [dict(zip([column[0] for column in cursor.description], row)) for row in results1]
        
        # Second Query Execution based on month_count
        month_count = request.data.get("month_count", None)
        if not month_count:
            return Response({"error": "Please provide month_count."}, status=HTTP_400_BAD_REQUEST)
        
        date_ranges = report_services.get_monthly_date_ranges(month_count)
        query2_data = defaultdict(list)

        for item in date_ranges:
            sql_query2 = report_queries.review_salesman_wise_query2(item['start_date'], item['end_date'], team_names)
            cursor.execute(sql_query2)
            results2 = cursor.fetchall()
            data2 = [dict(zip([column[0] for column in cursor.description], row)) for row in results2]
            month = item['month']
            query2_data[month].extend(data2)
        
        # Combine the data
        teams = defaultdict(lambda: {
            "team_target_qty": 0,
            "team_TargetCustomerCount": 0,
            "teamTargetCustomerReached": 0,
            "team_above_25_days_os": 0,
            "sales_persons": []
        })

        for q1 in query1_data:
            team_name = q1["Team Name"]
            sales_person = q1["Sales Person"]
            teams[team_name]["team_target_qty"] += q1["Target Qty"]
            teams[team_name]["team_TargetCustomerCount"] += q1["Target Customer Count"]
            teams[team_name]["teamTargetCustomerReached"] += q1["Target Customer Reached"]
            teams[team_name]["team_above_25_days_os"] += q1["Above 25 Days Outstanding"]
            
            # Initialize month_data
            month_data = []
            for month, month_results in query2_data.items():
                for q2 in month_results:
                    if q2["Team Name"] == team_name and q2["Sales Person"] == sales_person:
                        month_data.append({month: q2["Achv Qty"]})

            sales_person_data = {
                "sales_person": sales_person,
                "target_qty": q1["Target Qty"],
                "Target CustomerCount": q1["Target Customer Count"],
                "Target CustomerReached": q1["Target Customer Reached"],
                "above_25_days_os": q1["Above 25 Days Outstanding"],
                "month_data": month_data
            }
            
            teams[team_name]["sales_persons"].append(sales_person_data)
        
        # Format the combined data into a list
        combined_data = []
        for team_name, team_data in teams.items():
            team_data["team_name"] = team_name
            combined_data.append(team_data)

        # Log the report creation
        report_services.create_log(user=request.user, report_name=REPORT_NAME)
    
        return response(SUCCESS, combined_data, HTTP_200_OK)
    except Exception as e:
        logger.exception(f"an error occured while viewing the Report-{REPORT_NAME}: {e}")
        return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)
