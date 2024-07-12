from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate
from .services.auth_token import AuthTokenService
from rest_framework_simplejwt.tokens import Token, RefreshToken, AccessToken
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from .services.utils import response
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from dotenv import load_dotenv
from reporting_application.constants import *
from .services.utils import generate_otp, send_otp_email, create_log
from datetime import datetime, timedelta
from django.utils.timezone import now as aware_utcnow
from django.db.models import Q, Count
from reports.services import report_services, report_queries
from .services.utils import *
from rest_framework.views import APIView
from rest_framework import status
import pyotp
from .serializers import UserSerializer, UserActivityLogSerializer, LoginSerializer, TwoFactorAuthenticationSerializer,UserSearchSerializer
from .models import (
    User,
    OTP,
    TwoFactorAuthentication,
    ReportPermission,
    UserActivityLog,
    Hierarchy
)
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, inline_serializer, OpenApiTypes, extend_schema_serializer
from drf_spectacular.types import OpenApiTypes
from drf_spectacular import openapi
from django.db.models import Count, Value, TextField
from django.db.models.functions import Replace

import logging
from reporting_application.utils import *

logger = logging.getLogger('users')


class TwoFactorAuthenticationView(APIView):
    @extend_schema(
    request=TwoFactorAuthenticationSerializer,
    responses={
        HTTP_200_OK: {},
        HTTP_400_BAD_REQUEST: {}
    }
    )
    def post(self, request):
        """
        Authenticate user using two-factor authentication.

        Args:
            request (HttpRequest): Request object containing user credentials and OTP.

        Returns:
            Response: Response object containing access token or error message.
        """


        try:
            otp = request.data.get('otp')
            secret_key = request.data.get('secret_key', None)
            email = request.data.get('email')
            password = request.data.get('password')
            user = authenticate(email=email, password=password)
            user_mfa = TwoFactorAuthentication.objects.filter(user=user).first()
            if secret_key:
                user_mfa.is_enabled = True
                user_mfa.secret_key = secret_key
                user_mfa.save()
            user_secret_key = user_mfa.secret_key
            is_otp_valid = pyotp.TOTP(user_secret_key).verify(otp)
            if is_otp_valid:
                token = AuthTokenService.get_token_for_user(user)
                logger.info(f"Access token generated successfully for user with id {user.id}")
                return response(SUCCESS, token, HTTP_200_OK)
            else:
                logger.error(f"Invalid OTP for user with id {user.id}")
                return response(FAILED, {ERROR: "Invalid OTP provided"} ,HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error during user authentication: {str(e)}')                         
            return response(FAILED, {ERROR: f'Error during user authentication: {str(e)}'}, HTTP_400_BAD_REQUEST)     

                   


class Login(APIView):
    
    @extend_schema(
    request=inline_serializer(
        name="LoginSerializer",
        fields={
            "email": serializers.CharField(required=True),
            "password": serializers.CharField(required=True)
        }
        ),
    responses={
        HTTP_200_OK: {},
        HTTP_400_BAD_REQUEST: {}
    }   
    )
    def post(self, request):
        """
        Authenticate a user using email and password.

        Args:
            request (HttpRequest): The request object containing email and password.

        Returns:
            Response: Returns authentication tokens if credentials are valid. 
                      If the user is not an admin, returns a token for authentication 
                      and if the user is admin then follows two factor authentication
                      If the credentials are invalid or an error occurs, returns an error message.
        """

        try:
            email = request.data.get('email')
            try:
                user = User.objects.get(email=email)
                if not user.is_active:
                    return response(FAILED, {MESSAGE: "This user is deactivated. Please contact with your administrator"}, HTTP_400_BAD_REQUEST)
            except User.DoesNotExist:
                return response(FAILED, {MESSAGE: "User does not exist"}, HTTP_400_BAD_REQUEST)

            password = request.data.get('password')
            if not (email and password):
                raise Exception(f"email and password are required") 
            user = authenticate(email=email, password=password)
            if user is None:
                return response(FAILED, {MESSAGE: "Invalid credentials"}, HTTP_400_BAD_REQUEST)
            if not user.is_admin:
                token = AuthTokenService.get_token_for_user(user)
                logger.info(f'User with id {user.id} logged in  successfully')
                return response(SUCCESS, token, HTTP_200_OK)
            else:
                mfa = TwoFactorAuthentication.objects.filter(user=user).first()
                mfa_enabled = mfa.is_enabled
                logger.info(f'User with "email": {email} authenticated successfully')
                return response(SUCCESS, {"is_valid": True, "mfa_enabled": mfa_enabled} ,HTTP_200_OK)   
        except User.DoesNotExist:
            logger.error(f'User with id {user.id} does not exist')
            return response(FAILED, {ERROR: 'User does not exist'}, HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Error during OTP verification: {str(e)}')
            return response(FAILED, {ERROR: f'Error during OTP verification: {str(e)}'}, HTTP_400_BAD_REQUEST)



class Logout(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request):
        """
        Logout a user.

        Args:
            request (HttpRequest): Request object.

        Returns:
            Response: Returns {MESSAGE: "Logged out successfully"} upon successful logout.
        """
        try:
            access_token = request.headers.get('Authorization').split(' ')[1]
            if access_token is None:
                return response(FAILED, {MESSAGE: "Refresh token is missing"}, HTTP_400_BAD_REQUEST)
            token_obj = AccessToken(access_token)
            token_obj.set_exp(from_time=datetime.now(), lifetime=timedelta(seconds=1))
            return response(SUCCESS, {MESSAGE: "Logged out successfully"}, HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error during user logout: {str(e)}')
            return response(FAILED, {ERROR: f'Error during user logout: {str(e)}'}, HTTP_400_BAD_REQUEST)


class Users(APIView):
    permission_classes = [IsAdminUser, IsAuthenticated]
    @extend_schema(
    request=UserSerializer,  
    responses={HTTP_200_OK: UserSerializer(many=False)},
    description="Get user details or update user details.",
    parameters=[
        OpenApiParameter(
                name='Authorization',
                location= OpenApiParameter.HEADER,
                description='Authorization Bearer token',
                required=True,
                type=OpenApiTypes.STR
            ),
    ]
    )
    def get(self, request, pk=None):
        """
        Get user details.

        Args:
            request (HttpRequest): Request object.
            pk (int, optional): Primary key of the user to get. Defaults to None.
        Returns:
            Response: Returns user details if GET method is used. 
            If pk is none then all users are returned.
        """
        if pk:
            try:
                user = User.objects.get(id=pk)
                serializer = UserSerializer(user)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except User.DoesNotExist:
                logger.error(f'User with id {pk} does not exist')
                return Response({ERROR: 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f'Error during user detail retrieval: {str(e)}')
                return Response({ERROR: 'Error during user detail retrieval'}, status=status.HTTP_400_BAD_REQUEST)
        else:
            try:
                users = User.objects.filter(is_admin = False)
                serializer = UserSerializer(users, many=True)
                return Response(serializer.data, status=status.HTTP_200_OK)
            except Exception as e:
                logger.error(f'Error during user list retrieval: {str(e)}')
                return Response({ERROR: 'Error during user list retrieval'}, status=status.HTTP_400_BAD_REQUEST)
    @extend_schema(
    request=UserSerializer,  
    responses={HTTP_200_OK: UserSerializer},
    description="update the user details and return user instance",
    parameters=[
        OpenApiParameter(
                name='Authorization',
                location= OpenApiParameter.HEADER,
                description='Authorization Bearer token',
                required=True,
                type=OpenApiTypes.STR
            ),
    ]
    )
    def patch(self, request, pk=None):
        """
        Update user details.

        Args:
            request (HttpRequest): Request object.
            pk (int): Primary key of the user to update.
        Returns:
            Response: Returns user details if PATCH method is used.
        """
        try:
            user = User.objects.get(id=pk)
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                try:
                    create_log(request.user, user.full_name, "updated")
                except:
                    logger.error(f'Error in creating log for User updation')
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            logger.error(f'User with id {pk} does not exist')
            return Response({'error': 'User does not exist'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Error during user update: {str(e)}')
            return Response({ERROR: f'Error during user update: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
    @extend_schema(
    request=UserSerializer,  
    responses={HTTP_201_CREATED: UserSerializer},
    description="Create a new user",
    parameters=[
        OpenApiParameter(
                name='Authorization',
                location= OpenApiParameter.HEADER,
                description='Authorization Bearer token',
                required=True,
                type=OpenApiTypes.STR
            ),
    ]
    )
    @extend_schema_serializer(
        many=True,
        exclude_fields=["hierarchy"]
    )
    def post(self, request):
        """
        Creates a new user.

        Args:
            request (HttpRequest): The request object which contains user data.

        Returns:
            Response: The response object which contains the created user instanse.
        """
        try:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                try:
                    create_log(request.user, user.full_name, "created")
                except:
                    logger.error(f'Error in creating log for User creation')
                return response(SUCCESS, serializer.data, HTTP_201_CREATED)
            logger.debug(f'User creation failed: {serializer.errors}')
            raise ValidationError(f'User creation failed: {str(serializer.errors)}')
        except ValidationError as e:
            logger.error(f'Validation Error during user creation: {str(e)}')
            return response(FAILED, {ERROR: str(e)}, HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'error during user registration: {str(e)}')
            return response(FAILED, {ERROR: f'error during user registration: {str(e)}'}, HTTP_400_BAD_REQUEST)


class Profile(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
    request=UserSerializer,  
    responses={HTTP_200_OK: UserSerializer},
    description="Retrive user profile details",
    parameters=[
        OpenApiParameter(
                name='Authorization',
                location= OpenApiParameter.HEADER,
                description='Authorization Bearer token',
                required=True,
                type=OpenApiTypes.STR
            ),
    ]
    )
    def get(self, request):
        """
        Get user profile.

        Returns:
            Response: Returns user profile data if successful, else returns an error.
        """
        try:
            user = request.user
            serializer = UserSerializer(user)
            data = serializer.data
            report_order = [
                "sales_collection_outstanding",
                "all_customers_sales",
                "block_customers_list",
                "collection",
                "cr_utilization",
                "customer_wise_outstanding",
                "durastrong_tmt_product_sales",
                "incentive_report",
                "product_wise_month_sales",
                "product_wise_sales_summary",
                "review_product_wise",
                "review_salesman_wise",
                "sales_register",
                "sales_summary",
                "salesman_and_product_wise",
                "target_and_achieved",
                "target_customer_sales",
                "weekly_summary",
                "welding_electrode",
            ]
            if is_salesman(user):
                report_order.pop("sales_collection_outstanding")
                report_order.insert(13, "sales_collection_outstanding",)
            if not user.is_admin:
                accessible_reports_list = []
                for report in report_order:
                    if user.permitted_reports.reports_permission.get(report):
                        accessible_reports_list.append({
                            "path": f"/{report}".replace("_", "-"),
                            "title": " ".join([str(k).capitalize() for k in str(report).split("_")])
                        })
                if is_salesman(user):
                    accessible_reports_list.insert(0, {'title':"KPI Dashboard", "path":'/kpi-dashboard'})
                data['accessible_reports'] = accessible_reports_list
            logger.info(f'User with "email": {user.email} retrieved successfully')
            return response(SUCCESS, data, status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error during user detail retrieval: {str(e)}')
            return response(FAILED, {ERROR: 'Error during user detail retrieval'}, status.HTTP_400_BAD_REQUEST)
        
        
    @extend_schema(
    request=UserSerializer,  
    responses={HTTP_200_OK: UserSerializer},
    description="User can update their profile details",
    parameters=[
        OpenApiParameter(
                name='Authorization',
                location= OpenApiParameter.HEADER,
                description='Authorization Bearer token',
                required=True,
                type=OpenApiTypes.STR
            ),
    ]
    )
    def patch(self, request):
        """
        Update user profile.

        Returns:
            Response: Returns updated user profile data if successful, else returns an error.
        """
        try:
            user = request.user
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return response(SUCCESS, serializer.data, status.HTTP_200_OK)
            logger.debug(f'User update failed: {serializer.errors}')
            raise ValidationError(f'User update failed: {str(serializer.errors)}')
        except ValidationError as e:
            logger.error(f'Error during user update: {str(e)}')
            return response(FAILED, {ERROR: str(e)}, status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'Error during user update: {str(e)}')
            return response(FAILED, {ERROR: 'Error during user update'}, status.HTTP_400_BAD_REQUEST)

class ResetPasswordRequestOTP(APIView):
    @extend_schema(
    request=inline_serializer(
        name="EmailSerializer",
        fields = {
            "email": serializers.EmailField(required=True),
        }
    ),  
    responses= {HTTP_200_OK: {},
               HTTP_400_BAD_REQUEST: {}
    },
    description="Request User OTP for password reset",
    )
    def post(self, request):
        """
        Send an email with an OTP for password reset.

        Args:
            request (HttpRequest): Request object containing the user's email address.

        Returns:
            Response: Returns a success message if the email is sent successfully, else returns an error.
        """
        try:
            email = request.data.get('email')
            user = User.objects.get(email=email)
            #Generate OTP for the password reset
            otp = generate_otp()
            existing_otps = OTP.objects.filter(user=user)
            if existing_otps:
                existing_otps.delete()
            otp = OTP.objects.create(user=user, otp=otp)
            otp.save()
            # Send an email with OTP to verify the user
            send_otp_email(email, otp.otp)
            logger.info(f'OTP sent to {email}')
            return response(SUCCESS, {MESSAGE: "OTP sent to your email"}, HTTP_200_OK)
        except User.DoesNotExist:
            logger.error(f'User with email {email} does not exist')
            return response(FAILED, {ERROR: f'User with email {email} does not exist'}, HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'error during forgot password: {str(e)}')
            return response(FAILED, {ERROR: f'error during forgot password: {str(e)}'}, HTTP_400_BAD_REQUEST)



class VerifyOTP(APIView):
    @extend_schema(
        request=inline_serializer(
            name="OTPVerificationSerializer",
            fields = {
                "email": serializers.EmailField(required=True),
                "OTP": serializers.CharField(required=True),
            }
    ),  
    responses= {HTTP_200_OK: {},
               HTTP_400_BAD_REQUEST: {}
    }
    )
    def post(self, request):
        """
        Verify the OTP sent to the user's email.

        Args:
            request (HttpRequest): Request object containing the OTP and the user's email address.

        Returns:
            Response: Returns a success message if the OTP is valid, else returns an error.
        """
        try:
            otp = request.data.get('otp')
            email = request.data.get("email")
            user = User.objects.filter(email=email).first()
            if user is None:
                raise Exception(f"User with email {email} does not exist")
            otp_object = OTP.objects.filter(user=user, otp=otp).first()
            if otp_object and otp_object.is_valid():
                token = PasswordResetTokenGenerator().make_token(user)
                # OTP is valid
                otp_object.delete()
                logger.info(f'OTP verified for user {user.email}')
                return response(SUCCESS, {MESSAGE: "OTP verified successfully", "password_reset_token": token}, HTTP_200_OK)
            elif not otp_object:
                # OTP is invalid
                logger.error(f'OTP is invalid for user {user.email}')
                raise Exception("OTP is invalid")
            else:
                otp_object.delete()
                return response(FAILED, {ERROR: 'OTP Expired'}, HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            logger.error(f'error during OTP verification: {str(e)}')
            return response(FAILED, {ERROR: f'error during OTP verification: {str(e)}'}, HTTP_400_BAD_REQUEST)
    
class ResetPassword(APIView):
    @extend_schema(
    request=inline_serializer(
        name="EmailSerializer",
        fields = {
            "email": serializers.EmailField(required=True),
        }
    ),  
    responses={HTTP_200_OK: {},
            HTTP_400_BAD_REQUEST: {}
    },
    description="Password Reset API",
    )
    def post(self, request):
        """
        Reset the user's password.

        Args:
            request (HttpRequest): Request object containing email address, new password and confirm password.

        Returns:
            Response: Returns a success message if the password is reset successfully, else returns an error message.
        """

        try:
            email = request.data.get('email', None)
            if email is None:
                raise Exception("Email is required")
            user = User.objects.filter(email=email).first()
            if user is None:
                raise Exception(f"User with email {email} does not exist")
            new_password = request.data.get('password')
            confirm_password = request.data.get('confirm_password')
            try:
                admin_user = is_admin(request.user)
            except:
                admin_user = False
            token = request.data.get('token')
            if not admin_user and not PasswordResetTokenGenerator().check_token(user, token):
                return response(FAILED, {ERROR: 'Invalid or expired token'}, HTTP_400_BAD_REQUEST)

            if not new_password or not confirm_password:
                logger.error(f'New password and confirm password are required')
                return response(FAILED, {ERROR: 'New password and confirm password are required'}, HTTP_400_BAD_REQUEST)
            

            if new_password != confirm_password:
                logger.error(f'New password and confirm password do not match')
                return response(FAILED, {ERROR: 'New password and confirm password do not match'}, HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()
            if admin_user:
                create_log(request.user, user.full_name, "Updated", "password for")
            logger.info(f'Password reset for user {user.email}')
            return response(SUCCESS, {MESSAGE: "Password reset successfully"}, HTTP_200_OK)
        except Exception as e:
            logger.error(f'error during password reset: {str(e)}')
            return response(FAILED, {ERROR: f'error during password reset: {str(e)}'}, HTTP_400_BAD_REQUEST)



    
class ReportPermissions(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    @extend_schema(
        request=inline_serializer(
            name="AllowReportPermissionSerializer",
            fields = {
                "permissions": serializers.JSONField(required=True),
            }
    ),  
    responses= {HTTP_200_OK: {},
               HTTP_400_BAD_REQUEST: {}
    },
    parameters=[
        OpenApiParameter(
                name='Authorization',
                location= OpenApiParameter.HEADER,
                description='Authorization Bearer token',
                required=True,
                type=OpenApiTypes.STR
            ),
    ]
    )
    def patch(self, request, user_id):
        """
        Allow permission to the user to view the reports.

        Args:
            request (HttpRequest): User id and permissions(dictionary) to be updated.


        Returns:
            Response: Reurn a success message if the permissions are updated successfully, else returns an error message.
        """
        try:
            user = User.objects.get(id=user_id)
            permission_obj = request.data.get('permissions')
            user_permission_set = user.report_permission
            for permission_key, permission_value in permission_obj.items():
                user_permission_set.reports_permission[permission_key] = permission_value
            user_permission_set.save()
            return response(SUCCESS, {MESSAGE: "Permissions updated successfully"}, HTTP_200_OK)        
        except Exception as e:
            logger.error(f'Error during report permission update: {str(e)}')
            return response(FAILED, {ERROR: f'Error during report permission update: {str(e)}'}, HTTP_400_BAD_REQUEST)


class ReportLogs(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    @extend_schema(
    responses= {HTTP_200_OK: {},
               HTTP_400_BAD_REQUEST: {}
    },
    parameters=[
        OpenApiParameter(
                name='Authorization',
                location= OpenApiParameter.HEADER,
                description='Authorization Bearer token',
                required=True,
                type=OpenApiTypes.STR
            ),
    ]
    )
    def get(self, request):
        """
        Return User Activity Logs.

        Args:
            request (HttpRequest): None

        Returns:
            Response: Returns All the User Activity Logs from UserActivityLog model.
        """
        try:
            user_activity_logs = UserActivityLog.objects.all().order_by('-created_at')
            serializer = UserActivityLogSerializer(user_activity_logs, many=True)
            return response(SUCCESS, serializer.data, HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error during report logs retrieval: {str(e)}')
            return response(FAILED, {ERROR: f'Error during report logs retrieval: {str(e)}'}, HTTP_400_BAD_REQUEST)   


class UserSearch(APIView):
    @extend_schema(
    request=UserSearchSerializer,  
    responses={HTTP_200_OK: {},
            HTTP_400_BAD_REQUEST: {}
    },
    description="queried Users",
     parameters=[
        OpenApiParameter(
                name='Authorization',
                location= OpenApiParameter.HEADER,
                description='Authorization Bearer token',
                required=True,
                type=OpenApiTypes.STR
            ),
    ]
    )
    def post(self, request):
        try:
            serializer = UserSearchSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            query = serializer.validated_data['query']
            users = User.objects.filter(
                Q(emp_code__icontains=query) |
                Q(email__icontains=query) |
                Q(full_name__icontains=query) |
                Q(team_name__icontains=query) |
                Q(manager_name__icontains=query) |
                Q(phone_number__icontains=query)
            )
            serializer = UserSerializer(users, many=True)
            return response(SUCCESS, serializer.data, HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error during user search: {str(e)}')
            return response(FAILED, {ERROR: f'Error during user search: {str(e)}'}, HTTP_400_BAD_REQUEST)
        

class TeamNames(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={HTTP_200_OK: OpenApiTypes.OBJECT},
        description="Get a list of team names."
    )
    def post(self, request):
        """
        Get a list of team names.

        Args:
            request (HttpRequest): Request object.

        Returns:
            Response: Returns a list of team names.
        """
        try:
            user = request.user
            conn = report_services.create_sql_server_connection()
            cursor = conn.cursor()
            if is_admin(user):
                manager_name = request.data.get("manager_name", None)
            else:
                manager_name = user.full_name.lower()
            sql_query = report_queries.get_team_names(manager_name)
            cursor.execute(sql_query)
            results = cursor.fetchall()
            team_names = [row[0] for row in results]

            return response(SUCCESS, {'team_names': team_names}, HTTP_200_OK)

        except Exception as e:
            logger.error(f'Error during team names retrieval: {str(e)}')

            return response(SUCCESS, {'error': 'Error during team names retrieval'}, HTTP_400_BAD_REQUEST)



class ManagerList(APIView):

    """
    Return Manager Users.
    Args:
        request (HttpRequest): None
    Returns:
        Response: Returns All the User with hierarchy managers.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={HTTP_200_OK: OpenApiTypes.OBJECT},
        description="Get a list of manager names."
    )
    def get(self, request):
        try:
            conn = report_services.create_sql_server_connection()
            cursor = conn.cursor()
            sql_query = report_queries.manager_names_query()
            cursor.execute(sql_query)
        
            # Fetch data
            results = cursor.fetchall()
            
            # Initialize a nested dictionary to hold the grouped data
            manager_names = [row[0] for row in results]

            return response(SUCCESS, manager_names, HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error during manager names retrieval: {str(e)}')
            return response(SUCCESS, {'error': 'Error during manager names retrieval'},HTTP_400_BAD_REQUEST)
            

class SalesmanList(APIView):
    """
    Return Manager Users.
    Args:
        request (HttpRequest): None
    Returns:
        Response: Returns All the User with hierarchy managers.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={HTTP_200_OK: OpenApiTypes.OBJECT},
        description="Get a list of salesman names."
    )
    def post(self, request):
        try:
            team_name = request.data.get("team_name", None)
            conn = report_services.create_sql_server_connection()
            cursor = conn.cursor()
            sql_query = report_queries.salesman_names_query(team_name)
            cursor.execute(sql_query)
        
            # Fetch data
            results = cursor.fetchall()
            
            # Initialize a nested dictionary to hold the grouped data
            salesman_names = [row[0] for row in results]

            return response(SUCCESS, salesman_names, HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error during salesman names retrieval: {str(e)}')
            return response(SUCCESS, {'error': 'Error during salesman names retrieval'},HTTP_400_BAD_REQUEST)
            
class AdminDashboard(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    """
    Return Admin dashboard data.
    Args:
        request (HttpRequest): None
    Returns:
        Response: Returns active users count, reports viewed data count and teams count .
    """
    def get(self, request):
        try:
            users_count = User.objects.filter(is_active= True, is_admin= False).count()
            conn = report_services.create_sql_server_connection()
            cursor = conn.cursor()
            sql_query = report_queries.get_team_names()
            cursor.execute(sql_query)
            teams = cursor.fetchall()
            teams_count = len(teams)

            report_data = UserActivityLog.objects.filter( object='Report', action_type='viewed' ).annotate( report=Replace('log', Value('Viewed '), Value(''), output_field=TextField()) ).values( 'report' ).annotate( count=Count('report') ).order_by('-count')
            total_count = UserActivityLog.objects.count()
            reports_count  = len(report_data)
            final_data  = {"active_users": users_count, "total_teams": teams_count, "total_reports": reports_count,"reports_viewed": total_count, "reports_data": report_data}

            return response(SUCCESS, {"reports count": final_data}, HTTP_200_OK)
        except Exception as e:
            logger.error(f'Error during render manager dashboard: {str(e)}')
            return response(SUCCESS, {'error': 'Error during render manager dashboard'},HTTP_400_BAD_REQUEST)
            