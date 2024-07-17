from . import views
from django.urls import path

urlpatterns = [
    path('sales-summary-report/', views.SalesSummaryReport.as_view()),
    path('sales-collection-outstanding-report/', views.SalesCollectionOutstandingReportView.as_view()),
    path('product-wise-sales-summary-report/', views.ProductWiseSalesSummary.as_view()),
    path('weekly-summary-report/', views.WeeklySummary.as_view()),
    path('collection-report/', views.CollectionReport.as_view()),
    path('customer-wise-outstanding-report/', views.CustomerWiseOutstanding.as_view()),
    path('cr-utilization-report/', views.CrUtilizationReport.as_view()),
    path('salesman-and-product-wise-report/', views.SalesmanAndProductWiseReport.as_view()),
    path('target-and-achieved-report/', views.TargetAndAchievedReport.as_view()),
    path('welding-electrode-product-report/', views.WeldingElectrodeProductSalesReports.as_view()),
    path('durastrong-tmt-product-report/', views.DurastrongTmtProductSalesReport.as_view()),
    path('sales-register-report/', views.SalesRegisterReport.as_view()),
    path('block-customers-list-report/', views.BlockCustomersListReport.as_view()),
    path('target-customers-sales-report/', views.TargetCustomerSalesReport.as_view()),
    path('product-wise-mom-report/', views.ProductWiseMonthOnMonthReport.as_view()),
    path('review-product-wise-report/', views.ReviewProductWiseReport.as_view()),
    path('all-customers-sales-report/', views.AllCustomersMomReport.as_view()),
    path('review-salesman-wise-report/', views.ReviewSalesmanWiseData.as_view()),
    path('salesman-kpi-dashboard/', views.SalesmanKpiDashboard.as_view()),
    path('incentive-report/', views.IncentiveReport.as_view()),
]
