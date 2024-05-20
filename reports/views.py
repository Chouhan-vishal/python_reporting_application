from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from reports.services import report_services
from collections import defaultdict
import datetime
# # from services.report_services import report_services
# # Create your views here.

# # @api_view(['GET'])
# # def report_data(request):
# #     start_date = request.data.get("start_date", None)
# #     end_date = request.data.get("end_date", None)
# #     conn = report_services.create_sql_server_connection()
# #     cursor = conn.cursor()
# #     query = f"""
# #         SELECT
# #             SV.[Team Name],
# #             SV.[Sales Person] AS [Sales person],
# #             ROUND(SUM(CAST(SV.[Target Qty] AS Decimal(10, 2))), 2) AS [Target Qty],
# #             ROUND(SUM(CAST(SAL.[Qty(MTs)] AS Decimal(10, 2))), 2) AS [Sales Quantity],
# #             ISNULL(
# #                 (
# #                     SELECT
# #                         ROUND(SUM(CAST(SAL2.[Qty(MTs)] AS Decimal(10, 2))), 2)
# #                     FROM
# #                         tbl_SalesVouchers AS SAL2 WITH (NOLOCK)
# #                         JOIN tbl_TargetCustomers AS SV2 WITH (NOLOCK) ON SAL2.[Sales Person -2] = SV2.[Sales Person]
# #                     WHERE
# #                         SV2.[Team Name] = SV.[Team Name]
# #                         AND CAST(SAL2.[Voucher Date] AS DATE) = DATEADD(DAY, -1, CAST(GETDATE() AS DATE))
# #                         AND MONTH(SAL2.[Voucher Date]) = MONTH(GETDATE())
# #                         AND YEAR(SAL2.[Voucher Date]) = YEAR(GETDATE())
# #                         AND SAL2.[Sales Person -2] = SV.[Sales Person] -- Filter by salesperson
# #                 ),
# #                 0
# #             ) AS [PreDaySalesValue],
# #             CASE 
# #                 WHEN ROUND(SUM(CAST(SAL.[Qty(MTs)] AS Decimal(10, 2))), 2) != 0 
# #                 THEN ROUND(SUM(CAST(SV.[Target Qty] AS Decimal(10, 2))) / SUM(CAST(SAL.[Qty(MTs)] AS Decimal(10, 2))), 2)
# #                 ELSE 0
# #             END AS [Achieved %]
# #         FROM
# #             [dbo].[tbl_TargetCustomers] SV WITH (NOLOCK)
# #             JOIN tbl_SalesVouchers AS SAL WITH (NOLOCK) ON SAL.[Sales Person -2] = SV.[Sales Person]
# #         WHERE 
# #             SAL.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
# #         GROUP BY
# #             SV.[Team Name],
# #             SV.[Sales Person];
    
# #     """
# #     cursor.execute(query)
# #     columns = [column[0] for column in cursor.description]
# #     results = cursor.fetchall()
# #     # for row in results:
# #     #     row_dict = dict(zip(columns, row))
# #     #     updated_results.append(row_dict)
# #     # response_data = {"sales_summary": updated_results}
# #     # return Response(response_data)
# #     # After fetching the results
# #     # team_sales_summary = defaultdict(list)

# #     # for row in results:
# #     #     team_name = row[0]  # Accessing the first element for team name
# #     #     sales_person = row[1]  # Accessing the second element for sales person
# #     #     sales_summary = {
# #     #         'Sales person': sales_person,
# #     #         'Target Qty': row[2],
# #     #         'Sales Quantity': row[3],
# #     #         'PreDaySalesValue': row[4],
# #     #         'Achieved %': row[5]
# #     #     }
# #     #     team_sales_summary[team_name].append(sales_summary)

# #     # # Convert defaultdict to regular dictionary
# #     # team_sales_summary = dict(team_sales_summary)

# #     # response_data = {"sales_summary": team_sales_summary}
# #     # return Response(response_data)

# #     team_sales_summary = defaultdict(dict)

