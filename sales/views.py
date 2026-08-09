from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Sale
from .serializers import SaleCreateSerializer


class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['payment_method', 'cashier']
    search_fields = ['receipt_number']
    ordering_fields = ['created_at', 'total_amount']

    def get_queryset(self):
        # USALAMA: Onyesha Risiti za DUKA HILI pekee!
        return Sale.objects.filter(business=self.request.user.business).prefetch_related('items__product')