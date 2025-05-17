from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

CATEGORY_CHOICES = [
    ('Lighting', 'Lighting'),
    ('Actuators', 'Actuators'),
    ('Touch Switches', 'Touch Switches'),
    ('Security', 'Security'),
]

class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    offerprice = models.FloatField(blank=True, null=True)
    description = models.TextField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    warranty = models.CharField(max_length=100, blank=True, null=True)
    stock = models.PositiveIntegerField(default=1)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)  

    def __str__(self):
        return self.name

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

    def get_total_price(self):
        return self.product.price * self.quantity

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    @classmethod
    def get_or_create_profile(cls, user):
        profile, created = cls.objects.get_or_create(user=user)
        return profile

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=225)
    address = models.TextField()
    pincode = models.CharField(max_length=6)
    phone = models.CharField(max_length=12)
    is_default = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.address[:30]}"

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    pincode = models.CharField(max_length=10)
    address = models.TextField()
    address_type = models.CharField(max_length=50, blank=True, null=True)
    payment_method = models.CharField(max_length=20)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, default='Pending')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order #{self.id} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"