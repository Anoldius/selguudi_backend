from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Business

User = get_user_model()

# 1. Serializer ya Kuandikisha Biashara Mpya pamoja na Mmiliki wake
class RegisterBusinessSerializer(serializers.ModelSerializer):
    # Field za ziada za Mmiliki (Owner)
    owner_username = serializers.CharField(write_only=True)
    owner_email = serializers.EmailField(write_only=True, required=True) 
    owner_password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    owner_full_name = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Business
        fields = [
            'id', 'name', 'business_type', 'phone', 'address',
            'owner_username', 'owner_email', 'owner_password', 'owner_full_name'
        ]

    def create(self, validated_data):
        # Tenga data za owner na za business
        owner_username = validated_data.pop('owner_username')
        owner_email = validated_data.pop('owner_email')
        owner_password = validated_data.pop('owner_password')
        owner_full_name = validated_data.pop('owner_full_name', '')

        # A. Tengeneza Business kwanza
        business = Business.objects.create(**validated_data)

        # B. Tengeneza Owner User aliyeunganishwa na hii Business
        user = User.objects.create_user(
            username=owner_username,
            email=owner_email, # <--- Inahifadhiwa kwenye User Model ya Django hapa
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