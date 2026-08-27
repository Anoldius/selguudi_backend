import uuid
from datetime import timedelta
from django.utils import timezone
from django.conf import settings

from rest_framework import status, generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import (
    RegisterBusinessSerializer, 
    UserProfileSerializer, 
    BillingStatusSerializer
)
from .models import Business, SubscriptionPayment
from .pesapal import get_pesapal_token, submit_pesapal_order, register_pesapal_ipn

# A. Custom JWT Token Serializer ya Login inayotumia Username na Password
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        data = super().validate(attrs)
        
        # Taarifa za mtumiaji na biashara anayoimiliki/anayoifanyia kazi
        data['user_id'] = str(self.user.id)
        data['username'] = self.user.username
        data['role'] = self.user.role
        data['business_id'] = str(self.user.business.id) if self.user.business else None
        data['business_name'] = self.user.business.name if self.user.business else None
        data['business_type'] = self.user.business.business_type if self.user.business else None
        
        # Siku zilizobaki na Hali ya Trial
        if self.user.business:
            data['days_left_in_trial'] = self.user.business.days_left_in_trial
            data['has_active_access'] = self.user.business.has_active_access
            
        return data


# Class ndogo ya ku-limit Login Request kwa sekunde/dakika
class LoginRateThrottle(AnonRateThrottle):
    rate = '10/minute'


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


# B. API ya Kujisajili Biashara na Mmiliki
class RegisterBusinessView(generics.CreateAPIView):
    queryset = Business.objects.all()
    serializer_class = RegisterBusinessSerializer
    permission_classes = [permissions.AllowAny]


# C. API ya Kuangalia Profile ya Mtumiaji aliye-login
class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


# D. API ya Kuangalia Hali ya Billing & Trial
class BillingStatusView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        business = getattr(user, 'business', None)

        if not business:
            return Response(
                {"error": "Hauna duka lililounganishwa na akaunti hii."}, 
                status=status.HTTP_404_NOT_FOUND
            )

        if not business.subscription_end_date and business.trial_start_date:
            expected_trial_end = business.trial_start_date + timedelta(days=30)
            if business.trial_end_date != expected_trial_end:
                business.trial_end_date = expected_trial_end
                business.save()

        payload = {
            'business_name': business.name,
            'days_left_in_trial': business.days_left_in_trial,
            'has_active_access': business.has_active_access,
            'trial_start_date': business.trial_start_date,
            'trial_end_date': business.trial_end_date,
            'subscription_end_date': business.subscription_end_date,
            'monthly_amount': 20000.00
        }

        serializer = BillingStatusSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


# E. API ya Kuanzisha Malipo ya PesaPal
class InitiateSubscriptionPaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        business = getattr(request.user, 'business', None)
        if not business:
            return Response({"error": "Duka halijapatikana."}, status=status.HTTP_404_NOT_FOUND)

        merchant_ref = f"SEL-{uuid.uuid4().hex[:8].upper()}"

        token = get_pesapal_token()
        if not token:
            return Response(
                {"error": "PesaPal Gateway haijarudisha Token. Hakikisha Credentials zipo sahihi."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        payment = SubscriptionPayment.objects.create(
            business=business,
            merchant_reference=merchant_ref,
            amount=20000.00,
            status='PENDING'
        )

        ipn_id = getattr(settings, 'PESAPAL_IPN_ID', '')
        if not ipn_id:
            ipn_url = "https://selguudi-backend.onrender.com/api/auth/billing/pesapal-ipn/"
            ipn_id = register_pesapal_ipn(token, ipn_url) or "e86d2524-1111-2222-3333-444455556666"

        order_payload = {
            "id": merchant_ref,
            "currency": "TZS",
            "amount": 20000.00,
            "description": f"Subscription ya Selguudi POS - {business.name[:20]}",
            "callback_url": f"https://selguudi-frontend.vercel.app/billing/success?merchant_ref={merchant_ref}",
            "notification_id": ipn_id if ipn_id else None,
            "billing_address": {
                "email_address": request.user.email if request.user.email else "info@selguudi.com",
                "phone_number": request.user.phone if request.user.phone else "0700000000",
                "first_name": request.user.first_name if request.user.first_name else business.name,
                "last_name": "Owner"
            }
        }

        pesapal_res = submit_pesapal_order(token, order_payload)

        if pesapal_res and 'redirect_url' in pesapal_res:
            payment.pesapal_order_tracking_id = pesapal_res.get('order_tracking_id')
            payment.save()
            return Response({'redirect_url': pesapal_res['redirect_url']}, status=status.HTTP_200_OK)

        return Response({"error": "PesaPal imekataa kutengeneza Order Link."}, status=status.HTTP_400_BAD_REQUEST)


# F. API ya Ku-handle PesaPal IPN Notification Callback
class PesaPalIPNCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        pesapal_tracking_id = request.GET.get('OrderTrackingId')
        merchant_ref = request.GET.get('OrderMerchantReference')

        if merchant_ref:
            try:
                payment = SubscriptionPayment.objects.get(merchant_reference=merchant_ref)
                payment.status = 'COMPLETED'
                payment.pesapal_order_tracking_id = pesapal_tracking_id
                payment.save()

                business = payment.business
                now = timezone.now()
                start_from = business.subscription_end_date if (business.subscription_end_date and business.subscription_end_date > now) else now

                business.subscription_end_date = start_from + timedelta(days=30)
                business.is_active_subscription = True
                business.save()

                return Response({"status": "SUCCESS", "message": "Subscription updated successfully."})
            except SubscriptionPayment.DoesNotExist:
                pass

        return Response({"status": "FAILED"}, status=status.HTTP_400_BAD_REQUEST)