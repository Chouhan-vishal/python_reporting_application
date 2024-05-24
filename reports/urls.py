from django.urls import path
from . import views

urlpatterns = [
    path('sales-summary-report/', views.sales_summary_report),
    path('sales-collection-outstanding-report/', views.sales_collection_outstanding_report),
    path('product-wise-sales-summary/', views.product_wise_sales_summary),
    path('weekly-summary/', views.weekly_summary),
    path('collection-report/', views.collection_report),
    path('customer-wise-outstanding/', views.customer_wise_outstanding),
    
]
