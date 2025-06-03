from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
import re
import random
import json
import pandas as pd
import numpy as np
from django.contrib import auth
from django.utils import timezone
import razorpay
from django.views.decorators.csrf import csrf_exempt
from razorpay.errors import BadRequestError, ServerError, GatewayError
from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Address, users, ViewHistory, SearchHistory, reviews
from .vectorize import get_recommendations, combine_user_with_search_and_views, vectorize_product_with_reviews, vectorize_single_user

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


def update_product_vector(product):
    try:
        comments = [review.description for review in product.reviews_set.all()]
        pro_data = [{
            "pro_id": product.id,
            "name": product.name,
            "rating": product.rating,
            "type": product.category,  # Changed 'type' to 'category' to match Product model
            "description": product.description,
            "reviews": ','.join(comments)
        }]
        df = pd.DataFrame(pro_data)
        product_vector = vectorize_product_with_reviews(df)
        if product_vector is not None and len(product_vector) > 0:
            product.vector_data = json.dumps(product_vector[0].tolist())
        else:
            product.vector_data = json.dumps([])
        product.save()
    except Exception as e:
        print(f"Error during product vectorization: {str(e)}")
        product.vector_data = json.dumps([])
        product.save()
def product(request, id):
    product = get_object_or_404(Product, id=id)
    cart_item_ids = []
    product_reviews = product.reviews_set.all()  # Fetch reviews using reviews_set
    print(f"Reviews for product {product.id}: {product_reviews.count()}")  # Debug

    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
        if cart:
            cart_item_ids = cart.items.values_list('product_id', flat=True)
        
        # Save to view history
        try:
            user_obj = users.objects.get(user=request.user)
            ViewHistory.objects.create(user=user_obj, product=product)
            vectorize_single_user(request.user)
        except users.DoesNotExist:
            user_obj = users.objects.create(user=request.user)
            ViewHistory.objects.create(user=user_obj, product=product)
            vectorize_single_user(request.user)

        # Handle review submission
        if request.method == 'POST':
            rating = request.POST.get('rating')
            description = request.POST.get('description')
            
            if not rating or not description:
                messages.error(request, "Please provide both rating and description.", extra_tags='review')
            else:
                try:
                    rating = int(rating)
                    if rating < 1 or rating > 5:
                        messages.error(request, "Rating must be between 1 and 5.", extra_tags='review')
                    else:
                        # Create review
                        new_review = reviews.objects.create(
                            pname=product,
                            uname=user_obj,
                            rating=rating,
                            description=description
                        )
                        print(f"Created review ID {new_review.id} for product {product.id}")  # Debug
                        
                        # Update product rating
                        total_reviews = product.reviews_set.all()
                        total_rating = sum(review.rating for review in total_reviews)
                        product.rating = round(total_rating / len(total_reviews), 1) if total_reviews else rating
                        product.save()
                        
                        # Update product vector
                        update_product_vector(product)
                        
                        messages.success(request, "Review added successfully!", extra_tags='review')
                        return redirect('product', id=product.id)
                except ValueError:
                    messages.error(request, "Invalid rating value.", extra_tags='review')
                except Exception as e:
                    messages.error(request, f"Error adding review: {str(e)}", extra_tags='review')
                    print(f"Review creation error: {str(e)}")  # Debug

    additional_images = [
        img for img in [product.image, product.additional_image1, product.additional_image2, product.additional_image3] if img
    ]
    similar_products = Product.objects.filter(category=product.category).exclude(id=product.id)

    return render(request, 'product.html', {
        'product': product,
        'cart_item_ids': cart_item_ids,
        'additional_images': additional_images,
        'similar_products': similar_products,
        'reviews': product_reviews,  # Pass reviews as product_reviews
    })


def index(request):
    products = Product.objects.all().order_by('-id')[:8]
    recommended_products = []
    if request.user.is_authenticated:
        recommended_products = get_recommendations(request.user, top_n=4)
    if not recommended_products:
        recommended_products = Product.objects.order_by('?')[:4]
    return render(request, "index.html", {
        "products": products,
        "recommended_products": recommended_products
    })


