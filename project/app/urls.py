from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),
    path('', views.index, name='index'),
    path('category/', views.category, name='category'),
    path('bookings/', views.bookings, name='bookings'),
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('contact/', views.contact, name='contact'),
    path('product/<int:id>/', views.product, name='product'),
    path('products/', views.product_list, name='product_list'),
    path('search/', views.search_results, name='search_results'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/increment/<int:id>/', views.increment_cart, name='increment_cart'),
    path('cart/decrement/<int:id>/', views.decrement_cart, name='decrement_cart'),
    path('cart/delete/<int:id>/', views.delete_cart_item, name='delete_cart_item'),
    path('cart/remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('process-checkout/', views.process_checkout, name='process_checkout'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('order-confirmation/<int:order_id>/', views.contact, name='order_confirmation'),
    path('update_quantity/<int:product_id>/', views.update_quantity, name='update_quantity'),
    path('dashboard/', views.first_page, name='firstpage'),
    path('dashboard/add-product/', views.add_product, name='add_product'),
    path('dashboard/edit/<int:id>/', views.edit_g, name='edit_g'),
    path('dashboard/delete/<int:id>/', views.delete_g, name='delete_g'),
    path('payment-successful/', views.payment_successful, name='payment_successful'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
