from django.urls import path
from .views import DashboardSummaryView, LowStockProductsView, TopSellingProductsView

urlpatterns = [
    path('dashboard/', DashboardSummaryView.as_view(), name='dashboard_summary'),
    path('low-stock/', LowStockProductsView.as_view(), name='low_stock_report'),
    path('top-selling/', TopSellingProductsView.as_view(), name='top_selling_report'),
]