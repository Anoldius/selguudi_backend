import uuid
import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model

from rest_framework import status, generics, permissions, serializers
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import (
    RegisterBusinessSerializer, 
    UserProfileSerializer, 
    BillingStatusSerializer,
    VerifySettingsPasswordSerializer,
    SetSettingsPasswordSerializer,
    ResetSettingsPasswordSerializer,
    BusinessPermissionsSerializer,
    CreateCashierSerializer,
    CashierListSerializer
)
from .models import Business, SubscriptionPayment

User = get_user_model()


# ==========================================
# HELPER FUNCTIONS ZA PESAPAL V3 INTEGRATION
# ==========================================

def get_pesapal_base_url():
    """Inarudisha Base URL kulingana na Settings (Live au Sandbox)"""
    return getattr(settings, 'PESAPAL_BASE_URL', 'https://pay.pesapal.com/v3').rstrip('/')

def get_pesapal_token():
    """Omba Bearer Token kutoka PesaPal v3 API"""
    url = f"{get_pesapal_base_url()}/api/Auth/RequestToken"
    payload = {
        "consumer_key": str(getattr(settings, 'PESAPAL_CONSUMER_KEY', '')).strip(),
        "consumer_secret": str(getattr(settings, 'PESAPAL_CONSUMER_SECRET', '')).strip()
    }
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            return response.json().get('token')
        print(f"PesaPal Token Error [{response.status_code}]: {response.text}")
    except Exception as e:
        print(f"PesaPal Token Request Exception: {str(e)}")
    return None


def register_pesapal_ipn(token, ipn_url):
    """Sajili IPN Callback URL kwenye PesaPal kama haijatengenezwa"""
    url = f"{get_pesapal_base_url()}/api/URLSetup/RegisterIPN"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "url": ipn_url,
        "ipn_notification_type": "GET"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=12)
        if response.status_code == 200:
            return response.json().get('ipn_id')
        print(f"PesaPal IPN Reg Error [{response.status_code}]: {response.text}")
    except Exception as e:
        print(f"PesaPal IPN Reg Exception: {str(e)}")
    return None


def submit_pesapal_order(token, order_payload):
    """Tuma Ombi la Kutengeneza Link ya Malipo (Order Request)"""
    url = f"{get_pesapal_base_url()}/api/Transactions/SubmitOrderRequest"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.post(url, json=order_payload, headers=headers, timeout=12)
        if response.status_code == 200:
            return response.json()
        print(f"PesaPal Order Submit Error [{response.status_code}]: {response.text}")
    except Exception as e:
        print(f"PesaPal Order Exception: {str(e)}")
    return None


def get_pesapal_transaction_status(token, order_tracking_id):
    """Kagua Hali ya Muamala (Transaction Status) Kutoka PesaPal V3 API"""
    url = f"{get_pesapal_base_url()}/api/Transactions/GetTransactionStatus?orderTrackingId={order_tracking_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            return response.json()
        print(f"PesaPal Transaction Status Error [{response.status_code}]: {response.text}")
    except Exception as e:
        print(f"PesaPal Transaction Status Exception: {str(e)}")
    return None