@login_required(login_url='login')
def recommendations(request):
    recommended_products = get_recommendations(request.user, top_n=5)
    return render(request, 'recommendations.html', {'recommended_products': recommended_products})


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
    
    if query and request.user.is_authenticated:
        try:
            user_obj = users.objects.get(user=request.user)
            SearchHistory.objects.create(user=user_obj, query=query)
            vectorize_single_user(request.user)
        except users.DoesNotExist:
            user_obj = users.objects.create(user=request.user)
            SearchHistory.objects.create(user=user_obj, query=query)
            vectorize_single_user(request.user)
    
    return render(request, 'search.html', {'results': results, 'query': query})



def is_valid_password(password):
    return (
        len(password) >= 8 and
        re.search(r"[A-Z]", password) and
        re.search(r"\d", password) and
        re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    )

def register_view(request):
    if request.method == 'POST':
        username = request.POST['username'].strip()
        email = request.POST['email'].strip()
        password = request.POST['password']
        confpassword = request.POST['confpassword']

        # Check if passwords match
        if password != confpassword:
            messages.error(request, "Passwords do not match.")
            return redirect('register')

        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, "Invalid email format.")
            return redirect('register')

        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('register')

        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already in use.")
            return redirect('register')

        # Validate password strength
        if not is_valid_password(password):
            messages.error(
                request,
                "Password must be at least 8 characters long, contain an uppercase letter, a number, and a special character."
            )
            return redirect('register')

        # Create user
        user = User.objects.create_user(username=username, email=email, password=password)
        user.save()

        user_profile = users.objects.create(user=user)
        user_vector = combine_user_with_search_and_views(user_profile)
        user_profile.vector_data = json.dumps(user_vector.tolist())
        user_profile.save()

        messages.success(request, "Registration successful. Please login.")
        return redirect('login')

    # Clear messages for GET request
    messages.get_messages(request).used = True
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

        # Update images if provided
        if 'image' in request.FILES:
            product.image = request.FILES['image']
        if 'additional_image1' in request.FILES:
            product.additional_image1 = request.FILES['additional_image1']
        if 'additional_image2' in request.FILES:
            product.additional_image2 = request.FILES['additional_image2']
        if 'additional_image3' in request.FILES:
            product.additional_image3 = request.FILES['additional_image3']

        product.save()
        messages.success(request, 'Product updated successfully!')
        return redirect('firstpage')

    return render(request, 'add.html', {'data1': product})


@login_required(login_url='login')
def add_product(request):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('login')

    if request.method == 'POST':
        name = request.POST.get('name')
        price = request.POST.get('price')
        offerprice = request.POST.get('offerprice')
        description = request.POST.get('description')
        category = request.POST.get('category')
        warranty = request.POST.get('warranty')
        stock = request.POST.get('stock')
        image = request.FILES.get('image')
        additional_image1 = request.FILES.get('additional_image1')
        additional_image2 = request.FILES.get('additional_image2')
        additional_image3 = request.FILES.get('additional_image3')

        if not all([name, price, description, category, stock]):
            messages.error(request, "Please fill in all required fields.")
            return render(request, 'add.html', {
                'name': name,
                'price': price,
                'offerprice': offerprice,
                'description': description,
                'category': category,
                'warranty': warranty,
                'stock': stock,
            })

        try:
            price = float(price)
            offerprice = float(offerprice) if offerprice else None
            stock = int(stock)
            if stock < 0:
                raise ValueError("Stock cannot be negative.")
        except ValueError:
            messages.error(request, "Invalid price or stock value.")
            return render(request, 'add.html', {
                'name': name,
                'price': price,
                'offerprice': offerprice,
                'description': description,
                'category': category,
                'warranty': warranty,
                'stock': stock,
            })

        product = Product.objects.create(
            name=name,
            price=price,
            offerprice=offerprice,
            description=description,
            category=category,
            warranty=warranty,
            stock=stock,
            image=image,
            additional_image1=additional_image1,
            additional_image2=additional_image2,
            additional_image3=additional_image3,
            rating=0,
        )

        # Add error handling for vectorization
        try:
            pro_data = [{
                "pro_id": product.id,
                "name": product.name,
                "rating": product.rating,
                "type": product.category,
                "description": product.description,
                "reviews": ''
            }]
            df = pd.DataFrame(pro_data)
            product_vector = vectorize_product_with_reviews(df)
            
            # Check if product_vector is not empty and has valid data
            if product_vector is not None and len(product_vector) > 0:
                product.vector_data = json.dumps(product_vector[0].tolist())
                product.save()
            else:
                # Handle case where vectorization fails
                print(f"Warning: Vectorization failed for product {product.id}")
                # You might want to set a default vector or leave it empty
                product.vector_data = json.dumps([])
                product.save()
                
        except Exception as e:
            # Log the error and continue without crashing
            print(f"Error during product vectorization: {str(e)}")
            # Set empty vector data as fallback
            product.vector_data = json.dumps([])
            product.save()

        messages.success(request, "Product added successfully!")
        return redirect('firstpage')

    return render(request, 'add.html', {
        'categories': Product.CATEGORY_CHOICES,
    })



