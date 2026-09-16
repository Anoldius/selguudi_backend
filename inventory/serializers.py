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


# 2. Serializer ya Bidhaa (Product) - FIX HAPA
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

    def to_representation(self, instance):
        """
        Dhibiti nini kinaonyeshwa wakati wa kusoma (GET Request):
        - Owner anaona bei ya mtaji siku zote.
        - Cashier ataona 0.0 kama toggle ya show_buying_price_to_cashier ipo OFF.
        """
        data = super().to_representation(instance)
        request = self.context.get('request')

        if request and hasattr(request, 'user'):
            user = request.user
            role = getattr(user, 'role', 'cashier')
            business = getattr(user, 'business', None)

            # Kama ni Cashier na toggle ipo OFF, fanya buying_price iwe 0.0
            if role != 'owner' and business and not getattr(business, 'show_buying_price_to_cashier', False):
                data['buying_price'] = 0.0

        return data

    def create(self, validated_data):
        user = self.context['request'].user
        user_business = getattr(user, 'business', None)
        
        if not user_business:
            raise serializers.ValidationError({
                "detail": "Mtumiaji huyu hajahusianishwa na duka/biashara yoyote!"
            })
            
        validated_data['business'] = user_business
        return super().create(validated_data)