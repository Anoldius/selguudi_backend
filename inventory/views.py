from rest_framework import viewsets, permissions, filters, status
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

# 1. ViewSet ya Category
class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            return Category.objects.filter(business=user.business)
        return Category.objects.none()

    def perform_create(self, serializer):
        serializer.save(business=self.request.user.business)


# 2. ViewSet ya Product (Bidhaa na Stoko)
class ProductViewSet(viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    # Kusaidia Kusearch na Ku-filter bidhaa kwa haraka
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'unit', 'is_active']
    search_fields = ['name', 'barcode']
    ordering_fields = ['name', 'selling_price', 'quantity']

    def get_queryset(self):
        user = self.request.user
        # Hakikisha user ana business kabla ya ku-filter
        if hasattr(user, 'business') and user.business:
            return Product.objects.filter(business=user.business).order_by('-id')
        return Product.objects.none()

    def perform_create(self, serializer):
        # Mhimu: Ambatanisha duka (business) la mtumiaji aliyelogin otomatiki!
        user = self.request.user
        if hasattr(user, 'business') and user.business:
            serializer.save(business=user.business)
        else:
            raise serializers.ValidationError({
                "detail": "Mtumiaji huyu hajahusianishwa na duka/biashara yoyote."
            })