from datetime import datetime
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Count
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Product
from sales.models import Sale, SaleItem


# 1. API ya Muhtasari wa Dashboard ya Siku (Daily Summary)
class DashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        business = request.user.business
        today = timezone.now().date()

        # A. Mauzo ya Leo Pekee
        today_sales = Sale.objects.filter(
            business=business, 
            created_at__date=today
        )

        total_sales_amount = today_sales.aggregate(total=Sum('total_amount'))['total'] or 0.00
        total_receipts_count = today_sales.count()

        # B. Hesabu Faida ya Leo (Total Revenue - Total Cost)
        # Faida = (Selling Price - Buying Price) * Quantity
        profit_query = SaleItem.objects.filter(
            sale__business=business,
            sale__created_at__date=today
        ).annotate(
            item_profit=ExpressionWrapper(
                (F('unit_price') - F('product__buying_price')) * F('quantity'),
                output_field=DecimalField()
            )
        ).aggregate(total_profit=Sum('item_profit'))

        total_profit = profit_query['total_profit'] or 0.00

        # C. Idadi ya Bidhaa Zilizo na Stoko Ndogo (Low Stock Alert Count)
        low_stock_count = Product.objects.filter(
            business=business,
            quantity__lte=F('min_stock_alert'),
            is_active=True
        ).count()

        return Response({
            "date": today,
            "today_total_sales": float(total_sales_amount),
            "today_receipts": total_receipts_count,
            "today_estimated_profit": float(total_profit),
            "low_stock_items_count": low_stock_count
        }, status=status.HTTP_200_OK)


# 2. API ya Orodha ya Bidhaa Zilizobaki Kidogo (Low Stock Report)
class LowStockProductsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        business = request.user.business
        low_stock_products = Product.objects.filter(
            business=business,
            quantity__lte=F('min_stock_alert'),
            is_active=True
        ).values('id', 'name', 'quantity', 'min_stock_alert', 'unit')

        return Response(list(low_stock_products), status=status.HTTP_200_OK)


# 3. API ya Bidhaa Zinazotoka Sana (Top Selling Products)
class TopSellingProductsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        business = request.user.business
        
        top_products = SaleItem.objects.filter(
            sale__business=business
        ).values('product__id', 'product__name').annotate(
            total_quantity_sold=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_quantity_sold')[:10]  # Top 10

        return Response(list(top_products), status=status.HTTP_200_OK)