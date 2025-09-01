from django.shortcuts import render,redirect
from .forms import OrderForm
from .models import Order,Payment,OrderProduct
from cart.models import CartItem
from store.models import Product
import datetime
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

#paypal 
import requests
from django.http import JsonResponse
from django.conf import settings

# Create your views here.

def place_order(request,total=0,quantity=0,cart_items=None):
    current_user=request.user
    cart_items=CartItem.objects.filter(user=current_user)
    cart_count=cart_items.count()

    if cart_count <=0:
        return redirect('store')
    
    grand_total=0
    tax=0  
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

    tax = (12 * total)/100
    grand_total = total + tax

    if request.method == 'POST':
        form=OrderForm(request.POST)

        if form.is_valid():
            data=Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.city = form.cleaned_data['city']
            data.state = form.cleaned_data['state']
            data.country = form.cleaned_data['country']
            data.order_note = form.cleaned_data['order_note']
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            #generate order number
            current_date = datetime.date.today().strftime("%Y%m%d")  #2025
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            order = Order.objects.get(user=current_user,is_ordered=False,order_number=order_number)
            
            context={
                'order':order,
                'cart_items':cart_items,
                'total':total,
                'tax':tax,
                'grand_total':grand_total,

                }
            
            return render(request,'orders/payments.html',context)
        
    else:
        return redirect('checkout')        

def get_paypal_access_token(request):
    url = f"{settings.PAYPAL_API_BASE}/v1/oauth2/token"
    auth = (settings.PAYPAL_CLIENT_ID,settings.PAYPAL_SECRET)
    headers = {"Accept": "application/json", "Accept-Language": "en_US"}
    data = {"grant_type": "client_credentials"}

    response = requests.post(url, headers=headers, auth=auth, data=data)
    return response.json()['access_token']

def create_paypal_order(request,order_number):

    order=Order.objects.get(user=request.user, is_ordered=False,order_number=order_number)

    access_token = get_paypal_access_token(request)

    url = f"{settings.PAYPAL_API_BASE}/v2/checkout/orders"
    headers = {"Authorization": f"Bearer {access_token}","Content-type": "application/json"}
    data = {
        "intent": "CAPTURE",
        "purchase_units": [{
            "amount": {"currency_code": "USD", "value":order.order_total }
        }],
        "application_context": {
            "return_url": request.build_absolute_uri("capture/"),  #
            "cancel_url": request.build_absolute_uri("payment_failed/")   #
        }
    }
    
    response = requests.post(url, json=data, headers=headers).json()

    if "links" in response:
        for link in response["links"]:
            if link["rel"] == "approve":
                return redirect(link["href"])
            
    return JsonResponse(response, status=400)            


def capture_paypal_order(request,order_number,total=0,quantity=0,cart_items=None):
    token = request.GET.get("token") #paypal order_id

    access_token = get_paypal_access_token(request)

    url = f"{settings.PAYPAL_API_BASE}/v2/checkout/orders/{token}/capture"
    headers = {"Authorization": f"Bearer {access_token}", "content-type": "application/json"}  

    response = requests.post(url,headers=headers).json()

    if response["status"] == "COMPLETED":
        capture = response["purchase_units"][0]["payments"]["captures"][0]

        order=Order.objects.get(user=request.user, is_ordered=False,order_number=order_number)

        payment=Payment(
            user=request.user,
            payment_id=capture['id'],
            payment_method="paypal",
            amount_paid=order.order_total,
            status=capture['status']
        )
        
        payment.save()

        order.payment=payment
        order.is_ordered=True
        order.status='completed'
        order.save()

        #move cart items to OrderProduct model.
        cart_items=CartItem.objects.filter(user=request.user)
        for item in cart_items:
            order_product=OrderProduct()
            order_product.order_id=order.id
            order_product.payment=payment
            order_product.user_id=request.user.id
            order_product.product_id=item.product_id
            order_product.quantity=item.quantity
            order_product.product_price=item.product.price
            order_product.ordered=True
            order_product.save()
            
            #add product variations to OrderProduct model.
            cart_item=CartItem.objects.get(id=item.id)
            product_variation=cart_item.variations.all()
            order_product=OrderProduct.objects.get(id=order_product.id)
            order_product.variations.set(product_variation)
            order_product.save()

            #reduce ordered product quantity from Stock.
            product=Product.objects.get(id=item.product_id)
            product.stock -= item.quantity
            product.save()
            
            ordered_products=OrderProduct.objects.filter(user=request.user,payment=payment)
             
            total += (item.product.price * item.quantity)
            quantity += item.quantity

        tax = (12 * total)/100
        grand_total = total + tax

        CartItem.objects.filter(user=request.user).delete()  

        #EmailMessage for successful order
        email_subject = 'Thank you for your order'
        context_data = {
            'user': request.user,
            'order': order
            }
            
        body=render_to_string('orders/order_recieved_email.html',context_data)
        to_email=request.user.email
        send_email=EmailMessage(email_subject,body,to=[to_email])
        send_email.send()    

        data={
            'order':order,
            'payment':payment,
            'ordered_products': ordered_products,
            'total': total,
            'tax' : tax,
            'grand_total': grand_total
        }

        return render(request,'orders/payment_success.html',data)
    
    return redirect('place_order')

def payment_success(request,order_number):
    return render(request,'orders/payment_success.html')

def payment_failed(request,order_number):
    return render(request,'orders/payment_failed.html')

