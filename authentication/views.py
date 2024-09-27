from django.shortcuts import render, redirect,get_object_or_404,HttpResponseRedirect
from authentication.models import *
from product.models import *
from django.contrib.auth import authenticate, login
import random
from functions import send_email_otp,send_email_reset_link
from django.contrib import messages
from django.db.models import Q
from django.core.mail import send_mail
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.csrf import csrf_protect

from dashboard.models import HomeBannerImages,HomeBannerScrolling
from product.models import Product,DiscountOnProducts
from product import serializers
from product.serializers import product_serializer
from dashboard.models import *
import paypalrestsdk
from django.db.models import Sum
from django.contrib.auth.hashers import check_password
from django.shortcuts import render, redirect
from taggit.models import Tag




def home(request):
    if request.method == 'POST':
        email =request.POST.get('email')
        if request.user.is_authenticated:
            if request.user.newsletter == True:
                messages.error(request,'Already Subscribed to Newsletter!!')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

            elif request.user.email == email:
                user = User.objects.get(email=email)
                user.newsletter =True
                user.save()
                messages.success(request,'Thank You Subscribing to Our Newsletter')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


            elif Newsletter.objects.filter(email=email).exists():
                            messages.error(request,'Already Subscribed to Newsletter !!')
                            return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))

            else:
                Newsletter.objects.create(email=email).save()

                messages.success(request,'Thank You Subscribing to Our Newsletter')
                return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))
            
        else:
                    return redirect('signin')


    products = Product.objects.all().order_by('created_at').reverse()[:10]
    serializer = serializers.product_serializer(products,many=True)
    products=serializer.data

    sale_on_product = DiscountOnProducts.objects.filter(active=True).order_by('created_at').reverse()[:2]


    #topselling products 
    top_selling_products = Product.objects.filter(
        orderitem__isnull=False  # Only consider products that have associated order items
    ).annotate(
        total_quantity=Sum('orderitem__quantity')  # Calculate the total quantity sold
    ).order_by(
        '-total_quantity'  # Order by total quantity in descending order
    )[:12]
    
    cntx={
        'title': 'Zeba | Home Interior',
        'img':HomeBannerImages.objects.first(),
        'images':HomeBannerScrolling.objects.all(),
        'products':products,
        'sale_on_product':sale_on_product,
        'top_selling_products':top_selling_products
    }
    return render(request, 'index-6.html', cntx)


@csrf_protect
def signup(request):
    if request.user.is_authenticated:
        return redirect('home')
    
    else:
        if request.method == 'POST':
            first_name = request.POST.get('fname')
            last_name = request.POST.get('lname')
            email = request.POST.get('email')
            phone = request.POST.get('phone')
            password1 = request.POST.get('password1')
            password2 = request.POST.get('password2')
            newsletter = request.POST.get('newsletter')
            # newsletter = True/False
            if newsletter == "on":
                newsletter = True
            else:
                newsletter = False

            if password1 != password2:
                messages.error(request,'Password Must be same')
                return redirect('signup')
            if User.objects.filter(username=email).exists():
                messages.error(request,'Email Alrady Registered !!')
                return redirect('signup')
            if User.objects.filter(email=email).exists():
                messages.error(request,'Email Alrady Registered !!')
                return redirect('signup')
            if User.objects.filter(phone=phone).exists():
                messages.error(request,'Phone numeber is already registered !!')
                return redirect('signup')
            

            user = User.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=email,
                phone=phone,
                newsletter=newsletter,
            )
            user.set_password(password1)
            user.save()
            user = authenticate(request, username=email, password=password1)

            login(request, user)

            return redirect('otp')

        else:
            return render(request, 'registery/signup.html', {"title":"Zehohomes- Signup","active":"signup"})  


# @csrf_protect()
def signin(request):
        if request.user.is_authenticated:
            return redirect('home')     
        
        if request.method == 'POST':
                email = request.POST.get('email')
                password = request.POST.get('password')
            
            # try:    
                user = User.objects.get(email=email)
                if check_password(password, user.password):
                        login(request, user)
                 
                        if user.is_verified:
                            return redirect('home')
                else:
                        messages.error(request,'Invalid Password')
                        return redirect('signin')
            # except:
                        
            #             messages.error(request,'Invalid!! Email not exist')
            #             return redirect('signin')
        
        return render(request, 'registery/signin.html', {"title":"Zehohomes- Signin","active":"signin"})
    


