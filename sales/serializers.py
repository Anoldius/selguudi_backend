import uuid
from django.db import transaction
from rest_framework import serializers
from inventory.models import Product
from .models import Sale, SaleItem, Expense



class SaleItemSerializer(serializers.ModelSerializer):
    product_id = serializers.UUIDField()
    product_name = serializers.ReadOnlyField(source='product.name')

    class Meta:
        model = SaleItem
        fields = ['id', 'product_id', 'product_name', 'quantity', 'unit_price', 'total_price']
        read_only_fields = ['id', 'unit_price', 'total_price']


class SaleCreateSerializer(serializers.ModelSerializer):
    items = SaleItemSerializer(many=True)

    class Meta:
        model = Sale
        fields = ['id', 'receipt_number', 'total_amount', 'payment_method', 'created_at', 'items']
        read_only_fields = ['id', 'receipt_number', 'total_amount', 'created_at']

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user
        business = user.business

        if not items_data:
            raise serializers.ValidationError({"items": "Hauwezi kukamilisha muamala bila kuweka bidhaa angalau moja."})

        # DB Transaction ya Atomic - Kila kitu kinakamilika kwa pamoja au kuzuiliwa kwa pamoja
        with transaction.atomic():
            # A. Tengeneza Receipt Number ya kipekee (mfano: SEL-20260729-ABCD)
            receipt_no = f"SEL-{uuid.uuid4().hex[:8].upper()}"

            # B. Tengeneza Header ya Sale
            sale = Sale.objects.create(
                business=business,
                cashier=user,
                receipt_number=receipt_no,
                payment_method=validated_data.get('payment_method', 'cash'),
                total_amount=0.00
            )

            calculated_total = 0.00

            # C. Pitia kila Item, Kagua Stoko, na Ukate Stoko
            for item_data in items_data:
                product_id = item_data['product_id']
                qty_to_buy = item_data['quantity']

                try:
                    # Hakikisha bidhaa ni ya DUKA HILI tu
                    product = Product.objects.select_for_update().get(id=product_id, business=business)
                except Product.DoesNotExist:
                    raise serializers.ValidationError({
                        "product": f"Bidhaa yenye ID {product_id} haipo kwenye duka hili."
                    })

                # Validations za Stoko
                if product.quantity < qty_to_buy:
                    raise serializers.ValidationError({
                        "stock_error": f"Stoko haitoshi kwa bidhaa '{product.name}'. Iliyopo ni {product.quantity} {product.unit}, lakini unajaribu kuuza {qty_to_buy}."
                    })

                # 1. Kata Stoko Kiotomatiki
                product.quantity -= qty_to_buy
                product.save()

                # 2. Hesabu Bei ya Mauzo
                item_total = qty_to_buy * product.selling_price
                calculated_total += float(item_total)

                # 3. Hifadhi SaleItem
                SaleItem.objects.create(
                    sale=sale,
                    product=product,
                    quantity=qty_to_buy,
                    unit_price=product.selling_price,
                    total_price=item_total
                )

            # D. Hifadhi Jumla ya Pesa kwenye Sale
            sale.total_amount = calculated_total
            sale.save()

            return sale


from rest_framework import serializers
from .models import Customer, Debt, DebtPaymentHistory

class CustomerSerializer(serializers.ModelSerializer):
    total_debt = serializers.ReadOnlyField()

    class Meta:
        model = Customer
        fields = ['id', 'name', 'phone', 'total_debt', 'created_at']


class DebtPaymentHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = DebtPaymentHistory
        fields = ['id', 'amount_paid', 'notes', 'created_at']

class DebtSerializer(serializers.ModelSerializer):
    customer_name = serializers.ReadOnlyField(source='customer.name')
    customer_phone = serializers.ReadOnlyField(source='customer.phone')
    payment_history = DebtPaymentHistorySerializer(many=True, read_only=True)

    class Meta:
        model = Debt
        fields = [
            'id', 'customer', 'customer_name', 'customer_phone', 
            'total_amount', 'paid_amount', 'remaining_amount', 
            'status', 'due_date', 'payment_history', 'created_at'
        ]
        # Weka hivi ili backend ijaze zenyewe zikiwa za kusoma tu:
        read_only_fields = ['paid_amount', 'remaining_amount', 'status']


class ExpenseSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.ReadOnlyField(source='recorded_by.username')

    class Meta:
        model = Expense
        fields = ['id', 'title', 'amount', 'category', 'description', 'recorded_by_name', 'created_at']

