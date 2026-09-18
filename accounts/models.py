import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from datetime import timedelta

class Business(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    business_type = models.CharField(max_length=50, default='retail')
    
    # phone ikiwa bila unique=True kuruhusu namba moja kusimamia maduka mengi
    phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)  
    created_at = models.DateTimeField(auto_now_add=True)

    # Subscription & Trial Details
    trial_start_date = models.DateTimeField(default=timezone.now)
    trial_end_date = models.DateTimeField(blank=True, null=True)
    subscription_end_date = models.DateTimeField(blank=True, null=True)
    is_active_subscription = models.BooleanField(default=True)

    # MIPANGILIO YA HAKI ZA CASHIER (BUSINESS PERMISSIONS TOGGLES)
    show_profit_to_cashier = models.BooleanField(default=False)
    allow_cashier_debts = models.BooleanField(default=True)
    allow_cashier_custom_price = models.BooleanField(default=True)
    show_buying_price_to_cashier = models.BooleanField(default=False)
    show_stock_summary_cards = models.BooleanField(default=False)  # <--- FIELD MPYA HAPA

    # NENOSIRI MAALUM LA SETTINGS (SETTINGS PASSCODE - HASHED)
    settings_password = models.CharField(max_length=128, blank=True, null=True)

    def set_settings_password(self, raw_password):
        """Inahifadhi password ya settings ikiwa hashed"""
        self.settings_password = make_password(raw_password)

    def check_settings_password(self, raw_password):
        """Inahakiki kama password iliyoingizwa ni sahihi"""
        if not self.settings_password:
            return False
        return check_password(raw_password, self.settings_password)

    def save(self, *args, **kwargs):
        if not self.trial_end_date:
            # Weka siku 30 za trial wakati wa usajili
            self.trial_end_date = self.trial_start_date + timedelta(days=30)
        super().save(*args, **kwargs)

    @property
    def days_left_in_trial(self):
        """Inarudisha idadi ya siku halisi zilizobaki za trial kuanzia leo"""
        if not self.trial_end_date:
            return 0
            
        now = timezone.now()
        
        # Kama ameshalipia subscription na haijaisha, trial countdown haina maana tena
        if self.subscription_end_date and self.subscription_end_date > now:
            return 0
            
        if now >= self.trial_end_date:
            return 0
            
        time_left = self.trial_end_date - now
        return time_left.days + (1 if time_left.seconds > 0 else 0)

    @property
    def has_active_access(self):
        """Inakagua kama bado yupo kwenye Trial au amelipia Subscription"""
        now = timezone.now()

        # 1. Bado yupo ndani ya Siku 30 za trial
        if self.trial_end_date and now <= self.trial_end_date:
            return True

        # 2. Amelipia na tarehe ya subscription haijaisha
        if self.subscription_end_date and now <= self.subscription_end_date:
            return True

        return False

    def __str__(self):
        return self.name


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    role = models.CharField(max_length=20, default='cashier')
    phone = models.CharField(max_length=20, blank=True, null=True)


class SubscriptionPayment(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='payments')
    merchant_reference = models.CharField(max_length=100, unique=True)
    pesapal_order_tracking_id = models.CharField(max_length=100, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=20000.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)  # <--- Hapa ilikuwa imeandikwa auto_auto_add
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.business.name} - {self.amount} TZS ({self.status})"