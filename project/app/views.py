from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
import random
from .models import Product, Cart, CartItem, Order
from django.contrib import auth
from django.utils import timezone




# Home Page
def index(request):
    products = Product.objects.all().order_by('-id')[:10]
    return render(request, "index.html", {"products": products})


# Product Detail Page

def product(request, id):
    product = get_object_or_404(Product, id=id)
    cart_item_ids = []

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_item_ids = cart.items.values_list('product_id', flat=True)

    # Get additional images if any
    additional_images = [
        img for img in [
            product.image1,
            product.image2,
            product.image3,
            product.image4,
            product.image5
        ] if img
    ]

    # Get similar products (same category, excluding current)
    similar_products = Product.objects.filter(category=product.category).exclude(id=product.id)

    return render(request, 'product.html', {
        'product': product,
        'cart_item_ids': cart_item_ids,
        'additional_images': additional_images,
        'similar_products': similar_products,
    })

def product_list(request):
    products = Product.objects.all()
    categories = Product.objects.values_list('category', flat=True).distinct()

    category = request.GET.get('category')
    sort = request.GET.get('sort')

    if category:
        products = products.filter(category=category)
    
    if sort == 'newest':
        products = products.order_by('-id')
    elif sort == 'low_to_high':
        products = products.order_by('offerprice')
    elif sort == 'high_to_low':
        products = products.order_by('-offerprice')

    return render(request, 'allproduct.html', {
        'products': products,
        'categories': categories,
    })

# Search
def search_results(request):
    query = request.GET.get('q')
    results = Product.objects.filter(name__icontains=query) if query else Product.objects.all()
    return render(request, 'search.html', {'results': results, 'query': query})



# User Registration View
def register_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        confpassword = request.POST['confpassword']

        if password != confpassword:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')

        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already in use.")
            return redirect('register')

        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()
        messages.success(request, "Registration successful. Please login.")
        return redirect('login')

    return render(request, 'register.html')


# User Login View
def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)

            if user.is_superuser:
                return redirect('firstpage')  # 👈 This matches the URL pattern above
            else:
                return redirect('index')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('login')

    return render(request, 'login.html')


# User Logout View
def logout_view(request):
    auth.logout(request)
    return redirect('login')


# Forgot Password View
def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        otp = random.randint(100000, 999999)

        request.session['reset_email'] = email
        request.session['otp'] = otp

        send_mail(
            subject='Your OTP Code',
            message=f'Your OTP is {otp}',
            from_email='youremail@example.com',
            recipient_list=[email],
            fail_silently=False,
        )

        messages.success(request, 'OTP has been sent to your email.')
        return redirect('verify_otp')

    return render(request, 'forgot_password.html')


# OTP Verification View
def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if str(request.session.get('otp')) == entered_otp:
            messages.success(request, 'OTP verified. You can now reset your password.')
            return redirect('reset_password')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'verify_otp.html')


# Password Reset View
def reset_password(request):
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        email = request.session.get('reset_email')

        user = User.objects.filter(email=email).first()
        if user:
            user.set_password(new_password)
            user.save()
            messages.success(request, "Password has been reset. You can now log in.")
            return redirect('login')
        else:
            messages.error(request, "Something went wrong. Please try again.")
            return redirect('forgot_password')

    return render(request, 'reset_password.html')



# Admin Panel: Product Management
def first_page(request):
    products = Product.objects.all()
    return render(request, 'firstpage.html', {'products': products})


def delete_g(request, id):
    get_object_or_404(Product, pk=id).delete()
    return redirect('firstpage')


def edit_g(request, id):
    product = get_object_or_404(Product, id=id)

    if request.method == 'POST':
        product.name = request.POST.get('name')
        product.price = request.POST.get('price')
        product.offerprice = request.POST.get('offerprice')
        product.offers = request.POST.get('offers')
        product.category = request.POST.get('category')
        product.warranty = request.POST.get('warranty')
        product.description = request.POST.get('description')
        product.stock = request.POST.get('stock')

        for i in range(6):
            field = f'image{i if i else ""}'
            if field in request.FILES:
                setattr(product, field, request.FILES[field])

        product.save()
        messages.success(request, 'Product updated successfully!')
        return redirect('firstpage')

    return render(request, 'add.html', {'data1': product})

# Admin Panel: Add Product

def add_product(request):
    if request.method == 'POST':
        stock = request.POST.get('stock')

        if not stock:
            messages.error(request, "Stock is required.")
            return redirect('add_product_url')

        if int(stock) < 0:
            messages.error(request, "Invalid stock value.")
            return redirect('add_product_url')

        Product.objects.create(
            name=request.POST.get('name'),
            price=request.POST.get('price'),
            offerprice=request.POST.get('offerprice'),
            description=request.POST.get('description'),
            category=request.POST.get('category'),
            warranty=request.POST.get('warranty'),
            stock=stock,
            image=request.FILES.get('image'),
            image1=request.FILES.get('image1'),
            image2=request.FILES.get('image2'),
            image3=request.FILES.get('image3'),
            image4=request.FILES.get('image4'),
            image5=request.FILES.get('image5'),
        )
        messages.success(request, "Product added successfully!")
        return redirect('firstpage')

    return render(request, 'add.html')