# #     for row in results:
# #         team_name = row[0]  # Accessing the first element for team name
# #         sales_person = row[1]  # Accessing the second element for sales person
# #         sales_summary = {
# #             'sales_person': sales_person,
# #             'target_qty': row[2],
# #             'sales_quantity': row[3],
# #             'PreDaySalesValue': row[4],
# #             'achieved%': row[5]
# #         }
# #         # Check if team exists in team_sales_summary
# #         if team_name not in team_sales_summary:
# #             team_sales_summary[team_name] = {
# #                 'team_target_qty': 0,
# #                 'team_sales_quantity': 0,
# #                 'TeamPreDaySalesValue': 0,
# #                 'team_achieved%': 0,
# #                 'sales_persons': []
# #             }
        
# #         # Update team-level summary
# #         team_sales_summary[team_name]['team_target_qty'] += sales_summary['target_qty']
# #         team_sales_summary[team_name]['team_sales_quantity'] += sales_summary['sales_quantity']
# #         team_sales_summary[team_name]['TeamPreDaySalesValue'] += sales_summary['PreDaySalesValue']
        
# #         # Add individual sales summary under sales persons
# #         team_sales_summary[team_name]['sales_persons'].append(sales_summary)

# #     # Calculate team-level Achieved % after aggregation
# #     for team_name, team_summary in team_sales_summary.items():
# #         team_target_qty = team_summary['team_target_qty']
# #         team_sales_qty = team_summary['team_sales_quantity']
# #         if team_sales_qty != 0:
# #             team_summary['team_achieved%'] = round((team_target_qty / team_sales_qty), 2)

# #     # Convert defaultdict to regular dictionary
# #     team_sales_summary = dict(team_sales_summary)

# #     response_data = {"team_sales_summary": team_sales_summary}
# #     return Response(response_data)



# @api_view(['GET'])
# def report_data(request):
#     import pdb
#     pdb.set_trace()
#     start_date = request.data.get("start_date", None)
#     end_date = request.data.get("end_date", None)
#     if not start_date or not end_date:
#         return Response({"error": "Please provide both start_date and end_date."}, status=400)
#     start_date_obj = datetime.datetime.strptime(start_date, "%Y-%m-%d").date()
#     end_date_obj = datetime.datetime.strptime(end_date, "%Y-%m-%d").date()
#     # Get the current date
#     current_date = datetime.date.today()
#     # Simplified condition to check if the date range is within the current month
#     is_within_current_month = (
#         start_date_obj.year == current_date.year and start_date_obj.month == current_date.month and
#         end_date_obj.year == current_date.year and end_date_obj.month == current_date.month and
#         end_date_obj == current_date
#     )
#     sub_query = is_subquery_needed(is_within_current_month)
#     conn = report_services.create_sql_server_connection()
#     cursor = conn.cursor()
#     # Query with PreDaySalesValue
#     query = f'''
#         SELECT
#         ST.[Team Name],
#         ST.[Sales Person] AS [Sales person],
#         ROUND(SUM(CAST(TC.[Target Qty] AS Decimal(10, 2))), 2) AS [Target Qty],
#         ROUND(SUM(CAST(SV.[Qty(MTs)] AS Decimal(10, 2))), 2) AS [Sales Quantity],
#         {sub_query}
#         CASE 
#             WHEN ROUND(SUM(CAST(SV.[Qty(MTs)] AS Decimal(10, 2))), 2) != 0 
#             THEN ROUND(SUM(CAST(TC.[Target Qty] AS Decimal(10, 2))) / SUM(CAST(SV.[Qty(MTs)] AS Decimal(10, 2))), 2)
#             ELSE 0
#         END AS [Achieved %]
#         FROM
#             [dbo].[tbl_SalesTeam] ST WITH (NOLOCK)
#             JOIN tbl_SalesVouchers AS SV WITH (NOLOCK) ON SV.[Sales Person -2] = ST.[Sales Person]
#             JOIN tbl_TargetCustomers AS TC WITH (NOLOCK) ON TC.[Sales Person] = ST.[Sales Person]
#         WHERE 
#             SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'
#         GROUP BY
#             ST.[Team Name],
#             ST.[Sales Person];

