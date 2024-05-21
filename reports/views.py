from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from reports.services import report_services
from collections import defaultdict
from datetime import datetime, timedelta

@api_view(['GET'])
def sales_summary_report(request):
    start_date = request.data.get("start_date", None)
    end_date = request.data.get("end_date", None)
    if not start_date or not end_date:
        return Response({"error": "Please provide both start_date and end_date."}, status=400)
    pre_date = report_services.get_previous_date(end_date)
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    sql_query = f"""
        WITH SalesTeamCTE AS (
            SELECT   
                ST.[Team Name],   
                [Sales Person], 
                CAST(GETDATE() AS DATE) AS [Date],
                CAST(0 AS DECIMAL(10, 2)) AS [Target Qty],  
                CAST(0 AS DECIMAL(10, 2)) AS [Achv Qty],
                CAST(GETDATE() - 2 AS DATE) AS [Previous Date]
            FROM [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
        ),
        TargetCustomers AS (
            SELECT DISTINCT  
                SV.[Team Name],    
                [Sales Person],
                ROUND(SUM(CAST(SV.[Target Qty] AS DECIMAL(10, 2))), 2) AS [Target Qty], 
                SV.[Date] 
            FROM [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)
            WHERE [Item Category] <> 'Welding Electrodes'
            GROUP BY 
                SV.[Team Name],
                [Sales Person],
                SV.[Date]
        ),
        Sales AS (
            SELECT      
                ST.[Team Name],   
                [Sales Person],
                SUM([Qty(MTs)]) AS [Achv Qty], 
                ST.[Previous Date]
            FROM SalesTeamCTE ST
            INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
                ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
                AND SV.[Item Details] <> 'Welding Electrodes'
                AND SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
            GROUP BY 
                ST.[Team Name],    
                [Sales Person],
                ST.[Previous Date]
        ),
        PreviousDateQty AS (
        SELECT
            ST.[Team Name],
            [Sales Person],
            SUM([Qty(MTs)]) AS [Achv Qty]
        FROM [dbo].[tbl_SalesVouchers] SV WITH (NOLOCK)
        INNER JOIN [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
            ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person]))
        WHERE SV.[Item Details] <> 'Welding Electrodes'
        AND CAST(SV.[Voucher Date] AS DATE) = '{pre_date}'
        GROUP BY ST.[Team Name], [Sales Person]
        )
        SELECT DISTINCT 
            ST.[Team Name],
            ST.[Sales Person],
            ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS [Target Qty],  
            ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS [Achv Qty],
            ISNULL(ROUND(CAST(ISNULL((SELECT [Achv Qty] FROM Sales WHERE Sales.[Team Name] = ST.[Team Name] AND Sales.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT) / NULLIF(CAST(ISNULL((SELECT [Target Qty] FROM TargetCustomers WHERE TargetCustomers.[Team Name] = ST.[Team Name] AND TargetCustomers.[Sales Person] = ST.[Sales Person]), 0) AS FLOAT), 0) * 100, 0), 0) AS [Achv %],
            ISNULL((SELECT [Achv Qty] FROM PreviousDateQty WHERE PreviousDateQty.[Team Name] = ST.[Team Name] AND PreviousDateQty.[Sales Person] = ST.[Sales Person]), 0) AS [Previous Date Qty]
        FROM SalesTeamCTE ST
        ORDER BY ST.[Team Name], ST.[Sales Person];
    """
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
    return Response(response_data)
