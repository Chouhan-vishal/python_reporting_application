from django.urls import path
from . import views

urlpatterns = [
    path('sales-summary-report/', views.sales_summary_report),
    path('sales-collection-outstanding-report/', views.sales_collection_outstanding_report),
    path('product-wise-sales-summary-report/', views.product_wise_sales_summary),
    path('weekly-summary-report/', views.weekly_summary),
    path('collection-report/', views.collection_report),
    path('customer-wise-outstanding-report/', views.customer_wise_outstanding),
    path('cr-utilization-report/', views.cr_utilization_report),
    path('team-and-product-wise-report/', views.team_and_product_wise_report),
    path('salesman-and-product-wise-report/', views.salesman_and_product_wise_report),
    path('target-and-achieved-report/', views.target_and_achieved_report),
    path('welding-electrode-product-report/', views.welding_electrode_product_sales_report),
]
