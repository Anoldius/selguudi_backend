from rest_framework import viewsets, permissions, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

# 1. ViewSet ya Category
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # SARAFI YA USALAMA: Kurudisha tu categories za duka la user huyu!
        return Category.objects.filter(business=self.request.user.business)


# 2. ViewSet ya Product (Bidhaa na Stoko)
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # Kusaidia Kusearch na Ku-filter bidhaa kwa haraka (Search & Filter Backends)
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'unit', 'is_active']
    search_fields = ['name', 'barcode']
    ordering_fields = ['name', 'selling_price', 'quantity']

    def get_queryset(self):
        # SARAFI YA USALAMA: Kurudisha bidhaa za duka la user huyu pekee!
        return Product.objects.filter(business=self.request.user.business)