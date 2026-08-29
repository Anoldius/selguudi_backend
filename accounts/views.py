import uuid
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction

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


# A. CUSTOM JWT TOKEN SERIALIZER (KUZUIA LOGIN KWA DEACTIVATED USERS)
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        # 1. Tafuta Mtumiaji kwenye Database Kwanza
        try:
            user_obj = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            raise serializers.ValidationError({"detail": "Username au Password si sahihi."})

        # 2. ZUIA MOJA KWA MOJA KAMA AKAUNTI HAIPO HAI (is_active = False)
        if not user_obj.is_active:
            raise serializers.ValidationError({
                "detail": "Akaunti hii imezimwa/imefutwa na Bosi. Hauna ruhusa ya kuingia kwenye mfumo."
            })

        # 3. Hakiki Password
        if not user_obj.check_password(password):
            raise serializers.ValidationError({"detail": "Username au Password si sahihi."})

        # 4. Piga Validation ya Kawaida ya SimpleJWT kutengeneza Token
        data = super().validate(attrs)

        # 5. Ongeza Taarifa za Mtumiaji na Mipangilio kwenye Response
        data['user_id'] = str(self.user.id)
        data['username'] = self.user.username
        data['role'] = self.user.role
        data['business_id'] = str(self.user.business.id) if self.user.business else None
        data['business_name'] = self.user.business.name if self.user.business else None
        data['business_type'] = self.user.business.business_type if self.user.business else None
        
        if self.user.business:
            data['days_left_in_trial'] = self.user.business.days_left_in_trial
            data['has_active_access'] = self.user.business.has_active_access
            data['has_settings_password'] = bool(self.user.business.settings_password)
            data['permissions'] = {
                'show_profit_to_cashier': self.user.business.show_profit_to_cashier,
                'allow_cashier_debts': self.user.business.allow_cashier_debts,
                'allow_cashier_custom_price': self.user.business.allow_cashier_custom_price,
                'show_buying_price_to_cashier': self.user.business.show_buying_price_to_cashier,
                'show_stock_summary_cards': self.user.business.show_stock_summary_cards,
            }
            
        return data


class LoginRateThrottle(AnonRateThrottle):
    rate = '10/minute'


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
        if request.user.role != 'owner':
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
        if request.user.role != 'owner':
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
        if request.user.role != 'owner':
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
        if request.user.role != 'owner':
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


class ManageCashiersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != 'owner':
            return Response({"error": "Bosi pekee ndiye anayeweza kuona orodha ya wafanyakazi."}, status=status.HTTP_403_FORBIDDEN)

        business = getattr(request.user, 'business', None)
        if not business:
            return Response({"error": "Duka halijapatikana."}, status=status.HTTP_404_NOT_FOUND)

        # Leta Wafanyakazi WALIO HAI PEEKE (is_active = True)
        cashiers = User.objects.filter(business=business, role='cashier', is_active=True).order_by('-date_joined')
        serializer = CashierListSerializer(cashiers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        if request.user.role != 'owner':
            return Response({"error": "Bosi pekee ndiye anayeweza kusajili mfanyakazi mpya."}, status=status.HTTP_403_FORBIDDEN)

        serializer = CreateCashierSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            cashier = serializer.save()
            return Response({
                "message": f"Mfanyakazi {cashier.username} amesajiliwa kikamilifu!",
                "data": CashierListSerializer(cashier).data
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# J. API YA KUMUONDOA / KUFUTA MFANYAKAZI (FIXED: KUZUIA DB TRANSACTION ROLLBACK)
class DeleteCashierView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        if request.user.role != 'owner':
            return Response({"error": "Bosi pekee ndiye anayeweza kufuta mfanyakazi."}, status=status.HTTP_403_FORBIDDEN)

        business = getattr(request.user, 'business', None)
        try:
            cashier = User.objects.get(id=pk, business=business, role='cashier')
            
            # Hatua ya 1: Haribu credentials zake na kumzima papo hapo
            cashier.is_active = False
            cashier.set_unusable_password()
            random_tag = uuid.uuid4().hex[:6]
            cashier.username = f"deleted_{random_tag}_{cashier.username}"
            cashier.save() # Inahifadhiwa 100% bila rollback

            return Response({"message": "Mfanyakazi amefutwa na akaunti yake imefungwa kikamilifu."}, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({"error": "Mfanyakazi hajapatikana."}, status=status.HTTP_404_NOT_FOUND)


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