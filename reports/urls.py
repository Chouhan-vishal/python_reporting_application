from django.urls import path
from . import views

urlpatterns = [
    path('sales_summary_report/', views.sales_summary_report),
]    