import uuid
from django.db import models
from accounts.models import Business

class Category(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        unique_together = ('business', 'name')

    def __str__(self):
        return f"{self.name} - {self.business.name}"


class Product(models.Model):
    UNITS = (
        ('pcs', 'Pieces / Pack'),
        ('kg', 'Kilograms (Kg)'),
        ('liter', 'Liters (L)'),
        ('plate', 'Plates / Portions'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey(Business, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    
    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=100, blank=True, null=True)
    
    buying_price = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    selling_price = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Tunatumia Decimal (e.g. 0.50 kg ya bucha au mchezo wa mche)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    unit = models.CharField(max_length=20, choices=UNITS, default='pcs')
    
    min_stock_alert = models.DecimalField(max_digits=10, decimal_places=2, default=5.00)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('business', 'barcode')
        indexes = [
            models.Index(fields=['business', 'barcode']),
            models.Index(fields=['business', 'name']),
            models.Index(fields=['business', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.business.name})"