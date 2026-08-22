from django.http import JsonResponse
from django.utils import timezone

class SubscriptionCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Endpoints zilizoruhusiwa kupita hata kama subscription imeisha
        allowed_paths = [
            '/api/auth/login/',
            '/api/auth/register/',
            '/api/auth/billing/status/',
            '/api/auth/billing/initiate/',
            '/api/auth/billing/pesapal-ipn/',
            '/admin/',
        ]

        # Kama njia inaanzia na zilizoruhusiwa, ipite bila kuzuiliwa
        if any(request.path.startswith(path) for path in allowed_paths):
            return self.get_response(request)

        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            business = getattr(user, 'business', None)
            
            if business and hasattr(business, 'has_active_access'):
                if not business.has_active_access:
                    return JsonResponse({
                        'error': 'SUBSCRIPTION_EXPIRED',
                        'message': 'Siku 7 za bure zimeisha. Tafadhali lipia TZS 20,000 ili kuendelea kutumia Selguudi POS.',
                        'amount_due': 20000.00
                    }, status=402) # Status code 402 = Payment Required

        return self.get_response(request)