#     '''
#     cursor.execute(query)
#     results = cursor.fetchall()
#     team_sales_summary = {}
#     for row in results:
#         team_name = row[0]  # Accessing the first element for team name
#         sales_person = row[1]  # Accessing the second element for sales person
#         sales_summary = {
#             'sales_person': sales_person,
#             'target_qty': row[2],
#             'sales_quantity': row[3],
#             'achieved%': row[4 if is_within_current_month else 3]
#         }
#         if is_within_current_month:
#             sales_summary['PreDaySalesValue'] = row[4]
#         # Check if team exists in team_sales_summary
#         if team_name not in team_sales_summary:
#             team_sales_summary[team_name] = {
#                 'team_target_qty': 0,
#                 'team_sales_quantity': 0,
#                 'team_achieved%': 0,
#                 'sales_persons': []
#             }
#             if is_within_current_month:
#                 team_sales_summary[team_name]['TeamPreDaySalesValue'] = 0
#         # Update team-level summary
#         team_sales_summary[team_name]['team_target_qty'] += sales_summary['target_qty']
#         team_sales_summary[team_name]['team_sales_quantity'] += sales_summary['sales_quantity']
#         if is_within_current_month:
#             team_sales_summary[team_name]['TeamPreDaySalesValue'] += sales_summary['PreDaySalesValue']
#         # Add individual sales summary under sales persons
#         team_sales_summary[team_name]['sales_persons'].append(sales_summary)
#     # Calculate team-level Achieved % after aggregation
#     for team_name, team_summary in team_sales_summary.items():
#         team_target_qty = team_summary['team_target_qty']
#         team_sales_qty = team_summary['team_sales_quantity']
#         if team_sales_qty != 0:
#             team_summary['team_achieved%'] = round((team_target_qty / team_sales_qty), 2)
#     response_data = {"team_sales_summary": team_sales_summary}
#     return Response(response_data)


# def is_subquery_needed(month):
#     if month:
#         sub_query = """
#         ISNULL(
#                 (
#                 SELECT
#                     ROUND(SUM(CAST(SV2.[Qty(MTs)] AS Decimal(10, 2))), 2)
#                 FROM
#                     tbl_SalesVouchers AS SV2 WITH (NOLOCK)
#                     JOIN tbl_SalesTeam AS ST2 WITH (NOLOCK) ON SV2.[Sales Person -2] = ST2.[Sales Person]
#                 WHERE
#                     ST2.[Team Name] = ST.[Team Name]
#                     AND CAST(SV2.[Voucher Date] AS DATE) = DATEADD(DAY, -1, CAST(GETDATE() AS DATE))
#                     AND MONTH(SV2.[Voucher Date]) = MONTH(GETDATE())
#                     AND YEAR(SV2.[Voucher Date]) = YEAR(GETDATE())
#                     AND SV2.[Sales Person -2] = ST.[Sales Person] -- Filter by salesperson
#             ),
#                 0
#             ) AS [PreDaySalesValue],
#         """
#         return sub_query
#     else:
#         return ''




