from rest_framework import serializers
from .models import Category, Product
from authentication.models import BusinessPermission  # Hakikisha njia hii ya import inafanana na app yako ya permissions


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
        Kagua kama duka linaruhusu kuonyesha Bei ya Kununulia (buying_price).
        Kama ruhusa ipo False, rejesha 0 badala ya bei halisi.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            business = getattr(user, 'business', None)
            
            if business:
                perm = BusinessPermission.objects.filter(business=business).first()
                if perm and not perm.show_buying_price_to_cashier:
                    return 0

        return obj.buying_price

    def to_internal_value(self, data):
        """
        Kama buying_price haijatumwa kwenye request (kwa sababu field imefichwa frontend),
        weka default value ya 0 au tumia iliyopo ili kuzuia ValidationError.
        """
        data = data.copy()
        if 'buying_price' not in data or data['buying_price'] == '' or data['buying_price'] is None:
            if self.instance:
                data['buying_price'] = self.instance.buying_price
            else:
                data['buying_price'] = 0
        return super().to_internal_value(data)

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