# def addReview(request,pk):
#     if request.method == 'POST':
#         rating=request.POST['rating']
#         description=request.POST['description']
#         prod=product.objects.get(pk=pk)
        
#         user=users.objects.get(username=request.session['user'])
#         data=reviews.objects.create(rating=rating,description=description,uname=user,pname=prod)
#         data.save()
#         rev = reviews.objects.filter(pname=prod)
#         total = [i.rating for i in rev] 
#         if len(total) != 0:
#             total_rating = round(sum(total) / len(total), 1)
#             prod.rating = total_rating
#         else:
#             prod.rating = rating
#         prod.save()
#         comments = [i.description for i in rev]
#         pro_data = [{
#                 "pro_id": prod.id,
#                 "name": prod.name,
#                 "rating": prod.rating,
#                 "type":prod.type,
#                 "description": prod.description,
#                 "reviews": ','.join(comments)
#             }]
#         df = pd.DataFrame(pro_data)
#         product_vector = vectorize_product_with_reviews(df)
#         print('pro',product_vector)
#         prod.vector_data = json.dumps(product_vector[0].tolist())
#         prod.save()
#         return redirect(reverse('products', args=[pk]))
#     else:
#         return redirect(addReview)
    

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
    messages.success(request, 'Item removed.')
    return redirect('checkout') 

# views.py (updated cart_view)
@login_required(login_url='login')
def cart_view(request):
    cart = Cart.objects.filter(user=request.user).first()
    cart_items = cart.items.all() if cart else []
    total_price = sum(item.get_total_price() for item in cart_items)  # Now uses offerprice
    # Prepare cart items with subtotals for the template
    cart_items_with_subtotals = [
        {'item': item, 'subtotal': item.get_total_price()}
        for item in cart_items
    ]
    return render(request, 'cart.html', {
        'cart_items_with_subtotals': cart_items_with_subtotals,
        'total_price': total_price
    })



@login_required(login_url='login')
def checkout(request):
    cart_items = CartItem.objects.filter(cart__user=request.user)
    addresses = Address.objects.filter(user=request.user)

    total_price = sum(
        item.product.offerprice * item.quantity if item.product.offerprice
        else item.product.price * item.quantity
        for item in cart_items
    )

    if total_price <= 0:
        messages.error(request, "Invalid cart total. Please check your cart and try again.")
        return redirect('cart_view')

    razorpay_order = None
    if total_price > 0:
        try:
            razorpay_order = client.order.create({
                "amount": int(total_price * 100),
                "currency": "INR",
                "payment_capture": "1"
            })
        except BadRequestError:
            messages.error(request, "Invalid request to payment gateway. Please try again later.")
            return redirect('cart_view')
        except ServerError:
            messages.error(request, "Payment gateway server error. Please try again later.")
            return redirect('cart_view')
        except GatewayError:
            messages.error(request, "Payment gateway error. Please try again later.")
            return redirect('cart_view')
        except Exception:
            messages.error(request, "An unexpected error occurred. Please try again later.")
            return redirect('cart_view')

    context = {
        'cart_items': cart_items,
        'items_total': cart_items.count(),
        'total_price': total_price,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'razorpay_amount': total_price,
        'razorpay_order_id': razorpay_order['id'] if razorpay_order else '',
        'delivery_date': timezone.now() + timezone.timedelta(days=5),
        'addresses': addresses,
    }
    return render(request, 'checkout.html', context)
