from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from users.models import UserToken
from django.http import JsonResponse
import logging

logger = logging.getLogger(__name__)

class SingleDeviceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        auth = JWTAuthentication()
        try:
            if not 'login' in request.path and not 'authentication' in request.path and not 'reset-password' in request.path and 'request-password-reset-otp' not in request.path and not 'verify-otp' in request.path:
                user, token = auth.authenticate(request)
                try:
                    user_token = UserToken.objects.get(user=user)
                except UserToken.DoesNotExist:
                    # Log and return error if UserToken does not exist
                    logger.error(f'UserToken does not exist for user: {user.id}')
                    return JsonResponse({"error": "Token record not found. Please log in again."}, status=401)

                if user_token.token != str(token):
                    return JsonResponse({"error": "Token is invalid or has been replaced by a new login"}, status=401)
            response = self.get_response(request)
            return response
        
        except (InvalidToken, UserToken.DoesNotExist) as e:
            return JsonResponse({"error": "Invalid or expired token"}, status=401)
        
        except Exception as e:
            logger.error(f'Error during middleware processing: {str(e)}')
            return JsonResponse({"error": str(e)}, status=500)