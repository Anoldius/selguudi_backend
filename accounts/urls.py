from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    RegisterBusinessView, 
    CustomTokenObtainPairView, 
    UserProfileView,
    UpdateBusinessNameView,
    BillingStatusView,
    InitiateSubscriptionPaymentView,
    PesaPalIPNCallbackView,
    VerifyPasswordView,
    SetSettingsPasswordView,
    ResetSettingsPasswordView,
    BusinessPermissionsView,
    ManageCashiersView,   
    DeleteCashierView     
)

urlpatterns = [
    path('register/', RegisterBusinessView.as_view(), name='register_business'),
    path('login/', CustomTokenObtainPairView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('profile/', UserProfileView.as_view(), name='user_profile'),
    path('update-business-name/', UpdateBusinessNameView.as_view(), name='update_business_name'),
    
    # Security & Business Permissions Endpoints
    path('verify-password/', VerifyPasswordView.as_view(), name='verify_password'),
    path('set-settings-password/', SetSettingsPasswordView.as_view(), name='set_settings_password'),
    path('reset-settings-password/', ResetSettingsPasswordView.as_view(), name='reset_settings_password'),
    path('business-permissions/', BusinessPermissionsView.as_view(), name='business_permissions'),

    # Cashier Management Endpoints (Kusajili na Kufuta Wafanyakazi)
    path('cashiers/', ManageCashiersView.as_view(), name='manage_cashiers'),
    path('cashiers/<str:pk>/', DeleteCashierView.as_view(), name='delete_cashier'),

    # Billing & Subscription Endpoints
    path('billing/status/', BillingStatusView.as_view(), name='billing_status'),
    path('billing/initiate/', InitiateSubscriptionPaymentView.as_view(), name='initiate_payment'),
    path('billing/pesapal-ipn/', PesaPalIPNCallbackView.as_view(), name='pesapal_ipn'),
]