# Cart Views
@login_required(login_url='login')
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if product.stock <= 0:
        messages.error(request, "Product is out of stock.")
        return redirect('product', id=product_id)

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if created:
        cart_item.quantity = 1
    else:
        if cart_item.quantity >= product.stock:
            messages.error(request, "Stock limit reached.")
            return redirect('cart_view')
        cart_item.quantity += 1

    cart_item.save()
    product.stock -= 1
    product.save()

    messages.success(request, "Item added to cart.")
    return redirect('cart_view')


@login_required(login_url='login')
def increment_cart(request, id):
    cart_item = get_object_or_404(CartItem, id=id, cart__user=request.user)
    product = cart_item.product

    if product.stock > 0:
        cart_item.quantity += 1
        product.stock -= 1
        cart_item.save()
        product.save()
        messages.success(request, "Quantity updated.")
    else:
        messages.error(request, "No more stock available.")

    return redirect('cart_view')


@login_required(login_url='login')
def decrement_cart(request, id):
    cart_item = get_object_or_404(CartItem, id=id, cart__user=request.user)
    product = cart_item.product

    if cart_item.quantity > 1:
        cart_item.quantity -= 1
        product.stock += 1
        cart_item.save()
        product.save()
        messages.success(request, "Quantity updated.")
    else:
        product.stock += 1
        cart_item.delete()
        product.save()
        messages.success(request, "Item removed from cart.")

    return redirect('cart_view')

@login_required(login_url='login')
def buy_now(request, product_id):
    product = get_object_or_404(Product, pk=product_id)

    # Get or create the user's cart
    cart, created = Cart.objects.get_or_create(user=request.user)

    # Check if product is already in the cart
    item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    if not created:
        item.quantity += 1
        item.save()

    return redirect('checkout')
def remove_from_cart(request, product_id):
    try:
        cart = Cart.objects.get(user=request.user)
        cart_item = get_object_or_404(CartItem, cart=cart, product_id=product_id)
        cart_item.delete()
    except Cart.DoesNotExist:
        pass  # No cart, nothing to delete
    return redirect('checkout') 

@login_required(login_url='login')
def delete_cart_item(request, id):
    cart_item = get_object_or_404(CartItem, id=id, cart__user=request.user)
    cart_item.product.stock += cart_item.quantity
    cart_item.product.save()
    cart_item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart_view')


@login_required(login_url='login')
def cart_view(request):
    cart = Cart.objects.filter(user=request.user).first()
    cart_items = cart.items.all() if cart else []
    total_price = sum(item.get_total_price() for item in cart_items)
    return render(request, 'cart.html', {'cart_items': cart_items, 'total_price': total_price})


@login_required(login_url='login')
def checkout(request):
    # Get the user's cart
    cart = Cart.objects.filter(user=request.user).first()

    # Initialize variables
    cart_items = cart.items.all() if cart else []
    total_price = 0
    items_total = []

    # Calculate total price for each item and accumulate for the total price
    for item in cart_items:
        item_total = item.product.offerprice * item.quantity
        items_total.append({
            'item': item,
            'item_total': item_total
        })
        total_price += item_total
    
    # Calculate the delivery date as 3 days from now
    delivery_date = timezone.now() + timedelta(days=3)

    # Pass cart_items, items_total, total_price, and delivery_date to the template
    return render(request, 'checkout.html', {
        'cart_items': cart_items,
        'items_total': items_total,
        'total_price': total_price,
        'delivery_date': delivery_date
    })

@login_required(login_url='login')
def process_checkout(request):
    if request.method == 'POST':
        address = request.POST.get('address')
        payment_method = request.POST.get('payment_method')

        cart = Cart.objects.filter(user=request.user).first()
        cart_items = cart.items.all() if cart else []
        total_price = sum(item.get_total_price() for item in cart_items)

        order = Order.objects.create(
            user=request.user,
            shipping_address=address,
            payment_method=payment_method,
            total_price=total_price
        )

        cart.items.all().delete()
        messages.success(request, "Order placed successfully!")
        return redirect('order_confirmation', order_id=order.id)
    
    

    return redirect('cart_view')

@login_required(login_url='login')
def update_quantity(request, product_id):
    cart = Cart.objects.get(user=request.user)
    cart_item = CartItem.objects.get(cart=cart, product_id=product_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        product = cart_item.product

        if action == 'increase' and cart_item.quantity < product.stock:
            cart_item.quantity += 1
            product.stock -= 1
            cart_item.save()
            product.save()

        elif action == 'decrease' and cart_item.quantity > 1:
            cart_item.quantity -= 1
            product.stock += 1
            cart_item.save()
            product.save()

    return redirect('checkout')



def order_success(request):
    return render(request, 'order_success.html')

# Static Pages
def category(request):
    return render(request, 'category.html')


def bookings(request):
    return render(request, 'bookings.html')


def terms(request):
    return render(request, 'terms.html')


def privacy(request):
    return render(request, 'privacy.html')


def contact(request):
    return render(request, 'contact.html')