def forgot_password(request):
    

    if request.method == 'POST':
        email = request.POST.get('email')
        pass1 = request.POST.get('pass1')
        pass2 = request.POST.get('pass2')

        print(email,"######################################")


        # Check if the user exists
        try:
            user = User.objects.get(email=email)
            if pass1 != pass2:
                 messages.error(request,'Password is  not matching !')
            request.session['new_pass']={'email':email,'password':pass1}
            return redirect('otp_forgot_pass')
        

        except User.DoesNotExist:
            # Handle the case where the user does not exist
            messages.error(request,'Email Not Exist!!')
            return redirect('forgot_password')
     
    # If it's a GET request, render the empty form
    return render(request, 'registery/forgot_password.html')



def otp(request):
    if request.user.is_authenticated:
        if request.user.is_verified :
            return redirect('home')
            
    if not request.user.is_verified:

        email = request.user.email
        user = User.objects.get(email=email)
        

        if request.method == 'POST':
            otp = request.POST.get('otp')
            if user.otp == otp:
                
                user.is_verified = True
                user.otp = ''
                user.save()



                login(request, user)

                request.session.pop('signup_email', None)
                messages.success(request,'OTP Correct')
                return redirect('home')
                            
            else:
                messages.error(request,"OTP Invalid")
                return redirect('otp')
            
        otp = random.randint(100000, 999999)
        user.otp = otp
        user.save()
        # send opt to email
        send_email_otp(user=user,otp=otp)
        return render(request, 'registery/otp.html',{'title':'OTP Verification'})
        

def otp_forgot_pass(request):
        email = request.session['new_pass']['email']
        new_password = request.session['new_pass']['password']
        user = User.objects.get(email=email)

        if request.method == 'POST':
            otp = request.POST.get('otp')


            if user.otp == otp:
                user.is_verified = True
                user.otp = ''
                user.set_password(new_password)
                user.save()

                messages.success(request,'Password Has successfully changed')
                return redirect('signin')
                            
            else:
                messages.error(request,"OTP Invalid")
                return redirect('otp')
            
        otp = random.randint(100000, 999999)
        user.otp = otp
        user.save()
        # send opt to email
        send_email_otp(user=user,otp=otp)
        return render(request, 'registery/otp.html',{'title':'OTP Verification','resetpass':email})



def userprofile(request):
    if not request.user.is_authenticated:
        return redirect('signin')
    
    elif not request.user.is_verified :
            request.session['signup_email'] = request.user.email
            return redirect('otp')
    
    address = Address.objects.filter(user=request.user.id)
    orders = Order.objects.filter(customer_email = request.user.email)[::-1]
    print(orders,"@@@@@@@@@")
    return render(request,'user_profile/user-dashboard.html',{'title':'Profile','addresses':address,'orders':orders})



def address(request):
    if not request.user.is_authenticated:
        return redirect('signin')
    
    elif not request.user.is_verified :
            request.session['signup_email'] = request.user.email
            return redirect('otp')
    
    if request.method == 'POST':
            user = User.objects.get(id=request.user.id)
            address_line_1 = request.POST.get('address_line_1')
            address_line_2 = request.POST.get('address_line_2')
            city = request.POST.get('city')
            postal_code = request.POST.get('postal_code')
            country = request.POST.get('country')
            state = request.POST.get('state')
            is_default = request.POST.get('is_default')
            if is_default == "on":
                    is_default = True
            else:
                    is_default = False


            addresses = Address.objects.filter(user=request.user)
            if is_default == True and addresses:
                for address in addresses:
                    address.is_default = False
                    address.save()


            address = Address.objects.create(
                user = user,
                address_line_1 = address_line_1,
                address_line_2 = address_line_2,
                city = city,
                postal_code = postal_code,
                country = country,
                state = state,
                is_default = is_default,
            )
            address.save()
            messages.success(request,"Address Added Successfully")
            return redirect('userprofile')
    
    else:
        # Create add address html page and add path below
        
        return render(request,'update_forms/address_crud.html',{'title':'Add Address'})


      
