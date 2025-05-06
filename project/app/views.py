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
from .models import Product, Cart, CartItem, Order,UserProfile
from django.contrib import auth
from django.utils import timezone
import razorpay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from .models import *
from .models import Address 


client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def index(request):
    products = Product.objects.all().order_by('-id')[:10]
    return render(request, "index.html", {"products": products})
def product(request, id):
    product = get_object_or_404(Product, id=id)
    cart_item_ids = []

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_item_ids = cart.items.values_list('product_id', flat=True)

    # Since you only have one image field, just pass the single image
    additional_images = [product.image] if product.image else []

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

def search_results(request):
    query = request.GET.get('q')
    results = Product.objects.filter(name__icontains=query) if query else Product.objects.all()
    return render(request, 'search.html', {'results': results, 'query': query})

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

def login_view(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']

        user = auth.authenticate(username=username, password=password)
        if user is not None:
            auth.login(request, user)

            if user.is_superuser:
                return redirect('firstpage')
            else:
                return redirect('index')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('login')

    return render(request, 'login.html')

def logout_view(request):
    auth.logout(request)
    return redirect('login')

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

def verify_otp(request):
    if request.method == 'POST':
        entered_otp = request.POST.get('otp')
        if str(request.session.get('otp')) == entered_otp:
            messages.success(request, 'OTP verified. You can now reset your password.')
            return redirect('reset_password')
        else:
            messages.error(request, 'Invalid OTP. Please try again.')

    return render(request, 'verify_otp.html')

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
        product.category = request.POST.get('category')
        product.warranty = request.POST.get('warranty')
        product.description = request.POST.get('description')
        product.stock = request.POST.get('stock')

        # Update the image if provided
        if 'image' in request.FILES:
            product.image = request.FILES['image']

        product.save()
        messages.success(request, 'Product updated successfully!')
        return redirect('firstpage')

    return render(request, 'add.html', {'data1': product})



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
            image=request.FILES.get('image'),  # Only this image field
        )
        messages.success(request, "Product added successfully!")
        return redirect('firstpage')  # Ensure the redirect happens here after success

    # This part handles the GET request to render the form
    return render(request, 'add.html')


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

    cart, created = Cart.objects.get_or_create(user=request.user)

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
        pass
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
    cart_items = CartItem.objects.filter(cart__user=request.user)
    
    total_price = sum(item.product.offerprice * item.quantity if item.product.offerprice else item.product.price * item.quantity for item in cart_items)

    if total_price > 0:
        razorpay_order = client.order.create({
            "amount": int(total_price * 100),
            "currency": "INR",
            "payment_capture": "1"
        })
    else:
        razorpay_order = None

    context = {
        'cart_items': cart_items,
        'items_total': cart_items.count(),
        'total_price': total_price,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_amount': total_price,
        'razorpay_order_id': razorpay_order['id'] if razorpay_order else '',
        'delivery_date': timezone.now() + timezone.timedelta(days=5),
    }
    return render(request, 'checkout.html', context)

@csrf_exempt
def process_checkout(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        phone = request.POST.get('phone')
        pincode = request.POST.get('pincode')
        address = request.POST.get('address')
        address_type = request.POST.get('address_type')
        payment_method = request.POST.get('payment_method')
        razorpay_payment_id = request.POST.get('razorpay_payment_id')

        cart_items = CartItem.objects.filter(user=request.user)
        total_price = sum(item.product.offerprice * item.quantity for item in cart_items)

        order = Order.objects.create(
            user=request.user,
            name=name,
            phone=phone,
            pincode=pincode,
            address=address,
            address_type=address_type,
            payment_method=payment_method,
            total_price=total_price,
            status='Paid' if razorpay_payment_id else 'Pending',
            razorpay_payment_id=razorpay_payment_id
        )

        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.offerprice
            )
            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save()

        cart_items.delete()

        return redirect('order_success')

    return redirect('checkout')

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

def payment_successful(request):
    print("Payment Successful view is called")
    return render(request, 'payment_successful.html')

def order_tracking(request):
    return render(request, 'order_tracking.html')

def track_order(request):
    if request.method == 'POST':
        order_number = request.POST.get('order_number')
        try:
            order = Order.objects.select_related('product', 'user').get(order_number=order_number)
            product = order.product
            context = {
                'order_status': order.status,
                'product': product,
                'order': order,
            }
            return render(request, 'order_tracking.html', {
    'order_status': order.status,
    'order': order,
    'product': order.product,  # assuming order has a ForeignKey to Product
})
        except Order.DoesNotExist:
            return render(request, 'order_tracking.html', {'error': 'Order not found'})
        