@csrf_exempt
@login_required(login_url='login')
def process_checkout(request):
    if request.method == 'POST':
        address_id = request.POST.get('billing_address')
        payment_method = request.POST.get('payment_method')
        razorpay_payment_id = request.POST.get('razorpay_payment_id', '')
        cart_items = CartItem.objects.filter(cart__user=request.user)
        
        if not cart_items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('cart_view')
        
        if not address_id:
            messages.error(request, 'Please select a billing address.')
            return redirect('checkout')

        # Validate stock
        for cart_item in cart_items:
            if cart_item.product.stock < cart_item.quantity:
                messages.error(request, f'Insufficient stock for {cart_item.product.name}. Only {cart_item.product.stock} items left.')
                return redirect('checkout')

        selected_address = get_object_or_404(Address, id=address_id, user=request.user)
        total_price = sum(
            (item.product.offerprice or item.product.price) * item.quantity for item in cart_items
        )

        # Create order
        order = Order.objects.create(
            user=request.user,
            name=selected_address.name,
            phone=selected_address.phone,
            pincode=selected_address.pincode,
            address=selected_address.address,
            address_type='Home' if selected_address.is_default else 'Other',
            payment_method=payment_method,
            total_price=total_price,
            razorpay_payment_id=razorpay_payment_id if payment_method == 'razorpay' else '',
            status='Ordered'
        )

        # Create order items and reduce stock
        for cart_item in cart_items:
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=(cart_item.product.offerprice or cart_item.product.price)
            )
            # Reduce stock
            cart_item.product.stock -= cart_item.quantity
            cart_item.product.save()

        # Clear cart
        cart_items.delete()
        return redirect('payment_successful')

    return redirect('checkout')

def order_detail_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'order_detail.html', {'order': order})

