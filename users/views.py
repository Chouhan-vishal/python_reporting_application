from django.shortcuts import render
from rest_framework.response import Response
from rest_framework.status import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_201_CREATED
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth import authenticate
from .services.auth_token import AuthTokenService
from rest_framework_simplejwt.tokens import Token, RefreshToken, AccessToken
from .services.utils import response
from django.core.exceptions import ValidationError
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from dotenv import load_dotenv
from reporting_application.constants import *
from .services.utils import generate_otp, send_otp_email
from datetime import datetime, timedelta
from django.utils.timezone import now as aware_utcnow
import pyotp
from .serializers import UserSerializer, UserActivityLogSerializer, LoginSerializer
from .models import (
    User,
    OTP,
    TwoFactorAuthentication,
    ReportPermission,
    UserActivityLog
)

from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

import logging
import os

logger = logging.getLogger('users')


@extend_schema(
    request=UserSerializer,
    responses={
        HTTP_201_CREATED: OpenApiTypes.OBJECT,
        HTTP_400_BAD_REQUEST: OpenApiTypes.OBJECT
    },
    parameters=[
        OpenApiParameter(
                name='Authorization',
                location= OpenApiParameter.HEADER,
                description='Authorization token',
                required=True,
                type=OpenApiTypes.STR
            ),
    ]
)
@api_view(['POST'])
@permission_classes([IsAdminUser, IsAuthenticated])
def create(request):
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
            serializer.save()
            return response(SUCCESS, serializer.data, HTTP_201_CREATED)
        logger.debug(f'User creation failed: {serializer.errors}')
        raise ValidationError(f'User creation failed: {str(serializer.errors)}')
    except ValidationError as e:
        logger.error(f'Validation Error during user creation: {str(e)}')
        return response(FAILED, {ERROR: str(e)}, HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f'error during user registration: {str(e)}')
        return response(FAILED, {ERROR: f'error during user registration: {str(e)}'}, HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def two_factor_authentication(request):
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
        username = request.data.get('username')
        password = request.data.get('password')
        user = authenticate(username=username, password=password)
        user_mfa = TwoFactorAuthentication.objects.filter(user=user).first()
        if secret_key:
            user_mfa.is_enabled = True
            user_mfa.secret_key = secret_key
            user_mfa.save()
        secret_key = user_mfa.secret_key
        is_otp_valid = pyotp.TOTP(secret_key).verify(otp)
        if is_otp_valid:
            token = AuthTokenService.get_token_for_user(user)
            logger.info(f"Access token returned successfully for user with id {user.id}")
            return response(SUCCESS, token, HTTP_200_OK)
        else:
            logger.error(f"Invalid OTP for user with id {user.id}")
            return response(FAILED, {ERROR: "Invalid OTP provided"} ,HTTP_200_OK)
    except Exception as e:
        logger.error(f'error during user authentication: {str(e)}')                         
        return response(FAILED, {ERROR: f'error during user authentication: {str(e)}'}, HTTP_400_BAD_REQUEST)                                                                    

@extend_schema(
    request=LoginSerializer,
    responses={
        HTTP_200_OK: {},
        HTTP_400_BAD_REQUEST: {OpenApiTypes.OBJECT}
    }
)
@api_view(['POST'])
def login(request):
    """
    Authenticate a user using username and password.

    Args:
        request (HttpRequest): The request object containing username and password.

    Returns:
        Response: Returns authentication tokens if credentials are valid. 
                  If the user is not an admin, returns a token for authentication 
                  and if the user is admin then follows two factor authentication
                  If the credentials are invalid or an error occurs, returns an error message.
    """

    try:
        username = request.data.get('username')
        password = request.data.get('password')
        if not (username and password):
            raise Exception(f"Username and password are required") 
        user = authenticate(username=username, password=password)
        if user is None:
            return response(FAILED, {"message": "Invalid credentials"}, HTTP_400_BAD_REQUEST)
        if not user.is_admin:
            token = AuthTokenService.get_token_for_user(user)
            logger.info(f'User with id {user.id} logged in  successfully')
            return response(SUCCESS, token, HTTP_200_OK)
        else:
            mfa = TwoFactorAuthentication.objects.filter(user=user).first()
            mfa_enabled = mfa.is_enabled
            logger.info(f'User with "username": {username} authenticated successfully')
            return response(SUCCESS, {"is_valid": True, "mfa_enabled": mfa_enabled} ,HTTP_200_OK)   
    except User.DoesNotExist:
        logger.error(f'User with id {user.id} does not exist')
        return response(FAILED, {ERROR: 'User does not exist'}, HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f'error during OTP verification: {str(e)}')
        return response(FAILED, {ERROR: f'error during OTP verification: {str(e)}'}, HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout a user.

    Args:
        request (HttpRequest): Request object.

    Returns:
        Response: Returns {"message": "Logged out successfully"} upon successful logout.
    """
    try:
        access_token = request.headers.get('Authorization').split(' ')[1]
        if access_token is None:
            return response(FAILED, {"message": "Refresh token is missing"}, HTTP_400_BAD_REQUEST)
        token_obj = AccessToken(access_token)
        token_obj.set_exp(from_time=datetime.now(), lifetime=timedelta(seconds=1))
        return response(SUCCESS, {"message": "Logged out successfully"}, HTTP_200_OK)
    except Exception as e:
        logger.error(f'error during user logout: {str(e)}')
        return response(FAILED, {ERROR: f'error during user logout: {str(e)}'}, HTTP_400_BAD_REQUEST)



@api_view(['GET','PATCH'])
@permission_classes([IsAdminUser, IsAuthenticated])
def users(request, pk=None):
    """
    Get or update users.

    Args:
        request (HttpRequest): Request object.
        pk (int, optional): Primary key of the user to get or update. Defaults to None.
    Returns:
        Response: Returns user details if GET method is used. 
        If PATCH method is used, updates user details.
        For GET method, if pk is none then all users are returned.
    """
    if request.method == 'GET':
        
        if pk:
            try:
                user = User.objects.get(id=pk)
                serializer = UserSerializer(user)
                return response(SUCCESS, serializer.data, HTTP_200_OK)
            except User.DoesNotExist:
                logger.error(f'User with id {pk} does not exist')
                return response(FAILED, {ERROR: 'User does not exist'}, status=HTTP_400_BAD_REQUEST)
            except Exception as e:
                logger.error(f'error during user detail retrieval: {str(e)}')
                return response(FAILED, {ERROR: 'error during user detail retrieval'}, status=HTTP_400_BAD_REQUEST)
        else:
            try:
                users = User.objects.all()
                serializer = UserSerializer(users, many=True)
                return response(SUCCESS, serializer.data, HTTP_200_OK)
            except Exception as e:
                logger.error(f'error during user list retrieval: {str(e)}')
                return response(FAILED, {ERROR: 'error during user list retrieval'}, status=HTTP_400_BAD_REQUEST)

    if request.method == 'PATCH':
        try:
            user = User.objects.get(id=pk)
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return response(SUCCESS ,serializer.data, status=HTTP_200_OK)
            logger.debug(f'User update failed: {serializer.errors}')
            raise ValidationError(f'User update failed: {str(serializer.errors)}')
        except User.DoesNotExist:
            logger.error(f'User with id {pk} does not exist')
            return response(FAILED, {ERROR: 'User does not exist'}, status=HTTP_400_BAD_REQUEST)
        except ValidationError as e:
            logger.error(f'Validation Error during user update: {str(e)}')
            return response(FAILED, {ERROR: str(e)}, status=HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f'error during user update: {str(e)}')
            return response(FAILED, {ERROR: 'error during user update'}, status=HTTP_400_BAD_REQUEST)
        

    
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    try:
        user = request.user
        serializer = UserSerializer(user)
        logger.info(f'User with "username": {user.username} retrieved successfully')
        return response(SUCCESS, serializer.data, HTTP_200_OK)
    except Exception as e:
        logger.error(f'error during user detail retrieval: {str(e)}')
        return response(FAILED, {ERROR: 'error during user detail retrieval'}, status=HTTP_400_BAD_REQUEST)
    
@api_view(['PATCH'])
@permission_classes([IsAdminUser, IsAuthenticated])
def profile_update(request, pk):
    """
    Update user profile.

    Args:
        request (HttpRequest): Request object containing updated user profile data.
        pk (int): Primary key of the user to update.

    Returns:
        Response: Returns updated user profile data if successful, else returns an error.
    """

    try:
        user = User.objects.get(id=pk)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return response(SUCCESS, serializer.data, status=HTTP_200_OK)
        logger.debug(f'User update failed: {serializer.errors}')
        raise ValidationError(f'User update failed: {str(serializer.errors)}')
    except User.DoesNotExist:
        logger.error(f'User with id {pk} does not exist')
        return response({ERROR: 'User does not exist'}, status=HTTP_400_BAD_REQUEST)
    except ValidationError as e:
        logger.error(f'error during user update: {str(e)}')
        return response(FAILED, {ERROR: str(e)}, status=HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f'error during user update: {str(e)}')
        return response(FAILED, {ERROR: 'error during user update'}, status=HTTP_400_BAD_REQUEST)
    
    


@api_view(['POST'])
def reset_password_request_otp(request):
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
        return response(SUCCESS, {"message": "OTP sent to your email"}, HTTP_200_OK)
    except User.DoesNotExist:
        logger.error(f'User with email {email} does not exist')
        return response(FAILED, {ERROR: f'User with email {email} does not exist'}, HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f'error during forgot password: {str(e)}')
        return response(FAILED, {ERROR: f'error during forgot password: {str(e)}'}, HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def verify_otp(request):
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
            # OTP is valid
            otp_object.delete()
            logger.info(f'OTP verified for user {user.email}')
            return response(SUCCESS, {"message": "OTP verified successfully"}, HTTP_200_OK)
        else:
            # OTP is invalid
            logger.error(f'OTP is invalid for user {user.email}')
            otp_object.delete()
            return response(FAILED, {ERROR: 'OTP Expired'}, HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f'error during OTP verification: {str(e)}')
        return response(FAILED, {ERROR: f'error during OTP verification: {str(e)}'}, HTTP_400_BAD_REQUEST)
    
@api_view(['POST'])
def reset_password(request):
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

        if not new_password or not confirm_password:
            logger.error(f'New password and confirm password are required')
            return response(FAILED, {ERROR: 'New password and confirm password are required'}, HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            logger.error(f'New password and confirm password do not match')
            return response(FAILED, {ERROR: 'New password and confirm password do not match'}, HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        logger.info(f'Password reset for user {user.email}')
        return response(SUCCESS, {"message": "Password reset successfully"}, HTTP_200_OK)
    except Exception as e:
        logger.error(f'error during password reset: {str(e)}')
        return response(FAILED, {ERROR: f'error during password reset: {str(e)}'}, HTTP_400_BAD_REQUEST)
    


@api_view(['PATCH'])
@permission_classes([IsAuthenticated, IsAdminUser])
def report_permissions(request, user_id):
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
        return response(SUCCESS, {"message": "Permissions updated successfully"}, HTTP_200_OK)        
    except Exception as e:
        logger.error(f'Error during report permission update: {str(e)}')
        return response(FAILED, {ERROR: f'Error during report permission update: {str(e)}'}, HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def report_logs(request):
    """
    Return User Activity Logs.

    Args:
        request (HttpRequest): None

    Returns:
        Response: Returns All the User Activity Logs from UserActivityLog model.
    """
    try:
        user_activity_logs = UserActivityLog.objects.all()
        serializer = UserActivityLogSerializer(user_activity_logs, many=True)
        return response(SUCCESS, serializer.data, HTTP_200_OK)
    except Exception as e:
        logger.error(f'Error during report logs retrieval: {str(e)}')
        return response(FAILED, {ERROR: f'Error during report logs retrieval: {str(e)}'}, HTTP_400_BAD_REQUEST)