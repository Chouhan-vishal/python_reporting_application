from django.urls import path
from . import views

urlpatterns = [
    path('sales_summary_report/', views.sales_summary_report),
    path('sales_collection_outstanding_report/', views.sales_collection_outstanding_report),
]
