import jwt
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken

class AuthTokenService:
    @staticmethod
    def get_token_for_user(user):
        try:
            refresh = RefreshToken.for_user(user)

            return {
                'access': str(refresh.access_token),
            }
        except Exception as e:
            return None
