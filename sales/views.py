from django.db import connection
from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Sale, Customer, Debt, DebtPaymentHistory, Expense
from .serializers import (
    SaleCreateSerializer, 
    CustomerSerializer, 
    DebtSerializer, 
    DebtPaymentHistorySerializer,
    ExpenseSerializer
)


# Hii block inahakikisha column za business_id zipo kwenye database bila kutegemea migration iliyostuck
def ensure_business_columns():
    with connection.cursor() as cursor:
        try:
            cursor.execute("ALTER TABLE sales_customer ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES accounts_business(id) ON DELETE CASCADE;")
            cursor.execute("ALTER TABLE sales_debt ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES accounts_business(id) ON DELETE CASCADE;")
            cursor.execute("ALTER TABLE sales_expense ADD COLUMN IF NOT EXISTS business_id UUID REFERENCES accounts_business(id) ON DELETE CASCADE;")
        except Exception:
            pass

ensure_business_columns()


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
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            return Customer.objects.filter(business=user.business).order_by('-created_at')
        return Customer.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            serializer.save(business=user.business)
        else:
            raise serializers.ValidationError({"detail": "User hana biashara iliyosajiliwa."})


class DebtViewSet(viewsets.ModelViewSet):
    serializer_class = DebtSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            return Debt.objects.filter(business=user.business).order_by('-created_at')
        return Debt.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            serializer.save(business=user.business)
        else:
            raise serializers.ValidationError({"detail": "User hana biashara iliyosajiliwa."})

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


# 4. ViewSet ya Matumizi ya Duka (Expense Management)
class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            return Expense.objects.filter(business=user.business).order_by('-created_at')
        return Expense.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            serializer.save(
                business=user.business,
                recorded_by=user
            )
        else:
            raise serializers.ValidationError({"detail": "User hana biashara iliyosajiliwa."})