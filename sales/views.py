from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Sale
from .serializers import SaleCreateSerializer
from .models import Customer, Debt, DebtPaymentHistory
from .serializers import CustomerSerializer, DebtSerializer, DebtPaymentHistorySerializer


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



class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all().order_by('-created_at')
    serializer_class = CustomerSerializer


class DebtViewSet(viewsets.ModelViewSet):
    queryset = Debt.objects.all().order_by('-created_at')
    serializer_class = DebtSerializer

    # Endpoint ya kusajili Malipo ya Deni (Mfano: POST /api/debts/{id}/pay/)
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

        # 1. Ongeza malipo kwenye debt model
        debt.paid_amount = float(debt.paid_amount) + amount
        debt.save()

        # 2. Hifadhi history ya malipo haya
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

