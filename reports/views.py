from datetime import datetime
from django.db.models import Sum, F, ExpressionWrapper, DecimalField, Count
from django.utils import timezone
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from inventory.models import Product
from sales.models import Sale, SaleItem


# 1. API ya Muhtasari wa Dashboard / Ripoti (Filter kwa Kipindi + Permission Protection)
class DashboardSummaryView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        business = getattr(user, 'business', None)

        if not business:
            return Response({
                "date": timezone.now().date(),
                "today_total_sales": 0.0,
                "today_receipts": 0,
                "today_estimated_profit": 0.0,
                "low_stock_items_count": 0
            }, status=status.HTTP_200_OK)

        # Chagua Kipindi cha Takwimu (Default: 'today')
        period = request.GET.get('period', 'today')
        now = timezone.now()
        today = now.date()

        sales_filter = {'business': business}
        items_filter = {'sale__business': business}

        if period == 'today':
            sales_filter['created_at__date'] = today
            items_filter['sale__created_at__date'] = today
        elif period == 'yesterday':
            yesterday = today - timezone.timedelta(days=1)
            sales_filter['created_at__date'] = yesterday
            items_filter['sale__created_at__date'] = yesterday
        elif period == 'week':
            start_of_week = today - timezone.timedelta(days=7)
            sales_filter['created_at__date__gte'] = start_of_week
            items_filter['sale__created_at__date__gte'] = start_of_week
        elif period == 'month':
            start_of_month = today - timezone.timedelta(days=30)
            sales_filter['created_at__date__gte'] = start_of_month
            items_filter['sale__created_at__date__gte'] = start_of_month

        # A. Mauzo ya Kipindi Ulichochagua
        period_sales = Sale.objects.filter(**sales_filter)
        total_sales_amount = period_sales.aggregate(total=Sum('total_amount'))['total'] or 0.00
        total_receipts_count = period_sales.count()

        # B. Kagua Haki za Kuona Faida (Permissions Check)
        can_see_profit = (user.role == 'owner') or getattr(business, 'show_profit_to_cashier', False)

        total_profit = 0.00
        if can_see_profit:
            profit_query = SaleItem.objects.filter(**items_filter).annotate(
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
        business = getattr(request.user, 'business', None)
        if not business:
            return Response([], status=status.HTTP_200_OK)

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
        business = getattr(request.user, 'business', None)
        if not business:
            return Response([], status=status.HTTP_200_OK)
        
        top_products = SaleItem.objects.filter(
            sale__business=business
        ).values('product__id', 'product__name').annotate(
            total_quantity_sold=Sum('quantity'),
            total_revenue=Sum('total_price')
        ).order_by('-total_quantity_sold')[:10]  # Top 10

        return Response(list(top_products), status=status.HTTP_200_OK)