def address_by_id(request, id,slug):

    if not request.user.is_authenticated:
        return redirect('signin')
    
    elif not request.user.is_verified :
            request.session['signup_email'] = request.user.email
            return redirect('otp')
    
    if slug == 'UPDATE':
        address_id = id
        if request.method =="POST":    
                address_line_1 = request.POST.get('address_line_1')
                address_line_2 = request.POST.get('address_line_2')
                city = request.POST.get('city')
                postal_code = request.POST.get('postal_code')
                country = request.POST.get('country')
                state = request.POST.get('state')
                is_default = request.POST.get('is_default')
                if is_default == "on":
                    is_default = True
                else:
                    is_default = False
                address = Address.objects.get(id=address_id)
               
                addresses = Address.objects.filter(user=request.user)
                if is_default == True and addresses:
                    for old_address in addresses:
                        old_address.is_default = False
                        old_address.save()
                        
                address.address_line_1 = address_line_1
                address.address_line_2 = address_line_2
                address.city = city
                address.postal_code = postal_code
                address.country = country
                address.state = state
                address.is_default = is_default
                address.save()
                messages.success(request,"Address Updated Successfully")
                return redirect('userprofile')
        
        else:
            address = Address.objects.get(id=address_id)
            return render(request,'update_forms/address_crud.html',{'title':'Update Address','address':address})
        
    elif slug == 'delete':
        address_id =id
        address = Address.objects.get(id=address_id)
        address.delete()
        return redirect('userprofile')
    


def card(request):
    if not request.user.is_authenticated:
        return redirect('signin')
    
    elif not request.user.is_verified :
            request.session['signup_email'] = request.user.email
            return redirect('otp')
    
    if request.method == 'POST':
            user = User.objects.get(id=request.user.id)
            first_name = request.POST.get('first_name')
            last_name = request.POST.get('last_name')
            number = request.POST.get('number')
            month = request.POST.get('month')
            year = request.POST.get('year')
            card_type = request.POST.get('card_type')
            is_default = request.POST.get('is_default')
            if is_default == "on":
                    is_default = True
            else:
                    is_default = False

            if Card.objects.filter(user=user, number=number).exists():
                messages.error(request,"This Card Number Already Exists")
                return redirect('userprofile')
            
            cards = Card.objects.filter(user=request.user.id)
            if is_default == True and cards:
                for address in cards:
                    address.is_default = False
                    address.save()


            card = Card.objects.create(
                user = user,
                first_name = first_name,
                last_name = last_name,
                number = number,
                month = month,
                year = year,
                card_type = card_type,
                is_default = is_default,
            )
            card.save()
            messages.success(request,"Address Added Successfully")
            return redirect('userprofile')
    
    else:
        
        return render(request,'card.html',{'title':'Add Card'})


            
def card_by_id(request, id, slug):

    if not request.user.is_authenticated:
        return redirect('signin')
    
    elif not request.user.is_verified :
            request.session['signup_email'] = request.user.email
            return redirect('otp')
    
    if slug == 'UPDATE':
        card_id = id
        card = Card.objects.get(id=card_id)
        if card.user.id != request.user.id:
                messages.error(request,"Access Denied")
                return redirect('userprofile')
        
        if request.method =="POST":    
                first_name = request.POST.get('first_name')
                last_name = request.POST.get('last_name')
                number = request.POST.get('number')
                month = request.POST.get('month')
                year = request.POST.get('year')
                card_type = request.POST.get('card_type')
                is_default = request.POST.get('is_default')

                if is_default == "on":
                    is_default = True
                else:
                    is_default = False

                cards = Card.objects.filter(user=request.user.id)

                if Card.objects.filter(user=request.user.id, number=number).exists():
                    messages.error(request,"This Card Number Already Exists")
                    return redirect('userprofile')
        
                if is_default == True and cards:
                    for old_card in cards:
                        old_card.is_default = False
                        old_card.save()
                        
                card.first_name = first_name
                card.last_name = last_name
                card.number = number
                card.month = month
                card.year = year
                card.card_type = card_type
                card.is_default = is_default
                card.save()
                messages.success(request,"Address Updated Successfully")
                return redirect('userprofile')
        
        else:
            return render(request,'card_crud.html',{'title':'Update Card','card':card})
        
    elif slug == 'delete':
        card_id = id
        card = Card.objects.get(id=card_id)
        return redirect('userprofile')
    
