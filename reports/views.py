from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from reports.services import report_services, report_queries
from django.db import connection, DatabaseError
from rest_framework.views import APIView
from collections import defaultdict
import logging
from datetime import datetime, timedelta


logger = logging.getLogger('reports')

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sales_summary_report(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    pre_date = report_services.get_previous_date(end_date)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    sql_query = report_queries.sales_summary_query(start_date, end_date, pre_date)
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
    
    for team_name, team_summary in team_sales_summary.items():
        team_target_qty = team_summary['team_target_qty']
        team_sales_qty = team_summary['team_sales_quantity']
        if team_target_qty != 0:
            team_summary['team_achieved%'] = round((team_sales_qty / team_target_qty) * 100, 2)
    response_data = {"team_sales_summary": dict(team_sales_summary)}
    cursor.close()
    conn.close()
    return Response(response_data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def sales_collection_outstanding_report(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    pre_date = report_services.get_previous_date(end_date)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    query = report_queries.sales_collection_outstanding_summary(start_date, end_date, pre_date)
    cursor.execute(query)

    results = cursor.fetchall()
    team_sales_summary = {}
    team_sales_summary = defaultdict(lambda: {
        'Team Pre Day Sales(MTs)': 0,
        'Team Pre Day Collection': 0,
        'Team Overall Outstanding Amt': 0,
        'Team Above 25 Days O/S': 0,
        'Team Above 45 Days O/S': 0,
        'Team Above 90 Days O/S': 0,
        'Team sales persons': []
    })
    for row in results:
        team_name = row[0]
        sales_person = row[1]
        sales_summary = {
            'Sales Person': sales_person,
            'Pre Day Sales(MTs)': row[2],
            'Pre Day Collection': row[3],
            'Overall Outstanding Amt': row[4],
            'Team Above 25 Days O/S':row[5],
            'Team Above 45 Days O/S': row[6],
            'Team Above 90 Days O/S': row[7]
        }
        # Update team summary values
        team_sales_summary[team_name]['Team Pre Day Sales(MTs)'] += row[2]
        team_sales_summary[team_name]['Team Pre Day Collection'] += row[3]
        team_sales_summary[team_name]['Team Overall Outstanding Amt'] += row[4]
        team_sales_summary[team_name]['Team Above 25 Days O/S'] += row[5]
        team_sales_summary[team_name]['Team Above 45 Days O/S'] += row[6]
        team_sales_summary[team_name]['Team Above 90 Days O/S'] += row[7]

        # Append sales person summary to the team
        team_sales_summary[team_name]['Team sales persons'].append(sales_summary)
    team_sales_summary = dict(team_sales_summary)
    cursor.close()
    conn.close()
    return Response(team_sales_summary)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def product_wise_sales_summary(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    pre_date = report_services.get_previous_date(end_date)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    query = report_queries.product_wise_sales_summary_query(start_date, end_date, pre_date)
    cursor.execute(query)

    results = cursor.fetchall()
    columns = [col[0] for col in cursor.description]

    data = []
    for row in results:
        record = dict(zip(columns, row))
        # Handling Nulls
        if record['Pre Day Sales'] is None:
            record['Pre Day Sales'] = 0
        if record['Achievement Percentage'] is None:
            record['Achievement Percentage'] = 0
        data.append(record)
    final_response = {"Product wise sales": data}
    return Response(final_response)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def weekly_summary(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    query = report_queries.weekly_report_query(start_date, end_date)
    cursor.execute(query)
    results = cursor.fetchall()

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
        team_name = row[3]
        salesman = row[4]
        sales_summary = {
            'Salesman': salesman,
            'Target Qty(MTs)': row[5],
            'Achvd Qty(MTs)': row[6],
            'Pending Target': row[8],
            'Weekly Target': row[10],
            'Collection Target': row[11],
            'Collection Achived': row[12],
            'Weekly Achved Qty(MTs)': row[13]
        }
        
        # Update team summary values
        team_sales_summary[team_name]['Target Qty(MTs)'] += row[5]
        team_sales_summary[team_name]['Achvd Qty(MTs)'] += row[6]
        team_sales_summary[team_name]['Pending Target'] += row[8]
        team_sales_summary[team_name]['Weekly Target'] += row[10]
        team_sales_summary[team_name]['Collection Target'] += row[11]
        team_sales_summary[team_name]['Collection Achived'] += row[12]
        team_sales_summary[team_name]['Weekly Achved Qty(MTs)'] += row[13]
        
        # Append salesmen summary to the team
        team_sales_summary[team_name]['Salesmen'].append(sales_summary)

    # Close cursor and connection
    cursor.close()
    conn.close()

    # Convert defaultdict to regular dictionary
    team_sales_summary = dict(team_sales_summary)
    return Response(team_sales_summary)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def collection_report(request):
    start_date_str = request.data.get("start_date")
    end_date_str = request.data.get("end_date")
    
    if not start_date_str or not end_date_str:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    team_totals = {}
    
    current_date = start_date
    while current_date <= end_date:
        query = report_queries.collection_report_by_date_range(current_date)
        cursor.execute(query)
        data = cursor.fetchall()
        
        for row in data:
            team_name, sales_person, total_collection = row
            receipt_date = current_date.strftime('%Y-%m-%d')
            
            if team_name not in team_totals:
                team_totals[team_name] = {}
            
            if receipt_date not in team_totals[team_name]:
                team_totals[team_name][receipt_date] = {
                    "TotalCollection": 0,
                    "IndividualSales": {}
                }
                
            team_totals[team_name][receipt_date]["TotalCollection"] += total_collection
            team_totals[team_name][receipt_date]["IndividualSales"][sales_person] = total_collection
            
        current_date += timedelta(days=1)
    
    conn.close()
    
    return Response(team_totals)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def customer_wise_outstanding(request):

    outstanding_value = request.data.get("outstanding")
    outstanding_days = [0, 25, 45, 90]
    if outstanding_value not in outstanding_days:
        return Response({"error": "Please provide valid outstanding day value"}, status=400)
    # Define the raw SQL query

    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    sql_query = report_queries.customer_wise_outstanding_query(outstanding_value)
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
    # Return response with fetched data and total outstanding sum
    return Response({f"Customer wise {outstanding_value} Days O/S":formatted_data,"total_outstanding_sum": total_outstanding_sum})


@api_view(["POST"])
# @permission_classes([IsAuthenticated])
def cr_utilization_report(request):
    import pdb
    from django.http import JsonResponse  # Assuming you're using Django
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    sql_query = report_queries.cr_utilization_report_query()
    cursor.execute(sql_query)

    # Fetch data
    data = cursor.fetchall()
    
    # Format data
    query_data = []
    for row in data:
        formatted_row = {
            'Team Name': row[0],
            'Sales Person': row[1],
            'Customer ID': row[3],
            'Customer Name': row[2],
            'Target Qty (MTs)': row[4],
            'CR limit': row[5],
            'OS': row[6],
            'Cr Utliz %': row[7]
        }
        query_data.append(formatted_row)
    
    return JsonResponse({"cr_utilization_report": query_data})
