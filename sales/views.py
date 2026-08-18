from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Sale, Customer, Debt, DebtPaymentHistory
from .serializers import (
    SaleCreateSerializer, 
    CustomerSerializer, 
    DebtSerializer, 
    DebtPaymentHistorySerializer
)


class SaleViewSet(viewsets.ModelViewSet):
    serializer_class = SaleCreateSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['payment_method', 'cashier']
    search_fields = ['receipt_number']
    ordering_fields = ['created_at', 'total_amount']

    def get_queryset(self):
        return Sale.objects.filter(business=self.request.user.business).prefetch_related('items__product')


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # USALAMA: Onyesha Wateja wa DUKA HILI pekee!
        return Customer.objects.filter(business=self.request.user.business).order_by('-created_at')

    def perform_create(self, serializer):
        # Sajili mteja na umuunganishe na business ya mtumiaji aliyelogin
        serializer.save(business=self.request.user.business)


class DebtViewSet(viewsets.ModelViewSet):
    serializer_class = DebtSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # USALAMA: Onyesha Madeni ya DUKA HILI pekee!
        return Debt.objects.filter(business=self.request.user.business).order_by('-created_at')

    def perform_create(self, serializer):
        # Sajili deni na ulisajili chini ya business ya mtumiaji aliyelogin
        serializer.save(business=self.request.user.business)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        debt = self.get_object()
        amount = request.data.get('amount_paid')
        notes = request.data.get('notes', '')

        if not amount or float(amount) <= 0:
            return Response({'error': 'Ingiza kiasi sahihi cha malipo'}, status=status.HTTP_400_BAD_REQUEST)

        amount = float(amount)

        if amount > float(debt.remaining_amount):
            return Response({'error': f'Kiasi unacholipa (TZS {amount}) ni kikubwa kuliko deni linalobaki (TZS {debt.remaining_amount})'}, status=status.HTTP_400_BAD_REQUEST)

        debt.paid_amount = float(debt.paid_amount) + amount
        debt.save()

        DebtPaymentHistory.objects.create(
            debt=debt,
            amount_paid=amount,
            notes=notes
        )

        return Response({
            'message': 'Malipo yamerekodiwa kikamilifu!',
            'remaining_amount': debt.remaining_amount,
            'status': debt.status
        }, status=status.HTTP_200_OK)