def updateCart(request):
   
    return redirect('show_cart')



def Add_Cart(request,uuid,sqp_id):

    if request.user.is_authenticated:
        
        qty= request.GET.get('qty',1)

        if request.method == 'POST':
            qty= request.POST.get('qty',1)
            selected_color = request.POST.get('selected_color')

            
        status = request.GET.get('status',None)


        user = get_object_or_404(User,id=request.user.id)
        pro = get_object_or_404(Product,id=uuid)
        size_quantity_price = get_object_or_404(SizeQuantityPrice,id=sqp_id)
        

        total_price = (float(qty)*float(size_quantity_price.price))
                    
        if size_quantity_price.discount:
            total_price =(float(qty)*float(size_quantity_price.discounted_price))
 

        if status == 'UPDATE':
            cart_item=Cart.objects.get(user=user,product=pro)

            cart_item.total_price = total_price
            cart_item.quantity = qty
            cart_item.save()
            messages.success(request,'Cart is Updated Successfully!!')
            return redirect('updateCart')

        if Cart.objects.filter(user=user,product=pro):


            messages.error(request,"Already In cart")
            return redirect('product_inside',pro.id)
        

        

        cart_item = Cart.objects.create(user=user,product=pro,quantity=qty,size_quantity_price=size_quantity_price,total_price=total_price)
        if selected_color :
                cart_item.color=selected_color
        else:
             selected_color = size_quantity_price.color
        cart_item.save()
    
        messages.success(request,"Added to cart")
        return redirect('updateCart')
    else:
        return redirect('signin')


def show_Cart(request):
    if request.user.is_authenticated:
    
        cart_items = Cart.objects.filter(user=request.user)
        code=None
        if request.method == 'POST':
            code = request.POST.get('code')
            status= request.POST.get('status')
            if code:
                if status =='apply':
                    discountcoupon=DiscountCoupon.objects.get(code=code)
                    dis_pro = discountcoupon.products.all()
                    coupon = 'activate'

        else:
                coupon = 'deactivate'
                dis_pro = []


        products_list =[ ]
        total_price = 0
        sub_total=0
        coupon_dis = 0
        if cart_items:
            for item in cart_items:
                product =get_object_or_404(Product,id=item.product.id)
                if product in dis_pro:
                     total_price = round((float(item.total_price)-(float(item.total_price) * (float(discountcoupon.percentage)/100))) + total_price, 2)
                     request.session[product.name] = {'price':round( float(item.total_price)-(float(item.total_price) * (float(discountcoupon.percentage)/100)) ,2)}
                     coupon_dis =  coupon_dis +(float(item.total_price) * (float(discountcoupon.percentage)/100))


                
                else:
                    total_price = round(float(item.total_price)+ total_price, 2)

                sub_total = round(float(item.total_price)+ sub_total, 2)

                products_list.append({'product':product,'qty':item.quantity,'sqp':item.size_quantity_price,'cart':item})

        
            cntx={
                'products':products_list,
                'title':'My Cart',
                'total_price':total_price,
                'sub_total':sub_total,
                'coupon_dis':coupon_dis,
                'coupon':coupon,

            }

        else:
            cntx={
                'title':'My Cart',
            }
        return render(request,'user_profile/cart.html',cntx)
    else:
         return redirect('signin')
            


def del_cart(request, uuid):
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(id=uuid)
            cart.delete()
        except:
             product = Product.objects.get(id=uuid)
             cart = Cart.objects.get(product=product)
             cart.delete()
        messages.success(request,'')
        return redirect('show_cart')
    else:
         return redirect('signin')




# def order(request):
#     if not request.user.is_authenticated:
#         return redirect('signin')
    
#     elif not request.user.is_verified :
#             request.session['signup_email'] = request.user.email
#             return redirect('otp')
    
#     if request.method == 'POST':
#             user = User.objects.get(id=request.user.id)
#             address_id = request.POST.get('address_id')

#             payment_id = "Generated Using Stripe Here"

