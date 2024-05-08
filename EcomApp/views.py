from django.shortcuts import render,redirect,HttpResponse
from .models import Product,CartItem,Order,Address
from django.views.generic.detail import DetailView
from django.db.models import Q
from .forms import CreateUserForm
from django.contrib import messages
from django.contrib.auth import authenticate,login,logout
import razorpay
import random
from django.core.mail import send_mail
from django.contrib.auth.models import User

# Create your views here.
def index(req):
        products = Product.objects.all()
        if req.user.is_authenticated:
            cart_item = CartItem.objects.filter(user=req.user)
            length = len(cart_item)
        #uname = req.session.get("uname","Guest")
            context ={'products':products,'items':length}
        else:
            context ={'products':products}
        return render(req,"index.html",context)
    
class SpecificView(DetailView):
    model=Product
    template_name="prod_detail_view.html"

def mobileView(req):
    queryset = Product.prod.mobile_list()
    print(queryset)
    context={'products':queryset}
    return render(req,"index.html",context)

def mlaptopView(req):
    queryset = Product.objects.filter(category__iexact="laptop")
    print(queryset)
    context={'products':queryset}
    return render(req,"index.html",context)

def tvView(req):
    queryset = Product.prod.tv_list()
    print(queryset)
    context={'products':queryset}
    return render(req,"index.html",context)

def rangeView(req):
    if req.method == "GET":
        return redirect("/")
    else:
        try:
            min = req.POST["min"]
            max = req.POST["max"]
            
            print(min,max)
            products = Product.objects.filter(price__range=(min,max))
            context = {'products':products}
            return render(req,"index.html",context)
        except :
            products = Product.objects.all()
            msg = "Enter both the values for filtering"
            context = {'products':products,'msg':msg}
            return render(req,"index.html",context)
        
def sortProducts(req):
    sort_option = req.GET.get('sort')
    if sort_option == "high_to_low":
        products = Product.objects.all().order_by('-price')
    elif sort_option == "low_to_high":
        products = Product.objects.all().order_by('price')
    else:
        products = Product.objects.all()
    context = {'products':products}
    return render(req,"index.html",context)

def search(req):
    query = req.POST.get('q')
    results = Product.objects.filter(Q(prod_name__icontains = query)|Q(desc__icontains = query)|Q(price__iexact = query))
    context = {'products':results}
    return render(req,"index.html",context)

def addCart(req,prod_id):
    try:
        products = Product.objects.get(product_id = prod_id)
        user = req.user if req.user.is_authenticated else None
        print(user)
        if user:
            cart_item,created = CartItem.objects.get_or_create(product=products, user = user)
        print(cart_item,created)
        if not created:
            cart_item.quantity += 1
        else:
            cart_item.quantity = 1
        cart_item.save()
        
        return redirect("/viewCart")
    except:
        return redirect("login")

def viewCart(req):
    try:
        prod = CartItem.objects.filter(user = req.user)
        context = {}
        total_price = 0
        length = len(prod)
        for x in prod:
            total_price += (x.product.price * x.quantity)
            print(total_price)
        context["products"] = prod
        context['total'] = total_price
        context['items'] = length
        return render(req,"cart.html",context)
    except:
        return redirect("login")

def updateqty(req,uval,item_id):
    c = CartItem.objects.filter(user = req.user,product_id = item_id)
    print(uval,c[0].quantity)
    if uval ==  1:
        temp = c[0].quantity + 1
        c.update(quantity = temp)
    else:
        temp = c[0].quantity - 1
        c.update(quantity = temp) 
        if temp == 0:
            c.delete()
    context= {'products':c}
    return redirect("/viewCart")

def remove_from_cart(req,item_id):
    cart_item = CartItem.objects.filter(product_id = item_id)
    cart_item.delete()
    return redirect("/viewCart")

def register(req):
   # form = UserCreationForm() Default Form
    form = CreateUserForm()
    if req.method == "POST":
        form = CreateUserForm(req.POST)
        if form.is_valid():
            form.save()
            print("USer Created Successfully")
            messages.success(req,"User Created Successfully")
            return redirect("/login")
        else:
            messages.error(req,"Your username or password format is invalid.")
    context = {'form':form}
    return render(req,"register.html",context)

def login_user(req):
    if req.method == "GET":
        return render(req,"login.html")
    else:
        username = req.POST["uname"]
        passw = req.POST["upass"]
        #print(username,passw)
        user = authenticate(req,username=username,password = passw)
        if user is not None:
            login(req,user)
            req.session['uname'] = username
            print("Loggged in successfully")
            messages.success(req,"Loggged in successfully")
            return redirect("index")
        else:
            messages.error(req,"There was an error. Try Again!!!")
            return redirect("login")
        #return render(req,"login.html")

