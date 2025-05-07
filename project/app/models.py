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


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)  
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('Placed', 'Placed'), ('Confirmed', 'Confirmed'), ('Shipped', 'Shipped'), ('Delivered', 'Delivered')],
        default='Placed'
    )
    delivery_date = models.DateField(default=timezone.localdate)  

    def __str__(self):
        return f"Order by {self.user.username} for {self.product.name}"
    

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
        # Get or create the profile for the user
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

