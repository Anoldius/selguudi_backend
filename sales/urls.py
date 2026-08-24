from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, CustomerViewSet, DebtViewSet, ExpenseViewSet

router = DefaultRouter()

# Sajili SaleViewSet chini ya 'transactions' na 'sales' ili kuzuia 404 Not Found
router.register(r'transactions', SaleViewSet, basename='transaction')
router.register(r'sales', SaleViewSet, basename='sale')

router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'debts', DebtViewSet, basename='debt')
router.register(r'expenses', ExpenseViewSet, basename='expense')

urlpatterns = [
    path('', include(router.urls)),
]