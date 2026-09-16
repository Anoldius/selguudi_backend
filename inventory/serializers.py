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


class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name', default=None)
    buying_price = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'barcode', 'category', 'category_name',
            'buying_price', 'selling_price', 'quantity', 'unit',
            'min_stock_alert', 'is_active', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_buying_price(self, obj):
        """
        Boss (Owner) anaona bei halisi ya mtaji wakati wote.
        Cashier ataona 0.0 PEKEE kama toggle ya show_buying_price_to_cashier ipo OFF.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            role = getattr(user, 'role', 'cashier')
            business = getattr(user, 'business', None)

            # Boss (Owner) aonyeshwe bei halisi siku zote
            if role == 'owner':
                return obj.buying_price

            # Kama ni Cashier na toggle ya Mipangilio ipo OFF, rejesha 0.0
            if business and not getattr(business, 'show_buying_price_to_cashier', False):
                return 0.0

        return obj.buying_price