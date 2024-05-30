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
    query = report_queries.sales_collection_outstanding_summary(pre_date)
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

    return Response(result)


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
        if record['pre_day_sales'] is None:
            record['pre_day_sales'] = 0
        if record['achievement_percentage'] is None:
            record['achievement_percentage'] = 0
        data.append(record)
    final_response = {"product_wise_sales": data}

    # Closing the cursor and connection
    cursor.close()
    conn.close()
    return Response(final_response)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def weekly_summary(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    today_is_monday = datetime.today().weekday() == 0
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    query = report_queries.weekly_report_query(start_date, end_date)
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

    return Response(team_sales_list)

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
    team_totals = defaultdict(lambda: defaultdict(lambda: {"TotalCollection": 0, "IndividualSales": {}}))
    
    current_date = start_date
    while current_date <= end_date:
        query = report_queries.collection_report_by_date_range(current_date)
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
            result.append({
                "TeamName": team_name,
                "ReceiptDate": receipt_date,
                "TotalCollection": collections["TotalCollection"],
                "IndividualSales": collections["IndividualSales"]
            })
    
    # Closing the cursor and connection
    cursor.close()
    conn.close()
    
    return Response(result)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def customer_wise_outstanding(request):
    outstanding_value = request.data.get("outstanding")
    team_name = request.data.get("team_name")
    salesman = request.data.get("salesman")
    outstanding_days = [0, 25, 45, 90]
    if outstanding_value not in outstanding_days:
        return Response({"error": "Please provide valid outstanding day value"}, status=400)
    # Define the raw SQL query

    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    sql_query = report_queries.customer_wise_outstanding_query(outstanding_value, team_name, salesman)
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
@permission_classes([IsAuthenticated])
def cr_utilization_report(request):
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    team_name = request.data.get("team_name")
    salesman = request.data.get("salesman")
    sql_query = report_queries.cr_utilization_report_query(team_name, salesman)
    cursor.execute(sql_query)

    # Fetch data
    data = cursor.fetchall()
    
    # Initialize a nested dictionary to hold the grouped data
    grouped_data = defaultdict(lambda: defaultdict(list))

    # Organize data by team name and sales person
    for row in data:
        team_name = row[0]
        sales_person = row[1]
        customer_data = {
            'Customer ID': row[3],
            'Customer Name': row[2],
            'Target Qty (MTs)': row[4],
            'CR limit': row[5],
            'OS': row[6],
            'Cr Utliz %': row[7]
        }
        grouped_data[team_name][sales_person].append(customer_data)
    
    # Format the grouped data into the desired structure
    formatted_data = []
    for team_name, sales_persons in grouped_data.items():
        for sales_person, customers in sales_persons.items():
            formatted_data.append({
                'Team Name': team_name,
                'Sales Person': sales_person,
                'Customers': customers
            })
    
    # Closing the cursor and connection
    cursor.close()
    conn.close()

    return Response(formatted_data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def team_and_product_wise_report(request):
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    sql_query = report_queries.team_and_product_wise_query()
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


@api_view(["POST"])
# @permission_classes([IsAuthenticated])
def salesman_and_product_wise_report(request):
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    team_name = request.data.get("team_name")
    salesman = request.data.get("salesman")
    
    sql_query = report_queries.salesman_and_product_wise_query(team_name, salesman)
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

    return Response(formatted_data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def target_and_achieved_report(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    pre_date = report_services.get_previous_date(end_date)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    sql_query = report_queries.target_and_achieved_query(start_date, end_date, pre_date)
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

    return Response(team_sales_summary_list)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def welding_electrode_product_sales_report(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    sql_query = report_queries.welding_electrode_product_sales_query(start_date, end_date)
    # Assuming you execute the query with the provided start_date and end_date values
    cursor.execute(sql_query)
    results = cursor.fetchall()
    team_sales_summary = {}
    team_sales_summary = defaultdict(lambda: {
        'team_target_qty': 0,
        'team_sales_quantity': 0,
        'team_achieved%': 0,
        'sales_persons': []
    })
    for row in results:
        team_name = row[0]
        sales_person = row[1]
        sales_summary = {
            'sales_person': sales_person,
            'target_qty': row[2],
            'sales_quantity': row[3],
            'achieved%': row[4]
        }
        team_sales_summary[team_name]['team_target_qty'] += sales_summary['target_qty']
        team_sales_summary[team_name]['team_sales_quantity'] += sales_summary['sales_quantity']
        team_sales_summary[team_name]['sales_persons'].append(sales_summary)

    for team_name, team_summary in team_sales_summary.items():
        team_target_qty = team_summary['team_target_qty']
        team_sales_qty = team_summary['team_sales_quantity']
        if team_target_qty != 0:
            team_summary['team_achieved%'] = round((team_sales_qty / team_target_qty) * 100, 2)
    response_data = {"welding_electrode_product_sales_report": dict(team_sales_summary)}
    cursor.close()
    conn.close()

    return Response(response_data)


@api_view(["POST"])
# @permission_classes([IsAuthenticated])
def durastrong_tmt_product_sales_report(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    sql_query = report_queries.durastrong_tmt_product_sales_query(start_date, end_date)
    # Assuming you execute the query with the provided start_date and end_date values
    cursor.execute(sql_query)
    results = cursor.fetchall()
    team_sales_summary = {}
    team_sales_summary = defaultdict(lambda: {
        'team_target_qty': 0,
        'team_sales_quantity': 0,
        'team_achieved%': 0,
        'sales_persons': []
    })
    for row in results:
        team_name = row[0]
        sales_person = row[1]
        sales_summary = {
            'sales_person': sales_person,
            'target_qty': row[2],
            'sales_quantity': row[3],
            'achieved%': row[4]
        }
        team_sales_summary[team_name]['team_target_qty'] += sales_summary['target_qty']
        team_sales_summary[team_name]['team_sales_quantity'] += sales_summary['sales_quantity']
        team_sales_summary[team_name]['sales_persons'].append(sales_summary)

    for team_name, team_summary in team_sales_summary.items():
        team_target_qty = team_summary['team_target_qty']
        team_sales_qty = team_summary['team_sales_quantity']
        if team_target_qty != 0:
            team_summary['team_achieved%'] = round((team_sales_qty / team_target_qty) * 100, 2)
    response_data = {"durastrong_tmt_product_sales_report": dict(team_sales_summary)}
    cursor.close()
    conn.close()

    return Response(response_data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def sales_register_report(request):
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

    return Response(data)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def block_customers_list_report(request):
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    # Assuming you execute the query with the provided start_date and end_date values
    sql_query = report_queries.block_customers_list_query()
    cursor.execute(sql_query)
    results = cursor.fetchall()
    data = [dict(zip([column[0] for column in cursor.description], row)) for row in results]

    return Response(data)

@api_view(["POST"])
# @permission_classes([IsAuthenticated])
def target_customers_mom_report(request):
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    month_count = request.data.get("month_count", None)
    if not month_count:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    date_ranges = report_services.get_monthly_date_ranges(month_count)
    result = {}

    for _, item in enumerate(date_ranges):
        # Assuming you execute the query with the provided start_date and end_date values
        sql_query = report_queries.target_customers_mom_query(item['start_date'], item['end_date'])
        cursor.execute(sql_query)
        results = cursor.fetchall()
        data = [dict(zip([column[0] for column in cursor.description], row)) for row in results]
        month = item['month']
        result[month] = data

    return Response(result)
