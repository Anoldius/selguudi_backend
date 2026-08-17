from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SaleViewSet, CustomerViewSet, DebtViewSet

router = DefaultRouter()
router.register(r'transactions', SaleViewSet, basename='sale')
router.register(r'customers', CustomerViewSet, basename='customer')
router.register(r'debts', DebtViewSet, basename='debt')

urlpatterns = [
    path('', include(router.urls)),
]