@login_required(login_url='login')
def update_order_status(request, order_id):
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('index')

    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        
        if new_status in valid_statuses and new_status != 'Cancelled':  # Cancel is handled separately
            if order.status != new_status:
                order.status = new_status
                order.save()
                messages.success(request, f"Order #{order.id} status updated to {new_status}.")

                # Send email notification to the user
                try:
                    subject = f'Order #{order.id} Status Update'
                    message = (
                        f'Dear {order.user.username},\n\n'
                        f'Your order #{order.id} has been updated to the following status: {new_status}.\n'
                        f'Order Details:\n'
                        f'Total Price: ₹{order.total_price}\n'
                        f'Payment Method: {order.payment_method.title()}\n'
                        f'For more details, please check your order history on our website.\n\n'
                        f'Thank you for shopping with VaultGuard!'
                    )
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[order.user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    messages.error(request, f"Order status updated, but failed to send email notification: {str(e)}")

            else:
                messages.error(request, f"Order #{order.id} is already {new_status}.")
        else:
            messages.error(request, "Invalid status update.")
    
    return redirect('admin_bookings')

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

@login_required(login_url='login')
def payment_successful(request):
    if request.user.is_superuser:
        return redirect('admin_bookings')
    order = Order.objects.filter(user=request.user).order_by('-created_at').first()
    if not order:
        messages.error(request, 'No recent order found.')
        return redirect('index')
    return render(request, 'payment_successful.html', {'order': order})

def order_tracking(request):
    return render(request, 'order_tracking.html')

def track_order(request):
    if request.method == 'POST':
        order_number = request.POST.get('order_number')
        try:
            order = Order.objects.get(id=order_number, user=request.user)
            context = {
                'order_status': order.status,
                'order': order,
                'items': order.items.all(),  # Pass all order items
            }
            return render(request, 'order_tracking.html', context)
        except Order.DoesNotExist:
            return render(request, 'order_tracking.html', {'error': 'Order not found or you do not have permission to view it'})
    
    return render(request, 'order_tracking.html')

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
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    # Calculate delivery date and return eligibility for each order
    for order in orders:
        order.delivery_date = order.created_at + timedelta(days=5)
        # Check if order is within 7 days for return eligibility
        order.can_return = (order.status == 'Delivered' and 
                           (timezone.now() - order.created_at).days < 7)

    editing_address = False
    address_to_edit = None
    name = phone = pincode = address = ''
    errors = {}

    # Check if editing an address
    address_id = request.GET.get('edit')
    if address_id:
        try:
            address_to_edit = Address.objects.get(id=address_id, user=request.user)
            editing_address = True
            name = address_to_edit.name
            phone = address_to_edit.phone
            pincode = address_to_edit.pincode
            address = address_to_edit.address
        except Address.DoesNotExist:
            pass

    context = {
        'addresses': addresses,
        'orders': orders,
        'editing_address': editing_address,
        'address_to_edit': address_to_edit,
        'name': name,
        'phone': phone,
        'pincode': pincode,
        'address': address,
        'errors': errors,
        'action': 'Edit',
    }
    return render(request, 'profile.html', context)

@login_required
def add_address(request):
    if request.method == 'POST':
        name = request.POST.get('name', '')
        address = request.POST.get('address', '')
        pincode = request.POST.get('pincode', '')
        phone = request.POST.get('phone', '')

        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not address:
            errors['address'] = 'Address is required.'
        if not pincode:
            errors['pincode'] = 'Pincode is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'

        if not errors:
            Address.objects.create(
                user=request.user,
                name=name,
                address=address,
                pincode=pincode,
                phone=phone
            )
            messages.success(request, 'Address added successfully!')
            return redirect('profile')
        else:
            return render(request, 'address_form.html', {
                'errors': errors,
                'name': name,
                'address': address,
                'pincode': pincode,
                'phone': phone,
                'action': 'Add'
            })

    return render(request, 'address_form.html', {
        'action': 'Add',
        'name': '',
        'address': '',
        'pincode': '',
        'phone': '',
        'errors': {}
    })
@login_required
def edit_address(request, address_id):
    address_obj = get_object_or_404(Address, id=address_id, user=request.user)

    if request.method == 'POST':
        name = request.POST.get('name', '')
        address = request.POST.get('address', '')
        pincode = request.POST.get('pincode', '')
        phone = request.POST.get('phone', '')

        errors = {}
        if not name:
            errors['name'] = 'Name is required.'
        if not address:
            errors['address'] = 'Address is required.'
        if not pincode:
            errors['pincode'] = 'Pincode is required.'
        if not phone:
            errors['phone'] = 'Phone number is required.'

        if not errors:
            address_obj.name = name
            address_obj.address = address
            address_obj.pincode = pincode
            address_obj.phone = phone
            address_obj.save()
            messages.success(request, 'Address updated successfully!')
            return redirect('profile')
        else:
            return render(request, 'address_form.html', {
                'errors': errors,
                'name': name,
                'address': address,
                'pincode': pincode,
                'phone': phone,
                'action': 'Edit'
            })

    return render(request, 'address_form.html', {
        'name': address_obj.name,
        'address': address_obj.address,
        'pincode': address_obj.pincode,
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


@login_required
def admin_bookings(request):
    if not request.user.is_superuser:
        return redirect('index')
    orders = Order.objects.all().order_by('-created_at')
    
    # Calculate delivery date for each order (created_at + 5 days)
    for order in orders:
        order.delivery_date = order.created_at + timedelta(days=5)
    
    return render(request, 'bookings.html', {'orders': orders})

@login_required(login_url='login')
def confirm_order(request, order_id):
    # Ensure only admins can access this view
    if not request.user.is_superuser:
        messages.error(request, "You do not have permission to perform this action.")
        return redirect('index')

    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        if order.status == 'Pending':
            order.status = 'Confirmed'
            order.save()
            messages.success(request, f"Order #{order.id} has been confirmed.")
        else:
            messages.error(request, f"Order #{order.id} cannot be confirmed as it is already {order.status}.")
    
    return redirect('admin_bookings')

def payment_successful(request):
    return render(request, 'payment_successful.html')

@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == "POST":
        # Check if the order is in a cancellable state (not Delivered, Returned, or Cancelled)
        if order.status in ['Ordered', 'Confirmed', 'Shipped']:
            # Update order status to Cancelled
            order.status = 'Cancelled'
            order.save()
            
            # Restore stock for each item in the order
            for order_item in order.items.all():
                product = order_item.product
                product.stock += order_item.quantity
                product.save()
        
    
    return redirect('profile')

def order_success(request):
    order = Order.objects.filter(user=request.user).order_by('-created_at').first()
    if not order:
        messages.error(request, 'No recent order found.')
        return redirect('index')
    return render(request, 'order_success.html', {'order': order})


@login_required
def return_order(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        # Check if the order is in 'Delivered' status and within 7 days
        if order.status == 'Delivered':
            order_age = timezone.now() - order.created_at
            if order_age.days <= 7:
                order.status = 'Returned'
                order.save()
                messages.success(request, f"Order #{order.id} has been marked for return.")
            else:
                messages.error(request, "Return period has expired (7 days).")
        else:
            messages.error(request, "Only delivered orders can be returned.")
        return redirect('profile')
    
    return redirect('profile')


def category(request):
    return render(request, 'category.html')

def terms(request):
    return render(request, 'terms.html')

def privacy(request):
    return render(request, 'privacy.html')

def contact(request):
    return render(request, 'contact.html')
