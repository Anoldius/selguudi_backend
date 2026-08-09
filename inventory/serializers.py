from rest_framework import serializers
from .models import Category, Product

# 1. Serializer ya Categories
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        # Iwekee automatic business_id ya user aliye-login
        user = self.context['request'].user
        validated_data['business'] = user.business
        return super().create(validated_data)


# 2. Serializer ya Bidhaa (Product)
class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name')

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'category', 'category_name',
            'buying_price', 'selling_price', 'quantity', 'unit',
            'min_stock_alert', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def create(self, validated_data):
        # Aina hii inahakikisha bidhaa inaunganishwa na duka la mtumiaji husika pekee
        user = self.context['request'].user
        validated_data['business'] = user.business
        return super().create(validated_data)