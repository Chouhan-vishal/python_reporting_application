import logging
from collections import defaultdict
from rest_framework import serializers
from reports.models import ProductGroup
from datetime import datetime, timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from reporting_application.constants import *
from users.services.utils import extend_schema
from users.services.utils import drf_schema, response
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from reports.services import report_services, report_queries, dashboard_queries
from reports.services.report_services import HasReportPermission, is_month_last_week, find_max_date

logger = logging.getLogger('reports')

class SalesSummary(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = 'Sales Summary Report'
    def fetch_sales_summary(self, start_date, end_date, pre_date, salesman_names):
        conn = report_services.create_sql_server_connection()
        try:
            cursor = conn.cursor()
            sql_query = report_queries.sales_summary_query(start_date, end_date, pre_date, salesman_names)
            # Assuming you execute the query with the provided start_date and end_date values
            cursor.execute(sql_query)
            results = cursor.fetchall()
        finally:
            cursor.close()
            conn.close()
        return results
    
    def process_sales_results(self, results, month_count = 1):
        team_sales_summary = defaultdict(lambda: {
            'team_target_qty': 0,
            'team_sales_quantity': 0,
            'team_achieved%': 0,
            'sales_persons': [],
            'TeamPreDaySalesValue': 0
        })

        for row in results:
            team_name, sales_person, target_qty, sales_quantity, achieved_pct, pre_day_sales_value = row
            if target_qty == 0 and sales_quantity == 0 and pre_day_sales_value == 0:
                continue
            sales_summary = {
                'sales_person': sales_person,
                'target_qty': target_qty * month_count,
                'sales_quantity': sales_quantity,
                'achieved%':(sales_quantity / (target_qty * month_count) * 100) if target_qty != 0 else 0,
                'PreDaySalesValue': pre_day_sales_value,
            }
            team_sales_summary[team_name]['team_target_qty'] += sales_summary['target_qty']
            team_sales_summary[team_name]['team_sales_quantity'] += sales_summary['sales_quantity']
            team_sales_summary[team_name]['TeamPreDaySalesValue'] += sales_summary['PreDaySalesValue']
            team_sales_summary[team_name]['sales_persons'].append(sales_summary)
        
        return team_sales_summary

    def format_response_data(self, team_sales_summary):
        response_data = [
            {
                'team_name': team_name,
                'team_target_qty': team_summary['team_target_qty'],
                'team_sales_quantity': team_summary['team_sales_quantity'],
                'team_achieved%': round((team_summary['team_sales_quantity'] / team_summary['team_target_qty']) * 100, 2) if team_summary['team_target_qty'] != 0 else 0,
                'TeamPreDaySalesValue': team_summary['TeamPreDaySalesValue'],
                'sales_persons': team_summary['sales_persons']
            }
            for team_name, team_summary in team_sales_summary.items()
        ]
        return response_data
    
    @drf_schema(serializer_name="DateSerializer")
    def post(self,request):
        try:
            user = request.user
            start_date = request.data.get("start_date", None)
            end_date = request.data.get("end_date", None)

            try:
                salesman_names = report_services.get_salesmans_for_user(user)
            except Exception as e:
                return Response({"error": str(e)}, status=400)
            
            if not start_date or not end_date:
                return Response({"error": "Please provide both start_date and end_date."}, status=400)
            
            month_count  = report_services.count_months(start_date, end_date)            
            pre_date = report_services.get_previous_date(end_date)
            results = self.fetch_sales_summary(start_date, end_date, pre_date, salesman_names)
            team_sales_summary = self.process_sales_results(results, month_count)
            response_data = self.format_response_data(team_sales_summary)
            
            max_date = find_max_date()
            
            # response_data["refresh_date"] = max_date           
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, response_data, HTTP_200_OK, max_date)
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class SalesCollectionOutstanding(APIView):
    REPORT_NAME = 'Sales Collection Outstanding Report'
    permission_classes = [IsAuthenticated, HasReportPermission]
    def process_sales_collections_outstanding_results(self,results):
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
            team_name,sales_person,pre_day_sales_mts,pre_day_collection,overall_outstanding_amt,above_25_days_os,above_45_days_os,above_90_days_os = row[0],row[1],row[2], row[3], row[4], row[5], row[6], row[7]
            if pre_day_sales_mts == 0 and pre_day_collection == 0 and overall_outstanding_amt ==0 and above_25_days_os==0 and above_45_days_os == 0 and above_90_days_os == 0:
                continue
            
            sales_summary = {
                'sales_person': sales_person,
                'pre_day_sales_mts': pre_day_sales_mts,
                'pre_day_collection': pre_day_collection,
                'overall_outstanding_amt': overall_outstanding_amt,
                'above_25_days_os': above_25_days_os,
                'above_45_days_os': above_45_days_os,
                'above_90_days_os': above_90_days_os
            }
            # Update team summary values
            team_sales_summary[team_name]['team_pre_day_sales_mts'] += pre_day_sales_mts
            team_sales_summary[team_name]['team_pre_day_collection'] += pre_day_collection
            team_sales_summary[team_name]['team_overall_outstanding_amt'] += overall_outstanding_amt
            team_sales_summary[team_name]['team_above_25_days_os'] += above_25_days_os
            team_sales_summary[team_name]['team_above_45_days_os'] += above_45_days_os
            team_sales_summary[team_name]['team_above_90_days_os'] += above_90_days_os

            # Append sales person summary to the team
            team_sales_summary[team_name]['team_sales_persons'].append(sales_summary)

        return team_sales_summary

    def format_sales_collection_outstanding(self,team_sales_summary):
        return [
            {
                'team_name': team_name,
                'team_pre_day_sales_mts': summary['team_pre_day_sales_mts'],
                'team_pre_day_collection': summary['team_pre_day_collection'],
                'team_overall_outstanding_amt': summary['team_overall_outstanding_amt'],
                'team_above_25_days_os': summary['team_above_25_days_os'],
                'team_above_45_days_os': summary['team_above_45_days_os'],
                'team_above_90_days_os': summary['team_above_90_days_os'],
                'team_sales_persons': summary['team_sales_persons']
            }
            for team_name, summary in team_sales_summary.items()
        ]
    def fetch_sales_collection_outstanding_summary(self,pre_date, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        query = report_queries.sales_collection_outstanding_summary(pre_date, salesman_names)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    
    @drf_schema(serializer_name="DateSerializer")
    def post(self,request):
        try:
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            start_date = request.data.get("start_date", None)
            end_date = request.data.get("end_date", None)
            if not start_date or not end_date:
                return Response({"error": "Please provide both start_date and end_date."}, status=400)
        
            pre_date = report_services.get_previous_date(end_date)
            results = self.fetch_sales_collection_outstanding_summary(pre_date, salesman_names)
            team_sales_summary = self.process_sales_collections_outstanding_results(results)
            result = self.format_sales_collection_outstanding(team_sales_summary)

            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, result, HTTP_200_OK)
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class ProductWiseSalesSummary(APIView):
    REPORT_NAME = "Product Wise Sales Summary"
    permission_classes = [IsAuthenticated, HasReportPermission]
    def fetch_product_wise_sales_summary(self,start_date, end_date, pre_date, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        query = report_queries.product_wise_sales_summary_query(start_date, end_date, pre_date, salesman_names)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()

        return results

    @drf_schema(serializer_name="DateSerializer")
    def post(self,request):
        try:
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user)
            except Exception as e:
                return Response({"error": str(e)}, status=400)
            
            start_date, end_date = request.data.get("start_date", None), request.data.get("end_date", None)

            if not start_date or not end_date:
                return Response({"error": "Please provide both start_date and end_date."}, status=400)
            
            month_count  = report_services.count_months(start_date, end_date)

            pre_date = report_services.get_previous_date(end_date)
            results = self.fetch_product_wise_sales_summary(start_date, end_date, pre_date, salesman_names)

            # Initialize an empty dictionary to store the final result
            final_result = {}

            # Iterate through the data and process it within the same loop
            for entry in results:
                team_name = entry[1]
                product_name = entry[2]
                
                # Calculate values based on input, ensuring that None values are handled
                target_qty = (float(entry[3]) if entry[3] is not None else 0.0) * month_count
                achieved = float(entry[4]) if entry[4] is not None else 0.0
                pre_day = float(entry[8]) if entry[8] is not None else 0.0

                # Calculate the achieved percentage (achvd_per), handling division by zero
                achvd_per = (achieved / target_qty * 100) if target_qty > 0 else 0.0

                # If the team_name doesn't exist in the final_result, add it
                if team_name not in final_result:
                    final_result[team_name] = []

                # Append product details as a dictionary under the corresponding team
                final_result[team_name].append({
                    'product_name': product_name,
                    'target_qty': target_qty,
                    'sales_quantity': achieved,
                    'pre_day': pre_day,
                    'achieved%': achvd_per
                })

            # Convert final_result to the desired list of dictionaries format
            result_list = [
                {'team_name': team, 'products': products}
                for team, products in final_result.items()
            ]
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, result_list, HTTP_200_OK)

        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class WeeklySummary(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "Weekly Summary Report"
    def fetch_weekly_summary(self,user, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        query = report_queries.weekly_report_query(user, salesman_names)
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results

    def process_weekly_summary_results(self,results, today_is_monday):
        team_sales_list = []

        team_sales_summary = defaultdict(lambda: {
            'Target Qty(MTs)': 0,
            'Achvd Qty(MTs)': 0,
            'Pending Target': 0,
            'Weekly Target': 0,
            'Weekly Achved Qty(MTs)': 0,
            'Collection Target': 0,
            'Collection Achived': 0,
            'Salesmen': []
        })
        # Process query results
        for row in results:
            pending_taget = row[8]
            pending_taget = max(pending_taget, 0)

            weekly_target = pending_taget if today_is_monday else row[10]
            team_name = row[3]
            salesman = row[4]
            if row[5] ==0 and row[6] == 0 and pending_taget ==0 and weekly_target ==0 and row[13] ==0:
                continue
                
            if is_month_last_week:
                weekly_target = pending_taget

            sales_summary = {
                'Salesman': salesman,
                'Target Qty(MTs)': row[5],
                'Achvd Qty(MTs)': row[6],
                'Pending Target': pending_taget,
                'Weekly Target': weekly_target,
                'Weekly Achved Qty(MTs)': row[13],
                'Collection Target': row[11],
                'Collection Achived': row[12]
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
        return team_sales_list

    def post(self,request):
        try:
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            today_is_monday = datetime.today().weekday() == 0
            results  = self.fetch_weekly_summary(user, salesman_names)
            team_sales_list = self.process_weekly_summary_results(results, today_is_monday)
            
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, team_sales_list, HTTP_200_OK)
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class Collection(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "Collection Report"
    def fetch_collection_report(self,salesman_names,start_date,end_date):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        team_totals = defaultdict(lambda: defaultdict(lambda: {"TotalCollection": 0, "IndividualSales": {}}))
        
        current_date = start_date
        while current_date <= end_date:
            query = report_queries.collection_report_by_date_range(current_date, salesman_names)
            cursor.execute(query)
            data = cursor.fetchall()

            for row in data:
                team_name, sales_person, total_collection = row
                receipt_date = current_date.strftime('%Y-%m-%d')
                
                team_totals[team_name][receipt_date]["TotalCollection"] += total_collection
                team_totals[team_name][receipt_date]["IndividualSales"][sales_person] = total_collection
                
            current_date += timedelta(days=1)
        
        cursor.close()
        conn.close()
        return team_totals

    def process_team_totals(self,team_totals):
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
        return result

    @drf_schema(serializer_name="DateSerializer")
    def post(self,request):
        try:
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            start_date_str = request.data.get("start_date")
            end_date_str = request.data.get("end_date")
            
            if not start_date_str or not end_date_str:
                return Response({"error": "Please provide both start_date and end_date."}, status=400)
            
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
            
            team_totals = self.fetch_collection_report( salesman_names,start_date,end_date)
                
            result = self.process_team_totals(team_totals)
            
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, result, HTTP_200_OK)
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class CustomerWiseOutstanding(APIView):
    REPORT_NAME = 'Customer Wise Outstanding Report'
    permission_classes = [IsAuthenticated, HasReportPermission]
    def process_customer_wise_outstanding(self,data):
        # formatted_data,total_outstanding_sum = self.process_customer_wise_outstanding(data)
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

        return total_outstanding_sum,formatted_data
    
    def fetch_customer_wise_outstanding(self,outstanding_value, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.customer_wise_outstanding_query(outstanding_value, salesman_names)
        cursor.execute(sql_query)

        # Fetch data
        data = cursor.fetchall()
         # Close cursor and connection
        cursor.close()
        conn.close()
        return data

    @drf_schema(serializer_name="CustomerWiseOutstandingSerializer",
            serializer_fields={
                "team_name": serializers.CharField(),
                "salesman": serializers.CharField(),
                "outstanding_value": serializers.IntegerField()
            })
    def post(self,request):
        try:
            team_name = request.data.get("team_name")
            salesman = request.data.get("salesman")
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user, team_name, salesman)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            outstanding_value = request.data.get("outstanding")
            outstanding_days = [0, 25, 45, 90]
            if outstanding_value not in outstanding_days:
                return Response({"error": "Please provide valid outstanding day value"}, status=400)
            data = self.fetch_customer_wise_outstanding(outstanding_value, salesman_names)
            total_outstanding_sum,formatted_data = self.process_customer_wise_outstanding(data)

            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            # Return response with fetched data and total outstanding sum
            return response(SUCCESS, {f"Customer wise {outstanding_value} Days O/S":formatted_data,"total_outstanding_sum": total_outstanding_sum}, HTTP_200_OK)
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class CrUtilization(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "CR Utilization Report"
    @drf_schema(serializer_name="CRUtilizationReportSerializer",
            serializer_fields={
                "team_name": serializers.CharField(),
                "salesman": serializers.CharField()
            })
    def post(self,request):
        try:
            team_name = request.data.get("team_name")
            salesman = request.data.get("salesman")
            user = request.user
            
            try:
                salesman_names = report_services.get_salesmans_for_user(user, team_name, salesman)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            conn = report_services.create_sql_server_connection()
            cursor = conn.cursor()
            sql_query = report_queries.cr_utilization_report_query(salesman_names)
            cursor.execute(sql_query)
        
            # Fetch data
            results = cursor.fetchall()
            
            # Initialize a nested dictionary to hold the grouped data
            data = [dict(zip([column[0] for column in cursor.description], row)) for row in results]
            
            # Closing the cursor and connection
            cursor.close()
            conn.close()
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, data, HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class SalesmanAndProductWise(APIView):
    REPORT_NAME = "Salesman and Product Wise Report"
    permission_classes = [IsAuthenticated, HasReportPermission]
    def fetch_salesman_and_product_wise_report(self, user, salesman_names, month, year):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.salesman_and_product_wise_query(user, salesman_names, month, year)
        cursor.execute(sql_query)
        # Fetching all the rows
        rows = cursor.fetchall()
        # Closing the cursor and connection
        cursor.close()
        conn.close()
        return rows
    
    def process_salesman_and_product_wise_report(self,rows):
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
        return formatted_data
    
    @drf_schema(serializer_name="SalesmanProductWiseReportSerializer",
        serializer_fields={
            "team_name": serializers.CharField(),
            "salesman": serializers.CharField(),
            "year":serializers.CharField(),
            "month":serializers.CharField()
        })
    def post(self,request):
        try:
            team_name = request.data.get("team_name")
            salesman = request.data.get("salesman")
            year = request.data.get("year")
            month = request.data.get("month")
            if not year or not month:
                return Response({"error": "Please provide both year and month."}, status=400)
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user, team_name, salesman)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            rows = self.fetch_salesman_and_product_wise_report(user, salesman_names, month, year)
            formatted_data = self.process_salesman_and_product_wise_report(rows)
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, formatted_data, HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class TargetAndAchieved(APIView):
    REPORT_NAME = 'Target and Achieved Report'
    permission_classes = [IsAuthenticated, HasReportPermission]

    def fetch_target_and_achieved_report(self,year,month,pre_date,salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.target_and_achieved_query(month, year, pre_date, salesman_names)
        # Assuming you execute the query with the provided start_date and end_date values
        cursor.execute(sql_query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results
    
    def process_target_and_achieved_report(self,results):
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
            if row[2] == 0 and row[3] == 0 and row[5] ==0:
                continue
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
            
        return team_sales_summary_list

    @drf_schema(serializer_name="TargetAndAchievedReportSerializer",
                serializer_fields={
                    "team_name": serializers.CharField(),
                    "month": serializers.CharField(),
                    "year": serializers.CharField()
                })
    def post(self,request):
        try:
            team_name = request.data.get("team_name")
            user =  request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user, team_name)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            month = request.data.get("month", None)
            year = request.data.get("year", None)
            if not month or not year:
                return Response({"error": "Please provide both month and year."}, status=400)
            pre_date = report_services.get_previous_date(str(datetime.today().date()), month)
            results = self.fetch_target_and_achieved_report(month,year,pre_date,salesman_names)

            team_sales_summary_list = self.process_target_and_achieved_report(results)
        

            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, team_sales_summary_list, HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class WeldingElectrode(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "Welding Electrode Product Sales Report"

    def fetch_welding_electrode_product_sales(self,start_date, end_date, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.welding_electrode_product_sales_query(start_date, end_date, salesman_names)
        cursor.execute(sql_query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results

    def process_welding_electrode_product_sales(self, results, month_count = 1):
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
            sales_quantity = row[3] if row[3] is not None else 0
            if target_qty ==0 and sales_quantity ==0:
                continue

            sales_summary = {
                'sales_person': sales_person,
                'target_qty': target_qty * month_count,
                'sales_quantity': sales_quantity,
                'achieved%': (sales_quantity / (target_qty * month_count) * 100) if target_qty != 0 else 0,
            }

            team_sales_summary[team_name]['team_target_qty'] += target_qty * month_count
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
        return response_data
    
    @drf_schema(serializer_name="DateSerializer")
    def post(self,request):
        try:
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            start_date = request.data.get("start_date", None)
            end_date = request.data.get("end_date", None)
            if not start_date or not end_date:
                return Response({"error": "Please provide both start_date and end_date."}, status=400)
            
            month_count  = report_services.count_months(start_date, end_date)
            results = self.fetch_welding_electrode_product_sales(start_date, end_date, salesman_names)
            response_data = self.process_welding_electrode_product_sales(results, month_count)

            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, response_data, HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class DurastrongTMTProductSales(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "Durastrong TMT Product Sales Report"
    def fetch_durastrong_tmt_product_sales(self,start_date, end_date, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.durastrong_tmt_product_sales_query(start_date, end_date, salesman_names)
        cursor.execute(sql_query)
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results

    def process_durastrong_tmt_product_sales(self,results, month_count = 1):
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
            if target_qty == 0 and sales_quantity ==0:
                continue

            sales_summary = {
                'sales_person': sales_person,
                'target_qty': target_qty * month_count,
                'sales_quantity': sales_quantity,
                'achieved%': (sales_quantity / (target_qty * month_count) * 100) if target_qty != 0 else 0
            }

            team_sales_summary[team_name]['team_target_qty'] += target_qty * month_count
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
        return response_data
    
    @drf_schema(serializer_name="DateSerializer")
    def post(self,request):
        try:
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            start_date = request.data.get("start_date", None)
            end_date = request.data.get("end_date", None)
            if not start_date or not end_date:
                return Response({"error": "Please provide both start_date and end_date."}, status=400)
            
            month_count  = report_services.count_months(start_date, end_date)
            results = self.fetch_durastrong_tmt_product_sales(start_date, end_date, salesman_names)

            response_data = self.process_durastrong_tmt_product_sales(results, month_count)
            
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, response_data, HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

# Response is very huge not able to compare
class SalesRegister(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "Sales Register Report"

    def fetch_and_process_sales_register_report(self,start_date,end_date, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        sql_query = report_queries.sales_register_query(start_date, end_date, salesman_names)
        # Assuming you execute the query with the provided start_date and end_date values
        cursor.execute(sql_query)
        results = cursor.fetchall()
        data = [dict(zip([column[0] for column in cursor.description], row)) for row in results]
        cursor.close()
        conn.close()
        return data
    
    @drf_schema(serializer_name="SalesRegisterReportSerializer",
                serializer_fields={
                    "team_name": serializers.CharField(),
                    "start_date": serializers.DateField(input_formats=['%Y-%m-%d']),
                    "end_date": serializers.DateField(input_formats=['%Y-%m-%d'])
                })
    def post(self,request):
        try:
            user = request.user
            team_name = request.data.get("team_name")
            try:
                salesman_names = report_services.get_salesmans_for_user(user, team_name)
            except Exception as e:
                return Response({"error": str(e)}, status=400)
            start_date = request.data.get("start_date", None)
            end_date = request.data.get("end_date", None)
            if not start_date or not end_date:
                return Response({"error": "Please provide both start_date and end_date."}, status=400)
            
            # Both fetch and process the data
            data = self.fetch_and_process_sales_register_report(start_date,end_date, salesman_names)
            
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, data, HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

# Response is very huge not able to compare
class BlockCustomersList(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "Block Customers List Report"
    def fetch_and_process_block_customers_list_report(self, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        # Assuming you execute the query with the provided start_date and end_date values
        sql_query = report_queries.block_customers_list_query(salesman_names)
        cursor.execute(sql_query)
        results = cursor.fetchall()
        data = [dict(zip([column[0] for column in cursor.description], row)) for row in results]
        cursor.close()
        conn.close()
        return data
    @extend_schema()
    def post(self,request):
        try:
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user)
            except Exception as e:
                return Response({"error": str(e)}, status=400)
            data = self.fetch_and_process_block_customers_list_report(salesman_names)
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, data, HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class AllCustomersSales(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "All Customers Month on Month Report"
    def fetch_all_customers_mom_report(self,date_ranges, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        # list to hold the aggregated data
        result = []

        for _, item in enumerate(date_ranges):
            # Assuming you execute the query with the provided start_date and end_date values
            sql_query = report_queries.all_customers_sales_query(item['start_date'], item['end_date'], salesman_names)
            cursor.execute(sql_query)
            results = cursor.fetchall()
            month = item['month']
            
            # Process the results
            for row in results:
                sales_person = row[1]
                customer_name = row[0]
                achv_qty = row[3]
                
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
        return result
    @drf_schema(serializer_name="AllCustomerMomReportSerializer",
                serializer_fields={
                    "team_name": serializers.CharField(),
                    "salesman": serializers.CharField(),
                    "month_count": serializers.IntegerField()
                })
    def post(self,request):
        try:
            team_name = request.data.get("team_name")
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user, team_name)
            except Exception as e:
                return Response({"error": str(e)}, status=400)
            
            month_count = request.data.get("month_count", None)
            if not month_count:
                return Response({"error": "Please provide both Month count."}, status=400)
            date_ranges = report_services.get_monthly_date_ranges(month_count)

            result = self.fetch_all_customers_mom_report(date_ranges, salesman_names)

            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, result, HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class ProductWiseMonthSales(APIView):
    REPORT_NAME = "Product Wise Month On Month Report"
    permission_classes = [IsAuthenticated, HasReportPermission]

    def process_product_wise_month_report(self,intermediate_result):
        final_result = []
        for item_category, months_data in intermediate_result.items():
            month_list = [{month: value} for month, value in months_data.items()]
            final_result.append({
                "item_category": item_category,
                "month_data": month_list
            })
        return final_result
    
    def fetch_product_wise_month_report(self,salesman_names,month_count):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        if not month_count:
            return Response({"error": "Please provide both start_date and end_date."}, status=400)
        date_ranges = report_services.get_monthly_date_ranges(month_count)
        intermediate_result = {}

        for _, item in enumerate(date_ranges):
            # Assuming you execute the query with the provided start_date and end_date values
            sql_query = report_queries.product_wise_month_on_month_query(item['start_date'], item['end_date'], salesman_names)
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
        return intermediate_result
    @drf_schema(serializer_name="ProductWiseMonthOnMonthReportSerializer",
                serializer_fields={
                    "team_name": serializers.CharField(),
                    "salesman": serializers.CharField(),
                    "month_count": serializers.IntegerField()
                })
    def post(self,request):
        try:
            user = request.user
            team_name = request.data.get("team_name")
            try:
                salesman_names = report_services.get_salesmans_for_user(user, team_name)
            except Exception as e:
                return Response({"error": str(e)}, status=400)
            month_count = request.data.get("month_count", None)
            intermediate_result = self.fetch_product_wise_month_report(salesman_names,month_count)

            final_result = self.process_product_wise_month_report(intermediate_result)
            
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, final_result, HTTP_200_OK)
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class ReviewProductWise(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "Review Product Wise Report"
    def fetch_review_product_wise_report(self,month_count, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()        
        sql_query = report_queries.review_product_wise_query(month_count, salesman_names)
        cursor.execute(sql_query)
        results = cursor.fetchall()

        return results
    def process_review_product_wise_report(self,results, month_count):
        data = defaultdict(lambda: defaultdict(lambda: {"Target Qty": 0, "Months": defaultdict(float)}))
        # Process the results
        last_n_months = report_services.get_last_n_months_names(month_count)
        for row in results:
            team_name, product_cluster, target_qty, achv_qty, year, month = row
            if achv_qty is None:
                achv_qty = 0.0
            # if month is None:
            #     month = "No Month"
            data[team_name][product_cluster]["Target Qty"] = float(target_qty)
            data[team_name][product_cluster]["Months"][month] = float(achv_qty)
        # Convert the data to the desired format
        result = []
        for team, products in data.items():
            team_products = {}
            for product, product_data in products.items():
                product_dict = {
                "Target Qty": product_data["Target Qty"],
                "Months":  {month: product_data["Months"].get(month, 0.0) for month in last_n_months}
                }
                product_dict["Months"].pop("", None)
                team_products[product] = product_dict
            result.append({team: team_products})
        return result
    @drf_schema(serializer_name="ReviewProductWiseReportSerializer",
                serializer_fields={
                    "team_name": serializers.CharField(),
                    "salesman_names": serializers.CharField(),
                    "month_count": serializers.IntegerField()
                })
    def post(self,request):
        try:
            team_name = request.data.get("team_name")
            salesman = request.data.get("salesman")
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user,team_name, salesman)
            except Exception as e:
                return Response({"error": str(e)}, status=400)
            
            month_count = request.data.get("month_count", None)
            
            if not month_count:
                return Response({"error": "Please provide both start_date and end_date."}, status=400)

            data = self.fetch_review_product_wise_report(month_count, salesman_names)
            result = self.process_review_product_wise_report(data, month_count)
            
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, result, HTTP_200_OK)
        
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class TargetCustomerSales(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "Target Customer Sales Report"

    def fetch_and_process_target_customer_sales(self,month_count, salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        date_ranges = report_services.get_monthly_date_ranges(month_count)

        # Dictionary to hold the aggregated data
        aggregated_result = {}

        for _, item in enumerate(date_ranges):
            # Assuming you execute the query with the provided start_date and end_date values
            sql_query = report_queries.target_customers_sales_query(item['start_date'], item['end_date'], salesman_names)
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
        return aggregated_result
    @drf_schema(serializer_name="TargetCustomerSalesReportSerializer",
                serializer_fields={
                    "team_name": serializers.CharField(),
                    "salesman": serializers.CharField(),
                    "month_count": serializers.IntegerField()
                })    
    def post(self,request):
        try:
            team_name = request.data.get("team_name")
            salesman = request.data.get("salesman")
            user = request.user
            try:
                salesman_names = report_services.get_salesmans_for_user(user, team_name, salesman)
            except Exception as e:
                return Response({"error": str(e)}, status=400)
            
            month_count = request.data.get("month_count", None)
            if not month_count:
                return Response({"error": "Please provide month_count"}, status=400)

            aggregated_result  = self.fetch_and_process_target_customer_sales(month_count, salesman_names)
            # Convert aggregated result to the desired format
            final_result = list(aggregated_result.values())
            report_services.create_log(user=request.user,report_name=self.REPORT_NAME)
            return response(SUCCESS, final_result, HTTP_200_OK)
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class ReviewSalesmanWise(APIView):
    REPORT_NAME = "Review SalesMan Wise Report"
    permission_classes = [IsAuthenticated, HasReportPermission]
    def fetch_review_salesman_wise_data(self,month_count,salesman_names):
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        # Assuming you execute the query with the provided start_date and end_date values
        sql_query1 = report_queries.review_salesman_wise_query1(salesman_names)
        cursor.execute(sql_query1)
        results1 = cursor.fetchall()
        query1_data = [dict(zip([column[0] for column in cursor.description], row)) for row in results1]
        
        # Second Query Execution based on month_count
        
        date_ranges = report_services.get_monthly_date_ranges(month_count)
        query2_data = defaultdict(list)

        for item in date_ranges:
                sql_query2 = report_queries.review_salesman_wise_query2(item['start_date'], item['end_date'], salesman_names)
                cursor.execute(sql_query2)
                results2 = cursor.fetchall()
                data2 = [dict(zip([column[0] for column in cursor.description], row)) for row in results2]
                month = item['month']
                query2_data[month].extend(data2)

        return query1_data,query2_data

    def process_review_salesman_wise_data(self,query1_data, query2_data):
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
        return combined_data
    @drf_schema(serializer_name="ReviewSalesmanWiseDataSerializer",
                serializer_fields={
                    "team_name": serializers.CharField(),
                    "salesman": serializers.CharField(),
                    "month_count": serializers.IntegerField()
                })
    def post(self,request):
        try:
            user = request.user
            team_name = request.data.get("team_name")
            salesman = request.data.get("salesman")
            try:
                salesman_names = report_services.get_salesmans_for_user(user, team_name, salesman)
            except Exception as e:
                return Response({"error": str(e)}, status=400)

            month_count = request.data.get("month_count", None)
            if not month_count:
                return Response({"error": "Please provide month_count."}, status=HTTP_400_BAD_REQUEST)
            
            query1_data, query2_data = self.fetch_review_salesman_wise_data(month_count,salesman_names)

            combined_data = self.process_review_salesman_wise_data(query1_data, query2_data)
        
            # Log the report creation
            report_services.create_log(user=request.user, report_name=self.REPORT_NAME)
            return response(SUCCESS, combined_data, HTTP_200_OK)
        except Exception as e:
            logger.exception(f"an error occured while viewing the Report-{self.REPORT_NAME}: {e}")
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)

class SalesmanKpiDashboard(APIView):
    REPORT_NAME = ""
    permission_classes = [IsAuthenticated]
    @extend_schema()
    def post(self,request):
        user = request.user
        # Fetch the queries for main data and customer data
        main_query, customers_query = dashboard_queries.kpi_dashboard_queries(user)

        # Create a connection to the SQL Server
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()

        # Execute the main query
        cursor.execute(main_query)
        main_results = cursor.fetchall()
        main_data = [dict(zip([column[0] for column in cursor.description], row)) for row in main_results]

        # Execute the customers query
        cursor.execute(customers_query)
        customers_results = cursor.fetchall()

        # Initialize customers_data
        customers_data = {"Target": 0, "Non Target": 0}
        if customers_results:
            for row in customers_results:
                row_data = dict(zip([column[0] for column in cursor.description], row))
                if row_data.get("Customer Type") == "Target":
                    customers_data["Target"] = row_data.get("NewCustomersCreated", 0)
                elif row_data.get("Customer Type") == "Non Target":
                    customers_data["Non Target"] = row_data.get("NewCustomersCreated", 0)

        # Merge customer data into each main data dictionary
        for item in main_data:
            item.update(customers_data)
        
        max_date = find_max_date()
        if main_data and main_data[0]:
            main_data[0]["refresh_date"] = max_date

        # Prepare the final response data
        
        return Response(main_data)

class IncentiveReport(APIView):
    permission_classes = [IsAuthenticated, HasReportPermission]
    REPORT_NAME = "Incentive Report"
    @extend_schema()
    def post(self, request):
        try:
            month, year = report_services.get_previous_month_and_year()            
            salesman = request.user.full_name

            main_data, results, critera_result = self.fetch_product_wise_incentive_amount(month, year, salesman)
            if not len(main_data) != 0:
                return Response([], status=HTTP_200_OK)
            response_data = self.process_product_wise_incentive_amount(main_data, results, critera_result)
            report_services.create_log(user=request.user, report_name=self.REPORT_NAME)
            return Response(response_data, status=HTTP_200_OK)
        
        except Exception as e:
            return response(ERROR, {ERROR: f"error occured while viewing the report: {e}"},HTTP_400_BAD_REQUEST)
        
    def fetch_product_wise_incentive_amount(self,month,year,salesman):
        incentive_report_obj = report_queries.InsentiveQueries(month, year, salesman)
        conn = report_services.create_sql_server_connection()
        cursor = conn.cursor()
        criteria_query = incentive_report_obj.elegibilty_criteria()
        cursor.execute(criteria_query)
        criteria_results = cursor.fetchall()
        main_data = []
        transformed_data = []
        if len(criteria_results) != 0:
            sql_query = incentive_report_obj.incentive_amount_query()
            cursor.execute(sql_query)
            main_results = cursor.fetchall()
            main_data = [dict(zip([column[0] for column in cursor.description], row)) for row in main_results]

            # SQL command to fetch data from the table
            items = ProductGroup.objects.all()

            # Initialize a dictionary to hold the grouped data
            grouped_data = defaultdict(lambda: {'cost': 0, 'item_details': []})

            # Group item details by item group, including cost at the group level
            for item in items:
                grouped_data[item.item_group]['cost'] = item.cost  # Assuming cost is the same for the entire group
                grouped_data[item.item_group]['item_details'].append(item.item_details)
            
            transformed_data = dict(grouped_data)
        return main_data, transformed_data, criteria_results
    
    def process_product_wise_incentive_amount(self, main_data, results, criteria_result):

        group_achv_qty = defaultdict(float)
        for entry in main_data:

            product_detail = entry["Product Details"]
            achv_qty = float(entry["Achv Qty"])
            
            for product_cluster_key, product_cluster_value in results.items():
                if product_detail in product_cluster_value["item_details"]:
                    group_achv_qty[product_cluster_key] += achv_qty

        response_data = []

        for key,value in results.items():
            data = group_achv_qty.get(key)
            cost = value.get("cost")
            incentive_amount = 0
            if data:
                incentive_amount = cost * data
                data = {"group_name": key, "achv_qty": data, "incentive_amount": incentive_amount}
                response_data.append(data)
        target_info = criteria_result[0]
        target_details = {"final_details": { "target_qty": target_info[2], "achvd_qty": target_info[3], "achvd_percent": target_info[4] }}
        response_data.append(target_details)
        return response_data

# ================================== Not including ================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
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
