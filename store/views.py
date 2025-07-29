from django.shortcuts import render,get_object_or_404
from django.shortcuts import HttpResponse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Product
from category.models import Category 
from cart.models import Cart,CartItem
from cart.views import _cart_id
from django.db.models import Q
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
    cart = Cart.objects.get(cart_id=_cart_id(request))
    try:
        in_cart=CartItem.objects.filter(cart=cart,product=single_product).exists()
    except Exception as e:
        raise e
    data={
        'single_product':single_product,
        'in_cart':in_cart
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
