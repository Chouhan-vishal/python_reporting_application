from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from reports.services import report_services, report_queries
from collections import defaultdict

@api_view(['GET'])
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


@api_view(['GET'])
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
