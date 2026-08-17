import uuid
from django.db import models
from accounts.models import Business, User
from inventory.models import Product
from django.conf import settings

class Sale(models.Model):
    PAYMENT_METHODS = (
        ('cash', 'Pesa Taslimu (Cash)'),
        ('mobile_money', 'M-Pesa / TigoPesa / AirtelMoney'),
        ('bank_card', 'Kadi / Benki'),
        ('credit', 'Deni (Credit)'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='sales')
    cashier = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='sales_handled')
    
    receipt_number = models.CharField(max_length=50, unique=True, help_text="Namba ya Risiti")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='cash')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['business', 'created_at']),
            models.Index(fields=['business', 'receipt_number']),
        ]

    def __str__(self):
        return f"Receipt #{self.receipt_number} - {self.total_amount} TZS"


class SaleItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='sale_items')
    
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        # Hesabu total price ya item hii kiotomatiki
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"



class Customer(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def total_debt(self):
        # Inajumlisha salio la madeni yote yanayodaiwa mteja huyu
        debts = self.debts.filter(status__in=['PENDING', 'PARTIAL'])
        return sum(debt.remaining_amount for debt in debts)

    def __str__(self):
        return self.name


class Debt(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Haijalipwa'),
        ('PARTIAL', 'Imelipwa Nusu'),
        ('PAID', 'Imelipwa Yote'),
    )

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='debts')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2) # Thamani ya deni lote
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00) # Kiasi kilicholipwa
    remaining_amount = models.DecimalField(max_digits=12, decimal_places=2) # Salio linalobaki
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING')
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        # Kokotoa salio na badilisha status kiotomatiki
        self.remaining_amount = float(self.total_amount) - float(self.paid_amount)
        
        if self.remaining_amount <= 0:
            self.remaining_amount = 0
            self.status = 'PAID'
        elif self.paid_amount > 0:
            self.status = 'PARTIAL'
        else:
            self.status = 'PENDING'

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Deni la {self.customer.name} - TZS {self.remaining_amount}"


class DebtPaymentHistory(models.Model):
    debt = models.ForeignKey(Debt, on_delete=models.CASCADE, related_name='payment_history')
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2) # Kiasi kilicholipwa mara hii
    notes = models.TextField(blank=True, null=True) # Mfano: "Kalipa kwa M-Pesa"
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Malipo TZS {self.amount_paid} - {self.debt.customer.name}"
