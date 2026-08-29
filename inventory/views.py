from rest_framework import viewsets, permissions, filters, status, serializers
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, F, FloatField
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer


# PERMISSION MAALUM: Cashier anaona tu (GET), lakini Bosi (Owner) ndiye anayeongeza, ku-edit au kufuta
class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Njia za kusoma tu (GET, HEAD, OPTIONS) zinaruhusiwa kwa wote walio-login
        if request.method in permissions.SAFE_METHODS:
            return True
        # Njia za kubadilisha au kufuta (POST, PUT, PATCH, DELETE) ni kwa Owner pekee
        return getattr(request.user, 'role', '') == 'owner'


# 1. ViewSet ya Category
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsOwnerOrReadOnly]
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
    permission_classes = [IsOwnerOrReadOnly]
    pagination_class = None
    
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
        business = getattr(user, 'business', None)

        if not business:
            return Response({
                'total_current_cost': 0.0,
                'total_potential_retail': 0.0,
                'expected_stock_profit': 0.0,
                'total_products_count': 0
            }, status=status.HTTP_200_OK)

        queryset = self.get_queryset()
        total_products_count = queryset.count()

        # KAGUA ROLE YA USER: Kama sio Owner, rudisha 0.0
        if getattr(user, 'role', '') != 'owner':
            return Response({
                'total_current_cost': 0.0,
                'total_potential_retail': 0.0,
                'expected_stock_profit': 0.0,
                'total_products_count': total_products_count
            }, status=status.HTTP_200_OK)

        # KAMA NI OWNER, KOKOTOA DATA HALISI
        cost_sum = queryset.aggregate(
            total=Sum(F('quantity') * F('buying_price'), output_field=FloatField())
        )['total'] or 0.0

        retail_sum = queryset.aggregate(
            total=Sum(F('quantity') * F('selling_price'), output_field=FloatField())
        )['total'] or 0.0

        expected_profit = retail_sum - cost_sum

        return Response({
            'total_current_cost': round(cost_sum, 2),
            'total_potential_retail': round(retail_sum, 2),
            'expected_stock_profit': round(expected_profit, 2),
            'total_products_count': total_products_count
        }, status=status.HTTP_200_OK)