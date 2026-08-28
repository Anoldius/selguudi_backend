from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, FloatField
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer
from authentication.models import BusinessPermission  # Hakikisha import hii ipo kulingana na app yako ya permissions


# 1. ViewSet ya Category
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            return Category.objects.filter(business=user.business).order_by('name')
        return Category.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            serializer.save(business=user.business)
        else:
            raise serializers.ValidationError({
                "detail": "Mtumiaji huyu hajahusianishwa na duka/biashara yoyote."
            })


# 2. ViewSet ya Product (Bidhaa na Stoko)
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # ZIMA PAGINATION ILI BIDHAA ZOTE ZIONEKANE
    pagination_class = None
    
    # Kusaidia Kusearch na Ku-filter bidhaa kwa haraka
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'unit', 'is_active']
    search_fields = ['name', 'barcode']
    ordering_fields = ['name', 'selling_price', 'quantity']

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            return Product.objects.filter(business=user.business).order_by('-created_at')
        return Product.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            serializer.save(business=user.business)
        else:
            raise serializers.ValidationError({
                "detail": "Mtumiaji huyu hajahusianishwa na duka/biashara yoyote."
            })

    # CUSTOM ENDPOINT: /api/inventory/products/summary/
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def summary(self, request):
        user = request.user
        if not (hasattr(user, 'business') and user.business):
            return Response({
                'total_current_cost': 0.0,
                'total_potential_retail': 0.0,
                'expected_stock_profit': 0.0,
                'total_products_count': 0
            }, status=status.HTTP_200_OK)

        queryset = self.get_queryset()
        total_products_count = queryset.count()

        # Kagua Business Permissions zilizowekwa na Bosi
        business = user.business
        perm = BusinessPermission.objects.filter(business=business).first()
        
        # Angalia kama ruhusa za kuona faida na bei ya mtaji zimewashwa
        can_see_profit = perm.show_profit_to_cashier if perm else True
        can_see_buying_price = perm.show_buying_price_to_cashier if perm else True

        # KAMA RUHUSA IMESHAZIMWA (False), FICHA THAMANI ZOTE NA URUDISHE 0.0
        if not can_see_profit or not can_see_buying_price:
            return Response({
                'total_current_cost': 0.0,
                'total_potential_retail': 0.0,
                'expected_stock_profit': 0.0,
                'total_products_count': total_products_count
            }, status=status.HTTP_200_OK)

        # 1. Thamani ya Stoko ya Sasa kwa Bei ya Kununulia (Cost Price * Quantity)
        cost_sum = queryset.aggregate(
            total=Sum(F('quantity') * F('buying_price'), output_field=FloatField())
        )['total'] or 0.0

        # 2. Thamani Tarajiwa ya Mauzo kwa Bei ya Kuuzia (Selling Price * Quantity)
        retail_sum = queryset.aggregate(
            total=Sum(F('quantity') * F('selling_price'), output_field=FloatField())
        )['total'] or 0.0

        # 3. Kadirio la Faida Kwenye Stoko
        expected_profit = retail_sum - cost_sum

        return Response({
            'total_current_cost': round(cost_sum, 2),
            'total_potential_retail': round(retail_sum, 2),
            'expected_stock_profit': round(expected_profit, 2),
            'total_products_count': total_products_count
        }, status=status.HTTP_200_OK)