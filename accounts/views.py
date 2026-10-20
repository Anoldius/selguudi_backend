import uuid
import requests
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

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

        try:
            user_obj = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Username au Password si sahihi."})

        if not getattr(user_obj, 'is_active', True):
            raise serializers.ValidationError({
                "detail": "Akaunti hii imezimwa/imefutwa na Bosi. Hauna ruhusa ya kuingia kwenye mfumo."
            })

        if not user_obj.check_password(password):
            raise serializers.ValidationError({"detail": "Username au Password si sahihi."})

        data = super().validate(attrs)

        try:
            business = getattr(self.user, 'business', None)

            data['user_id'] = str(self.user.id)
            data['username'] = self.user.username
            data['role'] = getattr(self.user, 'role', 'owner')
            data['business_id'] = str(business.id) if business else None
            data['business_name'] = business.name if business else None
            data['business_type'] = getattr(business, 'business_type', 'retail') if business else None
            
            if business:
                # Siku za Trial zimepunguzwa kutoka 30 kuwa 7
                data['days_left_in_trial'] = getattr(business, 'days_left_in_trial', 7)
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

        # Sehemu ya Trial imebadilishwa kuwa siku 7
        if not business.trial_end_date and business.trial_start_date:
            business.trial_end_date = business.trial_start_date + timedelta(days=7)
            business.save()

        # Vuta namba ya simu kutoka kwenye Business au User aliyeingia
        store_phone = getattr(business, 'phone', None) or getattr(user, 'phone', None) or "07XXXXXXXX"

        payload = {
            'business_name': business.name,
            'phone': store_phone,  # <-- Hapa ndipo tunaituma namba kwenda Frontend
            'days_left_in_trial': getattr(business, 'days_left_in_trial', 7),
            'has_active_access': getattr(business, 'has_active_access', True),
            'trial_start_date': business.trial_start_date,
            'trial_end_date': business.trial_end_date,
            'subscription_end_date': business.subscription_end_date,
            'monthly_amount': 20000.00,
            'annual_amount': 200000.00
        }

        return Response(payload, status=status.HTTP_200_OK)


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

        plan = str(request.data.get('plan', 'MONTHLY')).upper()
        
        if plan == 'ANNUAL':
            amount = 200000.0
            plan_label = "Mwaka 1"
        else:
            plan = 'MONTHLY'
            amount = 20000.0
            plan_label = "Mwezi 1"

        merchant_ref = f"SEL-{uuid.uuid4().hex[:8].upper()}"

        token = get_pesapal_token()
        if not token:
            return Response(
                {"error": "PesaPal Token error. Hakikisha Credentials zipo sahihi."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        payment = SubscriptionPayment.objects.create(
            business=business,
            merchant_reference=merchant_ref,
            amount=amount,
            status='PENDING'
        )
        
        if hasattr(payment, 'plan'):
            payment.plan = plan
            payment.save()

        # IPN Notification URL: Tumia Domain Mpya ya Cloudflare badala ya Render URL
        ipn_id = getattr(settings, 'PESAPAL_IPN_ID', '')
        if not ipn_id:
            ipn_url = getattr(settings, 'PESAPAL_IPN_URL', "https://api.selguudi.co.tz/api/auth/billing/pesapal-ipn/")
            try:
                ipn_id = register_pesapal_ipn(token, ipn_url)
            except Exception as e:
                print("IPN Reg Exception:", e)

        user_phone = getattr(request.user, 'phone', None) or getattr(business, 'phone', None) or "0700000000"
        user_email = request.user.email if getattr(request.user, 'email', None) else "info@selguudi.com"
        first_name = getattr(request.user, 'first_name', '') or request.user.username or "Owner"

        order_payload = {
            "id": merchant_ref,
            "currency": "TZS",
            "amount": float(amount),
            "description": f"Subscription Selguudi POS ({plan_label}) - {business.name[:15]}",
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

        return Response({
            "error": f"PesaPal Request Failed: {pesapal_res}"
        }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class PesaPalIPNCallbackView(APIView):
    """
    Endpoint rasmi inayopokea IPN Callback kutoka PesaPal baada ya malipo
    """
    permission_classes = [permissions.AllowAny]

    def process_ipn(self, request):
        pesapal_tracking_id = (
            request.GET.get('OrderTrackingId') or 
            request.GET.get('orderTrackingId') or 
            request.data.get('OrderTrackingId') or 
            request.data.get('orderTrackingId')
        )
        merchant_ref = (
            request.GET.get('OrderMerchantReference') or 
            request.GET.get('merchant_ref') or 
            request.data.get('OrderMerchantReference') or 
            request.data.get('merchant_ref')
        )

        if not merchant_ref and not pesapal_tracking_id:
            return Response({"status": "FAILED", "detail": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        payment = None
        if merchant_ref:
            payment = SubscriptionPayment.objects.filter(merchant_reference=merchant_ref).first()
        if not payment and pesapal_tracking_id:
            payment = SubscriptionPayment.objects.filter(pesapal_order_tracking_id=pesapal_tracking_id).first()

        if not payment:
            return Response({"status": "FAILED", "detail": "Payment record not found"}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == 'COMPLETED':
            return Response({
                "orderNotificationType": "IPNCHANGE",
                "orderTrackingId": pesapal_tracking_id,
                "status": "200"
            }, status=status.HTTP_200_OK)

        is_payment_verified = False
        tracking_id_to_check = pesapal_tracking_id or payment.pesapal_order_tracking_id

        if tracking_id_to_check:
            try:
                token = get_pesapal_token()
                if token:
                    status_res = get_pesapal_transaction_status(token, tracking_id_to_check)
                    payment_status = None
                    if status_res and isinstance(status_res, dict):
                        payment_status = status_res.get('payment_status_description') or status_res.get('status')

                    if payment_status == 'COMPLETED':
                        is_payment_verified = True
            except Exception as e:
                print(f"Error checking PesaPal Status: {e}")

        if not is_payment_verified:
            return Response({
                "status": "PENDING_OR_FAILED", 
                "message": "Malipo bado hayajathibitishwa na PesaPal."
            }, status=status.HTTP_200_OK)

        payment.status = 'COMPLETED'
        if pesapal_tracking_id:
            payment.pesapal_order_tracking_id = pesapal_tracking_id
        payment.save()

        business = payment.business
        now = timezone.now()
        start_from = business.subscription_end_date if (business.subscription_end_date and business.subscription_end_date > now) else now

        paid_amount = float(payment.amount)
        if paid_amount >= 200000.00 or getattr(payment, 'plan', '') == 'ANNUAL':
            duration_days = 365
        else:
            duration_days = 30

        business.subscription_end_date = start_from + timedelta(days=duration_days)
        business.is_active_subscription = True
        business.save()

        return Response({
            "orderNotificationType": "IPNCHANGE",
            "orderTrackingId": tracking_id_to_check,
            "status": "200"
        }, status=status.HTTP_200_OK)

    def get(self, request):
        return self.process_ipn(request)

    def post(self, request):
        return self.process_ipn(request)


class ManualVerifyPaymentView(APIView):
    """
    API Inayoruhusu Frontend/Client Kubonyeza Kitufe cha 'Hakiki Malipo'
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        merchant_ref = request.data.get('merchant_ref')
        
        if not merchant_ref:
            return Response({'error': 'Merchant reference inahitajika'}, status=status.HTTP_400_BAD_REQUEST)

        payment = SubscriptionPayment.objects.filter(merchant_reference=merchant_ref).first()
        if not payment:
            return Response({'error': 'Muamala haujapatikana'}, status=status.HTTP_404_NOT_FOUND)

        if payment.status == 'COMPLETED':
            return Response({'message': 'Malipo tayari yamekamilika na duka ipo Active!'}, status=status.HTTP_200_OK)

        tracking_id = payment.pesapal_order_tracking_id
        if not tracking_id:
            return Response({'error': 'Tracking ID ya PesaPal haijatengenezwa bado.'}, status=status.HTTP_400_BAD_REQUEST)

        token = get_pesapal_token()
        if token:
            status_res = get_pesapal_transaction_status(token, tracking_id)
            payment_status = None
            if status_res and isinstance(status_res, dict):
                payment_status = status_res.get('payment_status_description') or status_res.get('status')

            if payment_status == 'COMPLETED':
                payment.status = 'COMPLETED'
                payment.save()

                business = payment.business
                now = timezone.now()
                start_from = business.subscription_end_date if (business.subscription_end_date and business.subscription_end_date > now) else now

                duration_days = 365 if (float(payment.amount) >= 200000.0 or getattr(payment, 'plan', '') == 'ANNUAL') else 30
                business.subscription_end_date = start_from + timedelta(days=duration_days)
                business.is_active_subscription = True
                business.save()

                return Response({'message': 'Malipo yamethibitishwa na duka limekuwa Active kikamilifu!'}, status=status.HTTP_200_OK)

        return Response({'error': 'Malipo bado hayajakamilika PesaPal. Tafadhali malizia muamala kwenye simu.'}, status=status.HTTP_400_BAD_REQUEST)



        # ==========================================
# 6. SMS GATEWAY WEBHOOK (AUTOMATED SMS LISTENER)
# ==========================================

class SMSWebhookView(APIView):
    """
    Endpoint ya kupokea SMS za malipo kutoka kwenye App ya Android ya SMS Forwarder
    na ku-activate subscription ya Selguudi POS moja kwa moja.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # 1. Kagua Secret Key kwa usalama wa Endpoint
        secret_header = request.headers.get('X-SMS-Secret') or request.data.get('secret')
        expected_secret = getattr(settings, 'SMS_WEBHOOK_SECRET', 'SELGUUDI_SECURE_SMS_KEY_2026')
        
        if secret_header != expected_secret:
            return Response({"error": "Unauthorized: Invalid Secret Key"}, status=status.HTTP_401_UNAUTHORIZED)

        sms_body = request.data.get('message', '') or request.data.get('text', '')
        sender_id = request.data.get('sender', '') or request.data.get('from', '')

        # 2. Hakikisha SMS inatoka kwa Kampuni za Simu halali
        valid_senders = ['M-PESA', 'TIGOPESA', 'TIGO', 'AIRTEL', 'AIRTELMONEY', 'HALOPESA', 'SELCOM']
        if sender_id and not any(valid in sender_id.upper() for valid in valid_senders):
            return Response({"status": "Ignored", "reason": "SMS sio ya muamala wa fedha"}, status=status.HTTP_200_OK)

        if not sms_body:
            return Response({"error": "SMS body iko tupu"}, status=status.HTTP_400_BAD_REQUEST)

        # 3. Vuta Transaction ID, Kiasi, na Namba ya Simu kwa kutumia Regex
        tx_match = re.search(r'\b([A-Z0-9]{8,12})\b', sms_body)
        amount_match = re.search(r'(?:TZS|TSH|TSH\.|Tsh)\s*([\d,]+(?:\.\d{2})?)', sms_body, re.IGNORECASE)
        phone_match = re.search(r'(255\d{9}|0[67]\d{8})', sms_body)

        if not (tx_match and amount_match and phone_match):
            return Response({
                "status": "Ignored", 
                "reason": "Haikuweza kuchukua maelezo ya muamala vizuri kutoka kwenye SMS"
            }, status=status.HTTP_200_OK)

        transaction_id = tx_match.group(1).upper()
        raw_amount = amount_match.group(1).replace(',', '')
        try:
            amount = float(raw_amount)
        except ValueError:
            amount = 0.0

        raw_phone = phone_match.group(1)
        clean_phone = '0' + raw_phone[-9:]

        # 4. Kagua kama Kiasi kilichotumwa kinatimiza angalau gharama ya mwezi (TZS 20,000)
        if amount < 20000:
            return Response({
                "status": "Ignored", 
                "reason": f"Kiasi kilichopokelewa (TZS {amount}) ni chini ya gharama ya mwezi (TZS 20,000)"
            }, status=status.HTTP_200_OK)

        # 5. Tafuta Duka linalohusika kupitia Namba ya Simu
        business = Business.objects.filter(phone__endswith=clean_phone[-9:]).first()
        
        if not business:
            return Response({
                "status": "Ignored", 
                "reason": f"Namba {clean_phone} haijasajiliwa kwenye duka lolote la Selguudi POS"
            }, status=status.HTTP_200_OK)

        # 6. Kuzuia Transaction ID Moja Kutumika Mara Mbili
        if SubscriptionPayment.objects.filter(merchant_reference=transaction_id).exists():
            return Response({
                "status": "Ignored", 
                "reason": f"Muamala {transaction_id} ulishachakatwa tayari"
            }, status=status.HTTP_200_OK)

        # 7. Washa Subscription ya Duka (Auto-Activation)
        now = timezone.now()
        start_from = business.subscription_end_date if (business.subscription_end_date and business.subscription_end_date > now) else now

        # Angalia kama ni ya mwaka au mwezi kutokana na kiasi (Mfano kiasi cha 200k+ ni Annual)
        duration_days = 365 if amount >= 200000.0 else 30

        business.subscription_end_date = start_from + timedelta(days=duration_days)
        business.is_active_subscription = True
        business.save()

        # 8. Hifadhi Kumbukumbu ya Malipo
        SubscriptionPayment.objects.create(
            business=business,
            merchant_reference=transaction_id,
            amount=amount,
            status='COMPLETED',
            payment_method=sender_id or 'MOBILE_MONEY_SMS'
        )

        return Response({
            "status": "Success",
            "message": f"Duka la '{business.name}' limewashwa kikamilifu hadi {business.subscription_end_date.strftime('%Y-%m-%d')}!"
        }, status=status.HTTP_200_OK)