from django.db import models
from django.contrib.auth.models import User

CATEGORY_CHOICES = [
    ('Lighting', 'Lighting'),
    ('Actuators', 'Actuators'),
    ('Touch Switches', 'Touch Switches'),
    ('Security', 'Security'),
]

# Product model
class Product(models.Model):
    name = models.CharField(max_length=255)
    price = models.FloatField()
    offerprice = models.FloatField(blank=True, null=True)
    description = models.TextField()
    category = models.CharField(max_length=100, choices=CATEGORY_CHOICES)
    warranty = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.IntegerField(default=0)
    stock = models.PositiveIntegerField(default=1)
    image = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image1 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image2 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image3 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image4 = models.ImageField(upload_to='product_images/', blank=True, null=True)
    image5 = models.ImageField(upload_to='product_images/', blank=True, null=True)

    def __str__(self):
        return self.name

# Order model
class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    ordered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=100, default="Pending")

    def __str__(self):
        return f"Order by {self.user.username} for {self.product.name}"

# Cart model
class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart for {self.user.username}"

    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())

# CartItem model
class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.product.name}"

    def get_total_price(self):
        return self.product.price * self.quantity

# UserProfile model
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"

    # This function ensures that only one profile per user exists
    @classmethod
    def get_or_create_profile(cls, user):
        # Attempt to get the profile or create it if it doesn't exist
        profile, created = cls.objects.get_or_create(user=user)
        return profile