#             order = Order.objects.create(
#                 address_line_1 = address_id.address_line_1,
#                 address_line_2 = address_id.address_line_2,
#                 city = address_id.city,
#                 postal_code = address_id.postal_code,
#                 country = address_id.country,
#                 state = address_id.state,
#                 payment_id = payment_id,
#             )
#             order.save()

#             toatl_amount = 0
#             for item in Cart.objects.filter(user=user):
#                 order_item = OrderItem.objects.create(product=item.product,quantity=item.quantity,size_quantity_price=item.size_quantity_price)
#                 order.order_items.add(order_item)
#                 toatl_amount += item.size_quantity_price.price
#                 order.save()
                
#             return redirect('/')
    
#     else:
#         return render(request,'cart.html',{'title':'Cart'})




paypalrestsdk.configure({
    "mode": "sandbox",  # or "live"
    "client_id": "AW51S_03IaBs6Kc-6UqkuAqLq9VzcjASJtDuTtwJlHkZAOsjBuZI0qXiobIHptNyDkUFEFEY9mcE0APm",
    "client_secret": "EAq19jPmNnIL07UjfpfXow80Y_luf3Zubd6Z2U74duLn2zuqwS4FR0K-JDK9azi2d2dFy1Ht1SP3IkQ6"
})
def generate_serial_id(cls):
        # Get the current month and year as two-digit strings
        month = str(datetime.date.today().month).zfill(2)
        year = str(datetime.date.today().year)[-2:]

        # Calculate the next counting number
        last_serial_id = cls.objects.filter(
            serial_id__startswith=month + year
        ).order_by('-serial_id').first()

        if last_serial_id:
            last_count = int(last_serial_id.serial_id[-3:])
            new_count = last_count + 1
        else:
            new_count = 1

        # Create the new serial_id
        new_serial_id = f"{month}{year}-{str(new_count).zfill(3)}"

        return new_serial_id
def payment(request):
    address_id = request.GET.get('address')
    if not address_id:
        messages.error(request,'Please Add/select Address')
        messages.error(request,'To Add Addres: view Profile >> Address >> Add New Address')
        return redirect('checkout')

    address = Address.objects.get(id=address_id)

    order = Order.objects.create(
        customer_name = str(request.user.first_name +' ' +request.user.last_name),
        customer_email = request.user.email,
        customer_contact = request.user.phone,
        address_line_1 = address.address_line_1,
        address_line_2 = address.address_line_2,
        city = address.city,
        postal_code = address.postal_code,
        country = address.country,
        state = address.state,
        
        payment_status = "Pending",
        payment_id = None,
        payment_amount = None, 
    )


    order.serial_id = generate_serial_id(Order)
    order.save()
    total = float(request.GET.get('total_amount'))
    charge = float(request.GET.get('charge'))
    
    deliverycountry =request.GET.get('deliverycountry') 


    for item in Cart.objects.filter(user=request.user):

        color = item.color
        size = item.size_quantity_price.size
        price = item.size_quantity_price.price
        sqp_code = item.size_quantity_price.name
        quantity = item.quantity
        dropdown_size = item.dropdown_size

        total_price =  (float(quantity)*float(price)) 



        order_item = OrderItem.objects.create(
                product = item.product,
                quantity = quantity,
                color = color,
                size = size,
                price = price,
                total=total_price,
                sqp_code=sqp_code,
                dropdown_size=dropdown_size
            )
        order_item.save()
        order.order_items.add(order_item)


        order.payment_amount = total
        order.deliveryCountry = deliverycountry
        order.deliveryCharges = charge
        order.sub_total = round(float(total-charge),2)
        order.save()

    payment = paypalrestsdk.Payment({
        "intent": "sale",
        "payer": {
            "payment_method": "paypal"
        },
        "redirect_urls": {
            "return_url": "http://127.0.0.1:8000/payment/execute/",
            "cancel_url": "http://127.0.0.1:8000/payment/cancel/"
        },
        "transactions": [{
            "amount": {
                "total": total,
                "currency": "USD"
            },
            "description": "Payment description"
        }]
    })
    
    if payment.create():
        request.session['paypal_payment_id'] = payment.id
        order.payment_id = payment.id
        order.save()
        for link in payment.links:
            if link.method == "REDIRECT":
                redirect_url = str(link.href)
                return redirect(redirect_url)
    else:
        messages.error(request,"Payment Canceled")
        return render(request, 'payment_error.html')


