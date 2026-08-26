import uuid
from django.db import models, connection
from accounts.models import Business

# Auto-setup ya Table & Columns kuzuia DB errors Render
def ensure_category_table():
    with connection.cursor() as cursor:
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS inventory_category (
                    id UUID PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    business_id UUID REFERENCES accounts_business(id) ON DELETE CASCADE,
                    CONSTRAINT inventory_category_business_id_name_key UNIQUE (business_id, name)
                );
            """)
            cursor.execute("""
                ALTER TABLE inventory_product 
                ADD COLUMN IF NOT EXISTS category_id UUID REFERENCES inventory_category(id) ON DELETE SET NULL;
            """)
        except Exception as e:
            print("Category DB Setup Note:", e)

ensure_category_table()


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