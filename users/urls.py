from django.urls import path, re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.Users.as_view()),
    re_path(r'^two-factor-authentication/?$', views.TwoFactorAuthenticationView.as_view()),
    re_path(r'^login/?$', views.Login.as_view()),
    re_path(r'^logout/?$', views.Logout.as_view()),
    re_path(r'^(?P<pk>\d+)/?$', views.Users.as_view()),
    re_path(r'^request-password-reset-otp/?$', views.ResetPasswordRequestOTP.as_view()),
    re_path(r'^verify-otp/?$', views.VerifyOTP.as_view()),
    re_path(r'^reset-password/?$', views.ResetPassword.as_view()),
    re_path(r'^search/?$', views.UserSearch.as_view()),
    re_path(r'^profile/?$', views.Profile.as_view()),
    re_path(r'^(?P<user_id>\d+)/report_permissions/?$', views.ReportPermissions.as_view()),
    re_path(r'^report-logs/?$', views.ReportLogs.as_view()),
    re_path(r'^teams/?$', views.TeamNames.as_view()),
    re_path(r'^managers/?$', views.ManagerList.as_view()),
    re_path(r'^salesmans/?$', views.SalesmanList.as_view()),
]

