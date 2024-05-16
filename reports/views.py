from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from reports.services import report_services
from collections import defaultdict
import datetime

@api_view(['GET'])
def report_data(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
    end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
    # Get the current date
    current_date = datetime.date.today()
    # Simplified condition to check if the date range is within the current month
    is_within_current_month = (
        start_date_obj.year == current_date.year and start_date_obj.month == current_date.month and
        end_date_obj.year == current_date.year and end_date_obj.month == current_date.month and
        end_date_obj == current_date
    )
    sub_query = is_subquery_needed(is_within_current_month)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    # Query with PreDaySalesValue
    query = f'''
        SELECT
        ST.[Team Name],
        ST.[Sales Person] AS [Sales person],
        ROUND(SUM(CAST(TC.[Target Qty] AS Decimal(10, 2))), 2) AS [Target Qty],
        ROUND(SUM(CAST(SV.[Qty(MTs)] AS Decimal(10, 2))), 2) AS [Sales Quantity],
        {sub_query}
        CASE 
            WHEN ROUND(SUM(CAST(SV.[Qty(MTs)] AS Decimal(10, 2))), 2) != 0 
            THEN ROUND(SUM(CAST(TC.[Target Qty] AS Decimal(10, 2))) / SUM(CAST(SV.[Qty(MTs)] AS Decimal(10, 2))), 2)
            ELSE 0
        END AS [Achieved %]
        FROM
            [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
            JOIN tbl_SalesVouchers AS SV WITH (NOLOCK) ON SV.[Sales Person -2] = ST.[Sales Person]
            JOIN tbl_TargetCustomers AS TC WITH (NOLOCK) ON TC.[Sales Person] = ST.[Sales Person]
        WHERE 
            SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
        GROUP BY
            ST.[Team Name],
            ST.[Sales Person];

    '''
    cursor.execute(query)
    results = cursor.fetchall()
    team_sales_summary = {}
    for row in results:
        team_name = row[0]  # Accessing the first element for team name
        sales_person = row[1]  # Accessing the second element for sales person
        sales_summary = {
            'sales_person': sales_person,
            'target_qty': row[2],
            'sales_quantity': row[3],
            'achieved%': row[4 if is_within_current_month else 3]
        }
        if is_within_current_month:
            sales_summary['PreDaySalesValue'] = row[4]
        # Check if team exists in team_sales_summary
        if team_name not in team_sales_summary:
            team_sales_summary[team_name] = {
                'team_target_qty': 0,
                'team_sales_quantity': 0,
                'team_achieved%': 0,
                'sales_persons': []
            }
            if is_within_current_month:
                team_sales_summary[team_name]['TeamPreDaySalesValue'] = 0
        # Update team-level summary
        team_sales_summary[team_name]['team_target_qty'] += sales_summary['target_qty']
        team_sales_summary[team_name]['team_sales_quantity'] += sales_summary['sales_quantity']
        if is_within_current_month:
            team_sales_summary[team_name]['TeamPreDaySalesValue'] += sales_summary['PreDaySalesValue']
        # Add individual sales summary under sales persons
        team_sales_summary[team_name]['sales_persons'].append(sales_summary)
    # Calculate team-level Achieved % after aggregation
    for team_name, team_summary in team_sales_summary.items():
        team_target_qty = team_summary['team_target_qty']
        team_sales_qty = team_summary['team_sales_quantity']
        if team_sales_qty != 0:
            team_summary['team_achieved%'] = round((team_target_qty / team_sales_qty), 2)
    response_data = {"team_sales_summary": team_sales_summary}
    return Response(response_data)


def is_subquery_needed(month):
    if month:
        sub_query = """
        ISNULL(
                (
                SELECT
                    ROUND(SUM(CAST(SV2.[Qty(MTs)] AS Decimal(10, 2))), 2)
                FROM
                    tbl_SalesVouchers AS SV2 WITH (NOLOCK)
                    JOIN tbl_SalesTeam AS ST2 WITH (NOLOCK) ON SV2.[Sales Person -2] = ST2.[Sales Person]
                WHERE
                    ST2.[Team Name] = ST.[Team Name]
                    AND CAST(SV2.[Voucher Date] AS DATE) = DATEADD(DAY, -1, CAST(GETDATE() AS DATE))
                    AND MONTH(SV2.[Voucher Date]) = MONTH(GETDATE())
                    AND YEAR(SV2.[Voucher Date]) = YEAR(GETDATE())
                    AND SV2.[Sales Person -2] = ST.[Sales Person] -- Filter by salesperson
            ),
                0
            ) AS [PreDaySalesValue],
        """
        return sub_query
    else:
        return ''