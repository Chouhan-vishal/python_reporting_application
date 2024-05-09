from rest_framework.response import Response
from django.core.mail import send_mail
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import random


# Send email with the html template
def send_email(context,to_email,template_name,subject):
    html_message = render_to_string(template_name, context)
    text_message = strip_tags(html_message)
    
    email = EmailMultiAlternatives(subject, text_message, to=[to_email])
    email.attach_alternative(html_message, 'text/html')
    email.send()
    
    
# def send_otp_email(email, otp):
#     subject = 'Password Reset OTP'
#     to_email = email
#     context = {'otp':otp}
#     template_name = "email_otp_template.html"
#     send_email(context=context, to_email=to_email,template_name=template_name,subject=subject)
    
  
def response(status, data, status_code):
    return Response({
        'status': status,
        'data': data
    }, status=status_code) 
    
    

def generate_otp():
    return str(random.randint(100000, 999999))


#send opt via email without the html template
def send_otp_email(email, otp):
    subject = 'Password Reset OTP'
    message = f'Your OTP for password reset is: {otp}'
    send_mail(subject, message, settings.EMAIL_HOST_USER, [email])