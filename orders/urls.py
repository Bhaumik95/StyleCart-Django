from django.urls import path,include
from . import views

urlpatterns = [
    path('place_order/',views.place_order, name='place_order'),
    path('create/<int:order_number>/',views.create_paypal_order, name='create_paypal'),
    path('create/<int:order_number>/capture/',views.capture_paypal_order, name='capture_paypal'),
    path('create/<int:order_number>/payment_success/',views.payment_success, name='payment_success'),
    path('create/<int:order_number>/payment_failed/',views.payment_failed, name='payment_failed'),
      
]
