from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterBusinessView, 
    CustomTokenObtainPairView, 
    UserProfileView,
    BillingStatusView,
    InitiateSubscriptionPaymentView,
    PesaPalIPNCallbackView,
    VerifyPasswordView,
    BusinessPermissionsView
)

urlpatterns = [
    path('register/', RegisterBusinessView.as_view(), name='register_business'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    
    # Security & Business Permissions Endpoints
    path('verify-password/', VerifyPasswordView.as_view(), name='verify_password'),
    path('business-permissions/', BusinessPermissionsView.as_view(), name='business_permissions'),

    # Billing & Subscription Endpoints
    path('billing/status/', BillingStatusView.as_view(), name='billing_status'),
    path('billing/initiate/', InitiateSubscriptionPaymentView.as_view(), name='initiate_payment'),
    path('billing/pesapal-ipn/', PesaPalIPNCallbackView.as_view(), name='pesapal_ipn'),
]