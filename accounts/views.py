from django.shortcuts import render,redirect
from .forms import RegistrationForm
from .models import Account
from django.contrib import messages,auth
from django.contrib.auth.decorators import login_required

#email verification
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.utils.http import urlsafe_base64_encode,urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator


# Create your views here.

def register(request):
    if request.method=="POST":
        form=RegistrationForm(request.POST)
        if form.is_valid():
            first_name=form.cleaned_data['first_name']
            last_name=form.cleaned_data['last_name']
            email=form.cleaned_data['email']
            password=form.cleaned_data['password']
            username=email.split('@')[0]
            phone_number=form.cleaned_data['phone_number']
            user=Account.objects.create_user(first_name=first_name,last_name=last_name,email=email,username=username,password=password)
            user.phone_number=phone_number
            user.save()

            current_site = get_current_site(request)
            email_subject = 'please activate your account'

            context_data = {
                'user': user,
                'domain': current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                }
            
            body=render_to_string('accounts/account_verification_email.html',context_data)
            to_email=email
            send_email=EmailMessage(email_subject,body,to=[to_email])
            send_email.send()
            
            # messages.success(request,"registration successful.")
            return redirect('/accounts/login/?command=verification&email='+email) 
    else:
        form=RegistrationForm()    

    data={
        'form':form
    }
    return render(request,'accounts/register.html',data)

def login(request):
    if request.method=='POST':
        email=request.POST['email']
        password=request.POST['password']

        user = auth.authenticate(email=email, password=password)   
         
        if user is not None:
            auth.login(request,user)
            # messages.success(request,"logged in successful.") 
            return redirect('home')
        else:
            messages.error(request,"invalid login credentials!")    
            return redirect('login')
        
    return render(request,'accounts/login.html')

login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request,"you are logged out.")
    return redirect('login')

def activate(request,uidb64,token):
    try:
        uid=urlsafe_base64_decode(uidb64).decode()
        user=Account._default_manager.get(pk=uid)  
    except(TypeError,ValueError,OverflowError,Account.DoesNotExist):
        user=None

    if user is not None and default_token_generator.check_token(user,token):
        user.is_active=True
        user.save()
        messages.success(request,'congrats! Your account is activated.')
        return redirect('login')
    else:
        messages.error(request,'invalid activation link.')
        return redirect('register')

