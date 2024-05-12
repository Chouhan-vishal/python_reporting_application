"""
URL configuration for reporting_application project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from rest_framework import permissions
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView

urlpatterns = [
    re_path('^api/schema/?$', SpectacularAPIView.as_view(), name='schema'),
    # Optional UI:
    re_path('^api/schema/swagger-ui/?$', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    re_path('^api/schema/redoc/?$', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
    # Project URLs
    re_path('^admin/?$', admin.site.urls),
    re_path("^api/users/?",include("users.urls")),
    # re_path("^api/reports/?$",include("reports.urls")),
]
