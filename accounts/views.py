from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .serializers import RegisterBusinessSerializer, UserProfileSerializer
from .models import Business

# A. Custom JWT Token Serializer ili kurudisha na taarifa za Business/Role wakati wa Login
class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        # Ongeza data za ziada kwenye Response ya Login
        data['user_id'] = str(self.user.id)
        data['username'] = self.user.username
        data['role'] = self.user.role
        data['business_id'] = str(self.user.business.id) if self.user.business else None
        data['business_name'] = self.user.business.name if self.user.business else None
        data['business_type'] = self.user.business.business_type if self.user.business else None
        return data


# Class ndogo ya ku-limit Login Request
class LoginRateThrottle(AnonRateThrottle):
    rate = '5/minute'


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]

# B. API ya Kujisajili Biashara na Mmiliki
class RegisterBusinessView(generics.CreateAPIView):
    queryset = Business.objects.all()
    serializer_class = RegisterBusinessSerializer
    permission_classes = [permissions.AllowAny] # Inaruhusu mtu yeyote kujisajili


# C. API ya Kuangalia Profile ya Mtumiaji aliye-login
class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)