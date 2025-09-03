from django.shortcuts import render,redirect,get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from .models import Product,ReviewRating
from .forms import ReviewRatingForm
from category.models import Category 
from cart.models import Cart,CartItem
from orders.models import OrderProduct
from cart.views import _cart_id
from django.db.models import Q
from django.contrib import messages
# Create your views here.

def store(request,category_slug=None):
    categories = None
    products   = None
    if category_slug != None:
        categories=get_object_or_404(Category,slug=category_slug)
        products=Product.objects.filter(category=categories,is_available=True)

        paginator=Paginator(products,1)
        page=request.GET.get('page')
        paged_products=paginator.get_page(page)

        products_count=products.count()
    else:
        products=Product.objects.filter(is_available=True).order_by('id')

        paginator=Paginator(products,3)
        page=request.GET.get('page')
        paged_products=paginator.get_page(page)

        products_count=products.count()
        
    data={
        'products':paged_products,
        'products_count':products_count
        }

    return render(request,'store/store.html',data)

def product_detail(request,category_slug,product_slug):
    single_product = get_object_or_404(Product, category__slug=category_slug, slug=product_slug)
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
        cart.save()

    try:
        in_cart=CartItem.objects.filter(cart=cart,product=single_product).exists()
    except Exception as e:
        raise e
    
    try:
        ordered_products=OrderProduct.objects.filter(user__id=request.user.id,product__id=single_product.id).exists()
    except OrderProduct.DoesNotExist:
        ordered_products=None

    reviews=ReviewRating.objects.filter(product__id=single_product.id,status=True)    

    data={
        'single_product':single_product,
        'in_cart':in_cart,
        'ordered_products':ordered_products,
        'reviews':reviews
        }
            
    return render(request,'store/product_detail.html',data)

def search(request):
    if 'keyword' in request.GET:
        keyword=request.GET['keyword']
        if keyword:
            products=Product.objects.order_by('-created_date').filter(Q(description__icontains=keyword) | Q(product_name__icontains=keyword))
            products_count=products.count()
    data={
        'products':products,
        'products_count':products_count
    }    

    return render(request,'store/store.html',data)       

def submit_review(request,product_id):
    url=request.META.get('HTTP_REFERER')

    try:
        if request.method == "POST":
            reviews = ReviewRating.objects.get(user__id=request.user.id,product__id=product_id)
            form = ReviewRatingForm(request.POST,instance=reviews)
            form.save()
            messages.success(request,"Your review has been updated.")
            return redirect(url)
        
    except ReviewRating.DoesNotExist:
        if request.method == "POST":
            form = ReviewRatingForm(request.POST)
            if form.is_valid():
                data = ReviewRating()
                data.subject = form.cleaned_data['subject']
                data.rating = form.cleaned_data['rating']
                data.review = form.cleaned_data['review']
                data.user_id = request.user.id
                data.product_id = product_id
                data.ip = request.META.get('REMOTE_ADDR')
                data.save()
                messages.success(request,"Your review has been submitted.")
                return redirect(url)

