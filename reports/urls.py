from . import views
from django.urls import path

urlpatterns = [
    path('sales-summary-report/', views.SalesSummary.as_view()),
    path('sales-collection-outstanding-report/', views.SalesCollectionOutstanding.as_view()),
    path('product-wise-sales-summary-report/', views.ProductWiseSalesSummary.as_view()),
    path('weekly-summary-report/', views.WeeklySummary.as_view()),
    path('collection-report/', views.Collection.as_view()),
    path('customer-wise-outstanding-report/', views.CustomerWiseOutstanding.as_view()),
    path('cr-utilization-report/', views.CrUtilization.as_view()),
    path('salesman-and-product-wise-report/', views.SalesmanAndProductWise.as_view()),
    path('target-and-achieved-report/', views.TargetAndAchieved.as_view()),
    path('welding-electrode-product-report/', views.WeldingElectrode.as_view()),
    path('durastrong-tmt-product-report/', views.DurastrongTMTProductSales.as_view()),
    path('sales-register-report/', views.SalesRegister.as_view()),
    path('block-customers-list-report/', views.BlockCustomersList.as_view()),
    path('target-customers-sales-report/', views.TargetCustomerSales.as_view()),
    path('product-wise-mom-report/', views.ProductWiseMonthSales.as_view()),
    path('review-product-wise-report/', views.ReviewProductWise.as_view()),
    path('all-customers-sales-report/', views.AllCustomersSales.as_view()),
    path('review-salesman-wise-report/', views.ReviewSalesmanWise.as_view()),
    path('salesman-kpi-dashboard/', views.SalesmanKpiDashboard.as_view()),
    path('incentive-report/', views.IncentiveReport.as_view()),
]