def logout_user(req):
    try:
        logout(req)
        del req.session['uname'];
        messages.success(req,"You have Logged Out successfully")
        return redirect("index")
    except:
        logout(req)
        messages.success(req,"You have Logged Out successfully")
        return redirect("index")

def placeOrder(req):
    prod = CartItem.objects.filter(user = req.user)
    context = {}
    total_price = 0
    length = len(prod)
    for x in prod:
        total_price += (x.product.price * x.quantity)
        print(total_price)
    context["products"] = prod
    context['total'] = total_price
    context['items'] = length
    #return render(req,"cart.html",context)
    return render(req,"place_order.html",context)

def makePayment(req):
    try:
        print(req.user)
        cart_item = CartItem.objects.filter(user = req.user)
        oid = random.randrange(1000,9999)
        oid = str(oid)
        total_price = 0
        for x in cart_item:
            total_price += (x.product.price * x.quantity)
            o = Order.objects.create(order_id = oid,product = x.product,quantity =x.quantity,user = req.user)
        client = razorpay.Client(auth=("rzp_test_GWWK3HBmr4C4Ng", "4UxKj0SL7WKQqjjWWnmHachl"))
        data ={'amount':total_price * 100,"currency":"INR","receipt":oid}
        payment = client.order.create(data = data)
        print(payment)
        context = {}
        context['data'] = payment
        cart_item.delete()
        #sendUserMail()
        orders = Order.objects.filter(user=req.user,is_completed = False)
        msg = f"Order Details: Order id:{oid}, Price:{total_price}"
        send_mail(
        "Order Placed Successfully",
        msg,
        "jessica.dias@itvedant.com",
        [req.user.email],
        fail_silently=False,
    )
        orders.update(is_completed = True)
        return render(req,"payment.html",context)
    except:
        messages.error(req,"Amount should be atleast 1")
        return redirect("/")
    
def viewOrder(req):
    o= Order.objects.filter(user=req.user,is_completed = True)
    context = {'products':o}
    return render(req,"viewOrder.html",context)

def genAddress(req):
    add = Address.objects.filter(user = req.user)
    print(add)
    context = {'address':add}
    return render(req,"address.html",context)

def addAddress(req):
    if req.method == "GET":
        return render(req,"addAddress.html")
    else:
        try:
            new_address = req.POST["address"]
            pincode = req.POST["zip"]
            phone = req.POST["phone"]
            a = Address.objects.create(user= req.user,address=new_address,zipcode=pincode,phone = phone)
            return redirect("address")
        except:
            messages.error(req,"Zipcode and/or Phone Number must be Integer and not string")
            return render(req,"addAddress.html")

def updateAddress(req,pid):
    address = Address.objects.get(user= req.user, id = pid)
    if req.method == "GET":
        return render(req,"addAddress.html",{"update_address":address})
    else:
        address.address = req.POST["address"]
        address.zipcode = req.POST["zip"]
        address.phone = req.POST["phone"]
        address.save()
        return redirect("address")
    
def deleteAddress(req,pid):
    address = Address.objects.get(user= req.user, id = pid)
    address.delete()
    return redirect("address")

def buy(req,prod_id):
    oid = random.randrange(1000,9999)
    oid = str(oid)
    prod = Product.objects.get(product_id = prod_id)
    amount = prod.price
    o = Order.objects.create(order_id = oid,product = prod,quantity =1,user = req.user)
    client = razorpay.Client(auth=("rzp_test_GWWK3HBmr4C4Ng", "4UxKj0SL7WKQqjjWWnmHachl"))
    data ={'amount':amount * 100,"currency":"INR","receipt":oid}
    payment = client.order.create(data = data)
    context = {}
    context['data'] = payment
    orders = Order.objects.filter(user=req.user,is_completed = False)
    msg = f"Order Details: Order id:{oid}, Price:{amount}"
    send_mail(
        "Order Placed Successfully",
        msg,
        "jessica.dias@itvedant.com",
        [req.user.email],
        fail_silently=False,
    )
    orders.update(is_completed = True)
    return render(req,"payment.html",context)






""" def sendUserMail():
    
    orders = Order.objects.filter(user = req.user,is_completed = False)
    total_price = 0
    for x in orders:
        total_price += (x.product.price * x.quantity)
        oid = x.order_id

    msg = f"Order Details: Order id:{oid}, Price:{total_price}"
    send_mail(
    "Order Placed Successfully",
    "msg",
    "jessica.dias@itvedant.com",
    ["jessica.dias@itvedant.com"],
    fail_silently=False,
)
    return HttpResponse("Mail sent Successfully") """