def payment_execute(request):

    payment_id = request.session.get('paypal_payment_id')
    if payment_id is None:
        return redirect('home')
    
    payment = paypalrestsdk.Payment.find(payment_id)
    if payment:
        # Payment successful
        order = Order.objects.filter(payment_id=payment_id)[0]
        order_items = order.order_items.all()
        
        products = []
        for item in order_items:
            products.append(item.product)
            for sqp in item.product.size_quantity_price.all() :
                sqp = SizeQuantityPrice.objects.get(id = sqp.id)
                sqp.quantity = int(sqp.quantity) -int(item.quantity) 
                sqp.save()
                print(sqp.quantity,"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

            
        serializer = product_serializer(products, many=True)

        order.payment_status = "Completed"
        order.delivery_status = "Order Processing"
        order.save()

        Cart.objects.filter(user=request.user).delete()

        cntx={
                    'payment':payment,
                    'products':serializer.data
        }
        # You can perform any additional actions here, such as updating your database
        messages.success(request,'Order Placed! You can check on order Track')
        return render(request, 'user_profile/order-success.html',cntx)
    else:
        # Payment failed
        order = Order.objects.filter(payment_id=payment_id)[0]
        
       
        order.payment_status = "Failed"
        order.save()

        messages.error(request,'Order Not Placed!')

        return render(request, 'payment_error.html')

def payment_cancel(request):
    # Payment cancelled
    order = Order.objects.filter(payment_id=payment_id)[0]
        
       
    order.payment_status = "Failed"
    order.save()
    messages.error(request,'Payment Canceled!')

    return render(request, 'payment_cancel.html')

# Navigations pages
def contactus(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        email = request.POST.get('email')
        phone_number =request.POST.get('phone_number')
        issue = request.POST.get('issue')
        product = request.POST.get('product',None)
        message = request.POST.get('message')

        enquiry = SupportTickets.objects.create(name=first_name, email=email,number=phone_number,issue=issue,
                                         product=product,message=message)
        enquiry.save()
        messages.success(request,'Support Tickets Generated Successfully')
        return redirect('contactus')
        
    if  request.GET.get('id'):
        id=request.GET.get('id')
        order =Order.objects.get(serial_id=id)
    else:
         order =None
    return render(request,'navigation_pages/contact-us.html',{'title':'Help Desk','order':order})


def aboutus(request):
    reviews = Reviews.objects.all()[::-1]

    page = request.GET.get('page', 1)  # Get the current page number from the request

    paginator = Paginator(reviews, 4)  # Paginate the serialized data with 10 items per page
    try:
        reviews = paginator.page(page)
    except PageNotAnInteger:
        reviews = paginator.page(1)
    except EmptyPage:
        reviews = paginator.page(paginator.num_pages)   

    return render(request,'navigation_pages/about-us.html',{'title':'About Us','reviews':reviews})

def faq(request):
    return render(request,'navigation_pages/faq.html',{'title':'F&Q'})

def wishlist(request):
    if request.user.is_authenticated:
        wishlist = WishList.objects.filter(user=request.user)
        cart_items_lis = Cart.objects.filter(user=request.user)

        product_list = []
        cart_items=[]
        if wishlist:
            for item in wishlist:
                for citem in cart_items_lis:
                    if citem.product.id == item.product.id:
                        cart_items.append(item.product.id)

                pro = get_object_or_404(Product,id=item.product.id)
                product_list.append({'pro':pro})
            cntx={
                'product_list':product_list,
                'cart_items':cart_items,
                'title':"Wishlist"
            }
            return render(request,'user_profile/wishlist.html',cntx)
        else:

            return render(request,'user_profile/wishlist.html',{'title':'WishList'})

    else:
        return redirect('signin')


def add_wishlist(request,uuid):
    if request.user.is_authenticated:
        try:
            pro = get_object_or_404(Product,id=uuid)
            WishList.objects.create(user=request.user,product=pro).save()

            return redirect('wishlist')
        except:
             messages.error(request, 'Already in wishlist')
             return redirect('wishlist')

    else:
        return redirect('signin')


def remove_wishlist(request,uuid):
     if request.user.is_authenticated:
        try:
            product = get_object_or_404(Product,id=uuid)
            WishList.objects.get(product=product).delete()
        except Exception as e:
             print(e)
        return redirect('wishlist')
     else:
            return redirect('signin')



def Track_order(request):
     if not request.user.is_authenticated:
            return redirect('signin')
     
     id = request.GET.get('id')
     if id:
            order = Order.objects.get(serial_id=id)
     else:       
        try:
             
            order = Order.objects.filter(user=request.user).order_by('-id')[0]
        except :
             order =None

     return render(request,"user_profile/order-tracking.html",{'title':'Order Tracking','order':order})


def terms_condition(request):
     return render(request,"navigation_pages/Terms&condition.html",{'title':'Terms & Conditions'})

def articles(request):
     tag = request.GET.get('tag')
     query = request.GET.get('query')
     print(tag,query)
     
     if query:
        # If a query parameter is present, filter articles based on the query
        articles = Articles.objects.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(content__icontains=query)
        )
     elif tag:
        # If a tag parameter is present, retrieve the tag and filter articles based on the tag
        articles = Articles.objects.filter(tags__name__in=[tag])

        print(articles)
     else:
        # If neither query nor tag parameter is present, retrieve all articles
        articles = Articles.objects.all()

     tags =Tag.objects.all()
     top_selling_products = Product.objects.filter(
        orderitem__isnull=False  # Only consider products that have associated order items
    ).annotate(
        total_quantity=Sum('orderitem__quantity')  # Calculate the total quantity sold
    ).order_by(
        '-total_quantity'  # Order by total quantity in descending order
    )[:4]
     return render(request,"navigation_pages/blogs.html",{'articles':articles,'tags':tags,'top_selling_products':top_selling_products})


def article_details(request,id):
     article = Articles.objects.get(id=id)
     top_selling_products = Product.objects.filter(
        orderitem__isnull=False  # Only consider products that have associated order items
    ).annotate(
        total_quantity=Sum('orderitem__quantity')  # Calculate the total quantity sold
    ).order_by(
        '-total_quantity'  # Order by total quantity in descending order
    )[:4]
     articles = Articles.objects.all()
     tags =Tag.objects.all()

     return render(request,"navigation_pages/blog-details.html",{'title':article.name,'article':article,'top_selling_products':top_selling_products,'articles':articles,'tags':tags})




def Update_Profile(request):
    if  request.method == 'POST':
         first_name = request.POST.get('first_name')
         last_name = request.POST.get('last_name')
         contact = request.POST.get('contact')
         gender = request.POST.get('gender')
         new_email =request.POST.get('new_email')
         user = User.objects.get(id = request.user.id)

         
         
         if User.objects.filter(phone=contact).exists():
                messages.error(request,'Phone numeber is already registered !!')
                return redirect('Update_Profile')


         user.first_name = first_name
         user.last_name = last_name
         user.phone = contact
         user.gender = gender
         user.save()

         if new_email:
                if User.objects.filter(email=new_email).exists():
                    messages.error(request,'Email Alrady Registered !!')
                    return redirect('Update_Profile')
                
                user.email = new_email
                user.is_verified = False

                user.save()
                
                return redirect('otp')

         return redirect('userprofile')
        
         
    cntx={
         'title':"Update Profile"
    }
    return render(request,'update_forms/update_profile.html',cntx)


def return_product(request):
     order_id = request.GET.get('id')
     order =Order.objects.get(serial_id = order_id)
     if request.method == 'POST':
            order_id = request.GET.get('id')
            issue = request.POST.get('issue')
            feedback =request.POST.get('feedback')
            order = Order.objects.get(serial_id =order_id)
            if ReturnOrders.objects.filter(order = order).exists():
                messages.error(request,"Return Order Already Initiated !!")
                return redirect('userprofile')
            else:
                 order.order_return = True
                 order.delivery_status = 'Cancel'
                 order.save()
                 ReturnOrders.objects.create(
                      order =order,
                      issue=issue,
                      feedback =feedback
                 ).save()
                 messages.success(request,"Return Order Initiated !!")
                 return redirect('userprofile')

     return render(request,'user_profile/return_product.html',{'title':'Return Product','order':order})