# ==========================================
# 1. CUSTOM JWT TOKEN SERIALIZER (BULLETPROOF LOGIN)
# ==========================================

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username', '').strip()
        password = attrs.get('password', '')

        # 1. Tafuta Mtumiaji kwenye Database
        try:
            user_obj = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Username au Password si sahihi."})

        # 2. ZUIA MOJA KWA MOJA KAMA AKAUNTI HAIPO HAI (is_active = False)
        if not getattr(user_obj, 'is_active', True):
            raise serializers.ValidationError({
                "detail": "Akaunti hii imezimwa/imefutwa na Bosi. Hauna ruhusa ya kuingia kwenye mfumo."
            })

        # 3. Hakiki Password
        if not user_obj.check_password(password):
            raise serializers.ValidationError({"detail": "Username au Password si sahihi."})

        # 4. Piga Validation ya Kawaida ya SimpleJWT
        data = super().validate(attrs)

        # 5. Chukua Taarifa za Mtumiaji na Mipangilio kwa Usalama Mkubwa (Safe Fallbacks)
        try:
            business = getattr(self.user, 'business', None)

            data['user_id'] = str(self.user.id)
            data['username'] = self.user.username
            data['role'] = getattr(self.user, 'role', 'owner')
            data['business_id'] = str(business.id) if business else None
            data['business_name'] = business.name if business else None
            data['business_type'] = getattr(business, 'business_type', 'retail') if business else None
            
            if business:
                data['days_left_in_trial'] = getattr(business, 'days_left_in_trial', 30)
                data['has_active_access'] = getattr(business, 'has_active_access', True)
                data['has_settings_password'] = bool(getattr(business, 'settings_password', None))
                data['permissions'] = {
                    'show_profit_to_cashier': getattr(business, 'show_profit_to_cashier', False),
                    'allow_cashier_debts': getattr(business, 'allow_cashier_debts', True),
                    'allow_cashier_custom_price': getattr(business, 'allow_cashier_custom_price', True),
                    'show_buying_price_to_cashier': getattr(business, 'show_buying_price_to_cashier', False),
                    'show_stock_summary_cards': getattr(business, 'show_stock_summary_cards', True),
                }
        except Exception as e:
            print(f"Error appending user login extra data: {e}")

        return data


class LoginRateThrottle(AnonRateThrottle):
    rate = '15/minute'


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class RegisterBusinessView(generics.CreateAPIView):
    queryset = Business.objects.all()
    serializer_class = RegisterBusinessSerializer
    permission_classes = [permissions.AllowAny]


class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UpdateBusinessNameView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request):
        if getattr(request.user, 'role', '') != 'owner':
            return Response({"error": "Bosi pekee ndiye anayeweza kubadilisha jina la duka."}, status=status.HTTP_403_FORBIDDEN)

        business = getattr(request.user, 'business', None)
        if not business:
            return Response({"error": "Duka halijapatikana."}, status=status.HTTP_404_NOT_FOUND)

        new_name = request.data.get('name', '').strip()
        if not new_name:
            return Response({"error": "Jina la duka haliwezi kuwa wazi."}, status=status.HTTP_400_BAD_REQUEST)

        business.name = new_name
        business.save()

        return Response({
            "message": "Jina la duka limebadilishwa kikamilifu!",
            "business_name": business.name
        }, status=status.HTTP_200_OK)


# ==========================================
# 2. BILLING & SUBSCRIPTION VIEWS
# ==========================================

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

        if not business.trial_end_date and business.trial_start_date:
            business.trial_end_date = business.trial_start_date + timedelta(days=30)
            business.save()

        payload = {
            'business_name': business.name,
            'days_left_in_trial': getattr(business, 'days_left_in_trial', 30),
            'has_active_access': getattr(business, 'has_active_access', True),
            'trial_start_date': business.trial_start_date,
            'trial_end_date': business.trial_end_date,
            'subscription_end_date': business.subscription_end_date,
            'monthly_amount': 20000.00
        }

        serializer = BillingStatusSerializer(payload)
        return Response(serializer.data, status=status.HTTP_200_OK)


# ==========================================
# 3. SETTINGS & PASSCODE VIEWS
# ==========================================

class VerifyPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VerifySettingsPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            return Response({
                "success": True, 
                "message": "Nenosiri la Mipangilio limehakikiwa kikamilifu!"
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SetSettingsPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'owner':
            return Response({"error": "Bosi pekee ndiye anayeweza kuweka Nenosiri la Mipangilio."}, status=status.HTTP_403_FORBIDDEN)

        business = getattr(request.user, 'business', None)
        if not business:
            return Response({"error": "Duka halijapatikana."}, status=status.HTTP_404_NOT_FOUND)

        serializer = SetSettingsPasswordSerializer(data=request.data)
        if serializer.is_valid():
            new_pwd = serializer.validated_data['new_settings_password']
            business.set_settings_password(new_pwd)
            business.save()
            return Response({"message": "Nenosiri la Mipangilio limewekwa kikamilifu!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ResetSettingsPasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if getattr(request.user, 'role', '') != 'owner':
            return Response({"error": "Bosi pekee ndiye anayeweza kubadilisha Nenosiri la Mipangilio."}, status=status.HTTP_403_FORBIDDEN)

        business = getattr(request.user, 'business', None)
        if not business:
            return Response({"error": "Duka halijapatikana."}, status=status.HTTP_404_NOT_FOUND)

        serializer = ResetSettingsPasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            new_pwd = serializer.validated_data['new_settings_password']
            business.set_settings_password(new_pwd)
            business.save()
            return Response({"message": "Nenosiri la Mipangilio limebadilishwa kikamilifu!"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class BusinessPermissionsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        business = getattr(request.user, 'business', None)
        if not business:
            return Response({"error": "Duka halijapatikana."}, status=status.HTTP_404_NOT_FOUND)

        serializer = BusinessPermissionsSerializer(business)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        if getattr(request.user, 'role', '') != 'owner':
            return Response({
                "error": "Hauna mamlaka ya kubadilisha mipangilio ya biashara."
            }, status=status.HTTP_403_FORBIDDEN)

        business = getattr(request.user, 'business', None)
        if not business:
            return Response({"error": "Duka halijapatikana."}, status=status.HTTP_404_NOT_FOUND)

        serializer = BusinessPermissionsSerializer(business, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Mipangilio ya duka imehifadhiwa kikamilifu!",
                "data": serializer.data
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ==========================================
# 4. MANAGEMENT YA CASHIERS
# ==========================================

class ManageCashiersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if getattr(request.user, 'role', '') != 'owner':
            return Response({"error": "Bosi pekee ndiye anayeweza kuona orodha ya wafanyakazi."}, status=status.HTTP_403_FORBIDDEN)

        business = getattr(request.user, 'business', None)
        if not business:
            return Response({"error": "Duka halijapatikana."}, status=status.HTTP_404_NOT_FOUND)

        cashiers = User.objects.filter(business=business, role='cashier', is_active=True).order_by('-date_joined')
        serializer = CashierListSerializer(cashiers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if getattr(request.user, 'role', '') != 'owner':
            return Response({"error": "Bosi pekee ndiye anayeweza kusajili mfanyakazi mpya."}, status=status.HTTP_403_FORBIDDEN)

        serializer = CreateCashierSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            cashier = serializer.save()
            return Response({
                "message": f"Mfanyakazi {cashier.username} amesajiliwa kikamilifu!",
                "data": CashierListSerializer(cashier).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteCashierView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        if getattr(request.user, 'role', '') != 'owner':
            return Response({"error": "Bosi pekee ndiye anayeweza kufuta mfanyakazi."}, status=status.HTTP_403_FORBIDDEN)

        business = getattr(request.user, 'business', None)
        try:
            cashier = User.objects.get(id=pk, business=business, role='cashier')
            
            cashier.is_active = False
            cashier.set_unusable_password()
            random_tag = uuid.uuid4().hex[:6]
            cashier.username = f"deleted_{random_tag}_{cashier.username}"
            cashier.save()

            return Response({"message": "Mfanyakazi amefutwa na akaunti yake imefungwa kikamilifu."}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "Mfanyakazi hajapatikana."}, status=status.HTTP_404_NOT_FOUND)


# ==========================================
# 5. PESAPAL INTEGRATION VIEWS
# ==========================================

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
                {"error": "PesaPal Gateway haijarudisha Token. Hakikisha PESAPAL_CONSUMER_KEY na SECRET zipo sahihi kwenye Environment Variables."}, 
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
            ipn_url = getattr(settings, 'PESAPAL_IPN_URL', "https://selguudi-backend.onrender.com/api/auth/billing/pesapal-ipn/")
            try:
                ipn_id = register_pesapal_ipn(token, ipn_url)
            except Exception as e:
                print("IPN Reg Exception:", e)

        user_phone = getattr(request.user, 'phone', None) or getattr(business, 'phone', None) or "0700000000"
        user_email = request.user.email if getattr(request.user, 'email', None) else "info@selguudi.com"
        first_name = getattr(request.user, 'first_name', '') or request.user.username

        order_payload = {
            "id": merchant_ref,
            "currency": "TZS",
            "amount": 20000.00,
            "description": f"Subscription ya Selguudi POS - {business.name[:20]}",
            "callback_url": f"https://selguudi-frontend.vercel.app/billing/success?merchant_ref={merchant_ref}",
            "notification_id": ipn_id if ipn_id else None,
            "billing_address": {
                "email_address": user_email,
                "phone_number": str(user_phone),
                "first_name": first_name,
                "last_name": "Owner"
            }
        }

        pesapal_res = submit_pesapal_order(token, order_payload)

        if pesapal_res and 'redirect_url' in pesapal_res:
            payment.pesapal_order_tracking_id = pesapal_res.get('order_tracking_id')
            payment.save()
            return Response({'redirect_url': pesapal_res['redirect_url']}, status=status.HTTP_200_OK)

        return Response({"error": "PesaPal imekataa kutengeneza Order Link. Hakikisha Credentials za PesaPal ziko sahihi."}, status=status.HTTP_400_BAD_REQUEST)


class PesaPalIPNCallbackView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        pesapal_tracking_id = request.GET.get('OrderTrackingId') or request.GET.get('orderTrackingId')
        merchant_ref = request.GET.get('OrderMerchantReference') or request.GET.get('merchant_ref')

        if not merchant_ref:
            return Response({"status": "FAILED", "detail": "Missing merchant reference"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            payment = SubscriptionPayment.objects.get(merchant_reference=merchant_ref)
        except SubscriptionPayment.DoesNotExist:
            return Response({"status": "FAILED", "detail": "Payment record not found"}, status=status.HTTP_404_NOT_FOUND)

        # KAGUA STATUS YA HAKI KUTOKA PESAPAL KAMA TRACKING ID IPO
        is_payment_verified = False
        if pesapal_tracking_id:
            try:
                token = get_pesapal_token()
                if token:
                    status_res = get_pesapal_transaction_status(token, pesapal_tracking_id)
                    payment_status = None
                    if status_res and isinstance(status_res, dict):
                        payment_status = status_res.get('payment_status_description') or status_res.get('status')

                    if payment_status == 'COMPLETED':
                        is_payment_verified = True
            except Exception as e:
                print(f"Error checking PesaPal Status: {e}")

        # Kama malipo HAIJAKAMILIKA au mtumiaji ame-exit/cancel:
        if not is_payment_verified:
            payment.status = 'FAILED'
            if pesapal_tracking_id:
                payment.pesapal_order_tracking_id = pesapal_tracking_id
            payment.save()
            return Response({
                "status": "FAILED", 
                "message": "Malipo hayajathibitishwa na PesaPal au mchakato ulisitishwa."
            }, status=status.HTTP_400_BAD_REQUEST)

        # KAMA MALIPO YAMETHIBITISHWA NA PESAPAL (COMPLETED):
        payment.status = 'COMPLETED'
        payment.pesapal_order_tracking_id = pesapal_tracking_id
        payment.save()

        business = payment.business
        now = timezone.now()
        start_from = business.subscription_end_date if (business.subscription_end_date and business.subscription_end_date > now) else now

        business.subscription_end_date = start_from + timedelta(days=30)
        business.is_active_subscription = True
        business.save()

        return Response({"status": "SUCCESS", "message": "Subscription updated successfully."}, status=status.HTTP_200_OK)