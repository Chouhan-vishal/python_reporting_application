from django.urls import path
from . import views

urlpatterns = [
    path('', views.health, name='index'),
    path('data/', views.report_data),
]    