@login_required
def user_list(request):
    if not request.user.is_superuser:
        return render(request, 'unauthorized.html')
    users = User.objects.all().order_by('-date_joined')  # <- newest first
    return render(request, 'user_list.html', {'users': users})

def user_detail(request, user_id):
    user_obj = User.objects.get(id=user_id)
    
    # Use the get_or_create_profile method to retrieve or create the profile for the user
    profile = UserProfile.get_or_create_profile(user_obj)
    
    # Retrieve the addresses and orders for the user
    addresses = Address.objects.filter(user=user_obj)
    orders = Order.objects.filter(user=user_obj)

    context = {
        'user_obj': user_obj,
        'profile': profile,
        'addresses': addresses,
        'orders': orders,
    }

    return render(request, 'user_detail.html', context)

@login_required
def delete_user(request, user_id):
    if not request.user.is_superuser:
        return render(request, 'unauthorized.html')

    user = get_object_or_404(User, id=user_id)
    user.delete()
    messages.success(request, "User deleted successfully.")
    return redirect('user_list')    
        

@login_required
def profile_view(request):
    addresses = Address.objects.filter(user=request.user)
    return render(request, 'profile.html', {'addresses': addresses})

@login_required
def add_address(request):
    if request.method == 'POST':
        name = request.POST.get('name', '')
        address = request.POST.get('address', '')
        phone = request.POST.get('phone', '')

        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not address:
            errors['address'] = 'Address is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'

        if not errors:
            Address.objects.create(user=request.user, name=name, address=address, phone=phone)
            messages.success(request, 'Address added successfully!')
            return redirect('profile')
        else:
            return render(request, 'address_form.html', {
                'errors': errors,
                'name': name,
                'address': address,
                'phone': phone,
                'action': 'Add'
            })
    return render(request, 'address_form.html', {
        'action': 'Add',
        'name': '',
        'address': '',
        'phone': '',
        'errors': {}
    })

@login_required
def edit_address(request, address_id):
    address_obj = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '')
        address = request.POST.get('address', '')
        phone = request.POST.get('phone', '')

        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not address:
            errors['address'] = 'Address is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'

        if not errors:
            address_obj.name = name
            address_obj.address = address
            address_obj.phone = phone
            address_obj.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('profile')
        else:
            return render(request, 'address_form.html', {
                'errors': errors,
                'name': name,
                'address': address,
                'phone': phone,
                'action': 'Edit'
            })

    return render(request, 'address_form.html', {
        'name': address_obj.name,
        'address': address_obj.address,
        'phone': address_obj.phone,
        'action': 'Edit',
        'errors': {}
    })

@login_required
def delete_address(request, address_id):
    address_obj = get_object_or_404(Address, id=address_id, user=request.user)
    address_obj.delete()
    messages.success(request, 'Address deleted successfully!')
    return redirect('profile')
@login_required
def edit_email(request):
    """View to edit user's email"""
    user = request.user
    
    if request.method == 'POST':
        email = request.POST.get('email', '')
        
        # Basic validation
        errors = {}
        if not email:
            errors['email'] = 'Email is required.'
        elif '@' not in email:
            errors['email'] = 'Please enter a valid email address.'
            
        if not errors:
            # Update email
            user.email = email
            user.save()
            messages.success(request, 'Email updated successfully!')
            return redirect('profile')
        else:
            # If there are errors, pass them to the template
            return render(request, 'email.html', {
                'errors': errors,
                'email': email
            })
    
    
    return render(request, 'email.html', {
        'email': user.email
    })

@login_required
def edit_username(request):
    """View to edit user's username"""
    user = request.user
    
    if request.method == 'POST':
        username = request.POST.get('username', '')
        
        # Basic validation
        errors = {}
        if not username:
            errors['username'] = 'Username is required.'
        elif len(username) < 4:
            errors['username'] = 'Username should be at least 4 characters long.'
        elif User.objects.filter(username=username).exists():
            errors['username'] = 'This username is already taken.'
            
        if not errors:
            # Update username
            user.username = username
            user.save()
            messages.success(request, 'Username updated successfully!')
            return redirect('profile')
        else:
            # If there are errors, pass them to the template
            return render(request, 'username.html', {
                'errors': errors,
                'username': username
            })
    
    # Pre-fill form with existing username
    return render(request, 'username.html', {
        'username': user.username
    }) 


def order_success(request):
    return render(request, 'order_success.html')


def category(request):
    return render(request, 'category.html')

# def bookings(request):
#     return render(request, 'bookings.html')

def terms(request):
    return render(request, 'terms.html')

def privacy(request):
    return render(request, 'privacy.html')

def contact(request):
    return render(request, 'contact.html')