@api_view(['GET'])
def sales_summary_report(request):
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
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()

    sql_query = f"""
    With SalesTeamCTE AS (
      Select   
              ST.[Team Name],   
              [Sales Person], 
              CAST(Getdate() as Date) as [Date],
              CAST(0  as Decimal(10,2)) as  [Target Qty] ,  
              CAST(0  as Decimal(10,2)) as  [Achv Qty] ,
              CAST(Getdate()-2  as Date) as [Previous Date]
      From [dbo].[tbl_SalesTeam] ST WITH(Nolock)  
    )
    , TargetCustomers AS (
      Select   Distinct  
              SV.[Team Name],    
              ROUND(SUM(CAST(SV.[Target Qty] as Decimal(10,2))),2) as [Target Qty], 
              SV.[Date] 
      From [dbo].[tbl_TargetCustomers] SV WITH(Nolock)   
      Where  [Item Category] <> 'Welding Electrodes'
      and SV.[Date] BETWEEN '{start_date}' AND '{end_date}'  
      GROUP BY 
              SV.[Team Name],
              SV.[Date] 
    )
    , Sales AS (
      Select      
              ST.[Team Name],   
              [Sales Person],
              SUM([Qty(MTs)] ) as [Achv Qty], 
              ST.[Previous Date] 
      From SalesTeamCTE ST 
      INNER JOIN [dbo].[tbl_SalesVouchers] SV WITH(Nolock) 
      ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person])) 
      and SV.[Item Details] <> 'Welding Electrodes'
      and SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'  
      GROUP BY 
              ST.[Team Name],    
              [Sales Person],
              ST.[Previous Date]
    )
    , PreviousDateQty AS (
      Select      
              ST.[Team Name],   
              [Sales Person],
              SUM(CAST([Qty(MTs)] as Decimal(10,2)))  as [Achv Qty],    
              ST.[Previous Date] 
      From SalesTeamCTE ST  
      LEFT JOIN [dbo].[tbl_SalesVouchers] SV WITH(Nolock) 
      ON LTRIM(RTRIM(SV.[Sales Person -2])) = LTRIM(RTRIM(ST.[Sales Person])) 
      and SV.[Voucher Date] BETWEEN '{start_date}' AND '{end_date}'  
      and CAST( SV.[Voucher Date]  as Date) = CAST(GETDATE()-2  as Date)   --Previous Date
      GROUP BY 
              ST.[Team Name],    
              [Sales Person],
              ST.[Previous Date]
    )
    Select Distinct 
      ST.[Team Name],
      ST.[Sales Person],
      (Select [Target Qty] From TargetCustomers  where TargetCustomers.[Team Name] = ST.[Team Name]) as [Target Qty],  
      (Select [Achv Qty] From Sales Where Sales.[Team Name] = ST.[Team Name] and Sales.[Sales Person] = ST.[Sales Person]) as [Achv Qty],
      ISNULL(ROUND(CAST((Select [Achv Qty] From Sales Where Sales.[Team Name] = ST.[Team Name] and Sales.[Sales Person] = ST.[Sales Person]) as float) / NULLIF(CAST((Select [Target Qty] From TargetCustomers  where TargetCustomers.[Team Name] = ST.[Team Name]) as float),0) *100 ,0),0)  as [Achv %] ,
     (Select [Achv Qty] From PreviousDateQty Where PreviousDateQty.[Team Name] = ST.[Team Name] and PreviousDateQty.[Sales Person] = ST.[Sales Person])
     as [Previous Date Qty]
    From SalesTeamCTE ST
    Where ST.[Date] BETWEEN '{start_date}' AND '{end_date}'  
    Order By ST.[Team Name], ST.[Sales Person];
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
        'TeamPreDaySalesValue': 0 if is_within_current_month else None
    })
    for row in results:
        team_name = row[0]
        sales_person = row[1]
        sales_summary = {
            'sales_person': sales_person,
            'target_qty': row[2] if row[2] is not None else 0,
            'sales_quantity': row[3] if row[3] is not None else 0,
            'achieved%': row[4] if row[4] is not None else 0,
            'PreDaySalesValue': row[5] if is_within_current_month else None,
        }
        team_sales_summary[team_name]['team_target_qty'] += sales_summary['target_qty']
        team_sales_summary[team_name]['team_sales_quantity'] += sales_summary['sales_quantity']
        if is_within_current_month:
            team_sales_summary[team_name]['TeamPreDaySalesValue'] += sales_summary['previous_date_qty']
        team_sales_summary[team_name]['sales_persons'].append(sales_summary)
    for team_name, team_summary in team_sales_summary.items():
        team_target_qty = team_summary['team_target_qty']
        team_sales_qty = team_summary['team_sales_quantity']
        if team_target_qty != 0:
            team_summary['team_achieved%'] = round((team_sales_qty / team_target_qty) * 100, 2)
    response_data = {"team_sales_summary": dict(team_sales_summary)}
    return Response(response_data)

