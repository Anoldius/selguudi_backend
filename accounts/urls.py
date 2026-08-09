from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import RegisterBusinessView, CustomTokenObtainPairView, UserProfileView

urlpatterns = [
    path('register/', RegisterBusinessView.as_view(), name='register_business'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
]