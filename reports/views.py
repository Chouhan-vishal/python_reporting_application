from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from reports.services import report_services
# from services.report_services import report_services
# Create your views here.

@api_view(['GET'])
def health(request):
    return Response({"status": "OK"}, status=HTTP_200_OK)

@api_view(['GET'])
def report_data(request):
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    request_body = request.data
    table_name = request_body.get("table", None)
    if table_name:
        query = f"SELECT * FROM {table_name}"
        cursor.execute(query)
        columns = [column[0] for column in cursor.description]

        # Fetch the results
        results = []
        for row in cursor.fetchall():
            row_dict = dict(zip(columns, row))
            results.append(row_dict)

        # Return response containing retrieved data
        response_data = {table_name: results}
    else:
        response_data = {'status': "failure", "message":"Please pass table name"}
    return Response(response_data)