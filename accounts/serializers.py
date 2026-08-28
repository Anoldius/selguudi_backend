import re
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Business, SubscriptionPayment

User = get_user_model()


# 0. FUNCTION YA KUHAKIKI STRONG PASSWORD (COMPLEXITY CHECK)
def validate_strong_password(value):
    if len(value) < 8:
        raise serializers.ValidationError("Nenosiri lazima liwe na angalau herufi 8 au zaidi.")
    if not re.search(r'[A-Z]', value):
        raise serializers.ValidationError("Nenosiri lazima liwe na angalau herufi kubwa moja (A-Z).")
    if not re.search(r'[a-z]', value):
        raise serializers.ValidationError("Nenosiri lazima liwe na angalau herufi ndogo moja (a-z).")
    if not re.search(r'[0-9]', value):
        raise serializers.ValidationError("Nenosiri lazima liwe na angalau namba moja (0-9).")
    if not re.search(r'[@$!%*?&_#^()-+={}]', value):
        raise serializers.ValidationError("Nenosiri lazima liwe na angalau alama maalum (mfano: @, #, $, %, !).")
    return value


# 1. Serializer ya Kuandikisha Biashara Mpya pamoja na Mmiliki wake
class RegisterBusinessSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(write_only=True)
    owner_email = serializers.EmailField(write_only=True, required=False, allow_blank=True) 
    owner_password = serializers.CharField(write_only=True, style={'input_type': 'password'}, validators=[validate_strong_password])
    owner_full_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Business
        fields = [
            'id', 'name', 'business_type', 'phone', 'address',
            'owner_username', 'owner_email', 'owner_password', 'owner_full_name'
        ]

    def validate_owner_username(self, value):
        # Username pekee ndiyo inapaswa kuwa Unique!
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("Username hii tayari inatumiwa. Tafadhali chagua username nyingine.")
        return value

    def create(self, validated_data):
        owner_username = validated_data.pop('owner_username')
        owner_email = validated_data.pop('owner_email', '')
        owner_password = validated_data.pop('owner_password')
        owner_full_name = validated_data.pop('owner_full_name', '')

        # A. Tengeneza Business
        business = Business.objects.create(**validated_data)

        # B. Tengeneza Owner User
        user = User.objects.create_user(
            username=owner_username,
            email=owner_email,
            password=owner_password,
            first_name=owner_full_name,
            business=business,
            role='owner',
            phone=business.phone
        )

        return business


# 2. Serializer ya Kuonyesha Profile ya User aliye-login
class UserProfileSerializer(serializers.ModelSerializer):
    business_name = serializers.ReadOnlyField(source='business.name')
    business_type = serializers.ReadOnlyField(source='business.business_type')

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'role', 'phone', 'business', 'business_name', 'business_type']


# 3. Serializer ya Hali ya Billing & Trial
class BillingStatusSerializer(serializers.Serializer):
    business_name = serializers.CharField()
    days_left_in_trial = serializers.IntegerField()
    has_active_access = serializers.BooleanField()
    trial_start_date = serializers.DateTimeField()
    trial_end_date = serializers.DateTimeField()
    subscription_end_date = serializers.DateTimeField(allow_null=True)
    monthly_amount = serializers.DecimalField(max_digits=10, decimal_places=2)


# 4. SERIALIZER YA KUHAKIKI PASSWORD (VERIFY PASSWORD BEFORE SETTINGS ENTRY)
class VerifyPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True)

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Nenosiri uliloingiza si sahihi. Imeshindikana kufungua Mipangilio.")
        return value


# 5. SERIALIZER YA CUSHANGE/READ BUSINESS PERMISSIONS TOGGLES
class BusinessPermissionsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = [
            'show_profit_to_cashier',
            'allow_cashier_debts',
            'allow_cashier_custom_price',
            'show_buying_price_to_cashier'
        ]