from django.urls import path

from . import views

app_name = 'shop'

urlpatterns = [
    path('catalog/', views.catalog, name='catalog'),
    path('category/<slug:slug>/', views.category_detail, name='category'),
    path('perfume/<slug:slug>/', views.perfume_detail, name='perfume_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('cart/add/<int:perfume_id>/', views.cart_add, name='cart_add'),
    path('cart/update/<str:cart_key>/', views.cart_update, name='cart_update'),
    path('cart/remove/<str:cart_key>/', views.cart_remove, name='cart_remove'),
    path('checkout/novaposhta/', views.nova_poshta_autofill, name='nova_poshta_autofill'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/success/<int:order_id>/', views.checkout_success, name='checkout_success'),
    path('payment/<int:order_id>/', views.payment_start, name='payment_start'),
    path('payment/<int:order_id>/return/', views.payment_return, name='payment_return'),
    path('payment/liqpay/callback/', views.liqpay_callback, name='liqpay_callback'),
]
