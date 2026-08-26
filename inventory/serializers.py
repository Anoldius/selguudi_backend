from rest_framework import serializers
from .models import Category, Product

# 1. Serializer ya Categories
class CategorySerializer(serializers.ModelSerializer):
    products_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at', 'products_count']
        read_only_fields = ['id', 'created_at']

    def get_products_count(self, obj):
        return obj.products.filter(is_active=True).count()

    def create(self, validated_data):
        user = self.context['request'].user
        user_business = getattr(user, 'business', None)
        if not user_business:
            raise serializers.ValidationError({
                "detail": "Akaunti hii haina Duka/Business iliyounganishwa nayo!"
            })
        validated_data['business'] = user_business
        return super().create(validated_data)


# 2. Serializer ya Bidhaa (Product)
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name', default=None)

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'category', 'category_name',
            'buying_price', 'selling_price', 'quantity', 'unit',
            'min_stock_alert', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_barcode(self, value):
        if value is not None and value.strip() == '':
            return None
        return value

    def create(self, validated_data):
        user = self.context['request'].user
        user_business = getattr(user, 'business', None)
        
        if not user_business:
            raise serializers.ValidationError({
                "detail": "Mtumiaji huyu hajahusianishwa na duka/biashara yoyote!"
            })
            
        validated_data['business'] = user_business
        return super().create(validated_data)