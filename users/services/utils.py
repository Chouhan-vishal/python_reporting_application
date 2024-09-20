import random
from django.conf import settings
from django.core.mail import send_mail
from rest_framework import serializers
from users.models import UserActivityLog
from django.utils.html import strip_tags
from rest_framework.response import Response
from reports.services import report_services
from drf_spectacular.types import OpenApiTypes
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter

    
def drf_schema(serializer_name=None, serializer_fields=None):
    if serializer_name=="DateSerializer":
        serializer_fields={
                "start_date": serializers.DateField(input_formats=['%Y-%m-%d']),
                "end_date": serializers.DateField(input_formats=['%Y-%m-%d']),
            }
    return extend_schema(
        request=inline_serializer(
            name=serializer_name,
            fields=serializer_fields
        ),
        responses={
            HTTP_200_OK: {},
            HTTP_400_BAD_REQUEST: {}
        },
        parameters=[
            OpenApiParameter(
                name='Authorization',
                location=OpenApiParameter.HEADER,
                description='Authorization Bearer token',
                required=True,
                type=OpenApiTypes.STR
            ),
        ]
    )
# Send email with the html template
def send_email(context,to_email,template_name,subject):
    html_message = render_to_string(template_name, context)
    text_message = strip_tags(html_message)    
    email = EmailMultiAlternatives(subject, text_message, to=[to_email])
    email.attach_alternative(html_message, 'text/html')
    email.send()

def response(status, data, status_code, refresh_date=''):
    response_data = {
        'status': status,
        'data': data,
    }
    if refresh_date:
        response_data['refresh_date'] = refresh_date    
    return Response(response_data, status=status_code)


def generate_otp():
    return str(random.randint(100000, 999999))

#send opt via email without the html template
def send_otp_email(email, otp):
    subject = 'Password Reset OTP'
    message = f'Your OTP for password reset is: {otp}'
    send_mail(subject, message, settings.EMAIL_HOST_USER, [email])

def create_log(admin_user, user_name, action, sub_action = ""):
    logs = f'{action.title()} user {sub_action} {user_name}'.replace("  ", " ") 
    activity_log = UserActivityLog.objects.create(user=admin_user, action_type= action, object = "User", log=logs)
    activity_log.save()

def verify_user_existance(role, emp_code):
    conn = report_services.create_sql_server_connection()
    cursor = conn.cursor()
    if role == 'manager':
        query = f"select * from tbl_HierarchyMapping where [Reporting Manager EMP ID] = '{emp_code}'"
    elif role == "salesman":
        query = f"select * from tbl_HierarchyMapping where [EMP ID] = '{emp_code}'"
    elif role == "admin":
        return True # by pass emp_code if we creating admin User
    else:
        raise Exception("Role does not exist")
    cursor.execute(query)
    results = cursor.fetchall()
    if not len(results) > 0:
        raise Exception(f"User '{emp_code}' does not exist with '{role}' role")
    cursor.close()
    conn.close()
