import uuid
from django.db import models
from accounts.models import Business, User
from inventory.models import Product

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