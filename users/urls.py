from django.urls import path
from . import views

urlpatterns = [
    path('', views.users),
    path("two-factor-authentication/", views.two_factor_authentication),
    path("two-factor-authentication", views.two_factor_authentication),
    path('create', views.create),
    path('create/', views.create),
    path('login', views.login, name='login'),
    path('login/', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('logout/', views.logout, name='logout'),
    path('<int:pk>', views.users),
    path('<int:pk>/', views.users),
    path('request-password-reset-otp', views.reset_password_request_otp),
    path('request-password-reset-otp/', views.reset_password_request_otp),
    path('verify-otp', views.verify_otp),
    path('verify-otp/', views.verify_otp),
    path('reset-password', views.reset_password),
    path('reset-password/', views.reset_password),
    path('profile/', views.profile),
    path('profile', views.profile),
    path('<int:user_id>/report_permissions/', views.report_permissions),
    path('<int:user_id>/report_permissions', views.report_permissions)
]
