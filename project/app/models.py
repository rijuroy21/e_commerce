# app/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Lighting', 'Lighting'),
        ('Actuators', 'Actuators'),
        ('Touch Switches', 'Touch Switches'),
        ('Security', 'Security'),
    ]

    name = models.CharField(max_length=255)
    price = models.FloatField()
    offerprice = models.FloatField(blank=True, null=True)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    warranty = models.CharField(max_length=100, blank=True, null=True)
    stock = models.IntegerField()
    image = models.ImageField(upload_to='products/')
    additional_image1 = models.ImageField(upload_to='products/', blank=True, null=True)
    additional_image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    additional_image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    rating = models.FloatField(default=0)
    vector_data = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name
    
class users(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vector_data = models.TextField(null=True)
    
    def __str__(self):
        return self.user.username 

class ViewHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    user = models.ForeignKey(users, on_delete=models.CASCADE)
    
class SearchHistory(models.Model):
    query = models.CharField(max_length=255)
    user = models.ForeignKey(users, on_delete=models.CASCADE)

class reviews(models.Model):
    rating = models.IntegerField()
    description = models.TextField()
    uname = models.ForeignKey(users, on_delete=models.CASCADE)
    pname = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews_set')    

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
        price_to_use = self.product.offerprice if self.product.offerprice is not None else self.product.price
        return price_to_use * self.quantity

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
    STATUS_CHOICES = [
        ('Ordered', 'Ordered'),
        ('Confirmed', 'Confirmed'),
        ('Packed', 'Packed'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),
        ('Returned', 'Returned'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    pincode = models.CharField(max_length=10)
    address = models.TextField()
    address_type = models.CharField(max_length=10)
    payment_method = models.CharField(max_length=20)
    total_price = models.FloatField()
    razorpay_payment_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Ordered')
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