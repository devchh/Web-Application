from shop import app, db
from .models import Product, User, Order, OrderItem, Customer
from flask import render_template, flash, session, redirect, url_for, request, json
from .form_helper import FormHelper
from .forms import *
import os

#PRODUCT_UPLOAD_FOLDER = 'static/product_pics'
# Needs actual location when saving file
PROFILE_UPLOAD_FOLDER = 'shop/static/profile_pics'
default_pic = 'blank-user.png'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
form_helper = FormHelper(PROFILE_UPLOAD_FOLDER, ALLOWED_EXTENSIONS)

def get_orders_into_display_format(user_id):
    # Get customers associated with user_id
    user_customers = db.session.query(Customer).join(User).filter(User.id == user_id).all()
    # Get orders assoicated with user customers
    user_customer_orders = [db.session.query(Order).join(Customer).filter(Customer.id == user_customer.id).all() for user_customer in user_customers]
    orders = {}
    for customer_orders in user_customer_orders:
        # Loops through all the orders for a specific customer
        for order in customer_orders:
            order_num = order.id
            customer = Customer.query.get(order_num)
            orders[order_num] = {}
            items = db.session.query(OrderItem).join(Order).filter(Order.id == order_num).all()
            item_list = []
            for item in items:
                # Add stuff for discount here if functionality is added
                product = Product.get_product_from_id(item.product_id)
                #orders[order_num][product] = item
                item_list.append({"product": product, "item": item})

            # FORM OF orders[order_num] = {"customer": customer, "items"=[{"product": product, "item": item"} for each item]}
            orders[order_num] = {"customer": customer, "items": item_list}
            
    return orders

def get_order_items(cart):
    # format wanted is [{"product_id": , "price": , "quantity": , "discount": }, {}]
    items = []
    for product_id, quantity in cart.items():
        product = Product.get_product_from_id(product_id)
        # No discount yet but if there is one add here
        discount = None
        if discount is None:
            items.append({"product_id": product.id, "price": product.price, "quantity": quantity, "discount": discount})
    return items
                
def get_cart():
    cart = []
    if 'cart' in session:
        cart = {Product.get_product_from_id(product_id): int(quantity) for product_id, quantity in session['cart'].items()}
    return cart

def get_cart_total(cart):
    total = 0
    for product, quantity in cart.items():
        total += (product.price * quantity)
    return total

def get_order_as_json():
    if 'cart' in session:
        return {"order_items": [{"product_id": product_id, "quantity": quantity} for product_id, quantity in session['cart'].items()]}
    else:
        return None
    
def checkIfQueryMet(query, text):
    if text[:len(query)].lower() == query.lower():
        return True
    else:
        return False

@app.route('/', methods=["GET", "POST"])
def index():
    apply_sort = False
    apply_search = False
    sort_type = None
    search_query = None
    if 'cart' not in session:
        session['cart'] = {}
    if request.method == "POST":
        if 'SortBar' in request.form:
            apply_sort = True
            sort_type = request.form['SortBar']
        elif 'SearchInput' in request.form:
            apply_search = True
            search_query = request.form['SearchInput']
        else:
            quantity, product_id = None, None
            if 'quantity' in request.form:
                quantity = request.form['quantity']
            if 'product_id' in request.form:
                product_id = request.form['product_id']
            if quantity is not None and product_id is not None:
                if product_id in session['cart']:
                    session['cart'][product_id] = int(session['cart'][product_id]) + int(quantity)
                else:
                    session['cart'][product_id] = quantity
    if apply_sort:
        if sort_type == "Price":
            products = Product.query.order_by(Product.price).all()
        elif sort_type == "Standard":
            products = Product.query.all()
        elif sort_type == "Name":
            products = Product.query.order_by(Product.name).all()
    elif apply_search:
        products = Product.query.filter(Product.name.ilike("%"+search_query+"%"))
    else:
        products = Product.query.all()
    return render_template("index.html", products=products)


@app.route('/logout')
def logout():
    session.pop('logged')
    return redirect(url_for('index'))
    
@app.route('/search/<query>')
def search(query):
    #points = {"products": [{"name": product} for product in products if query.lower() in product.lower()]}
    products = Product.query.filter(Product.name.ilike(query+"%"))
    points = {"products": [{"name": product.name, "id":product.id} for product in products]}

    return json.dumps(points)

@app.route('/orders')
def orders():
    orders = db.session.query(Order).all()
    print(orders)
    return "slut"

@app.route('/productPage/<product_id>/<product_name>', methods=["GET", "POST"])
def productPage(product_id, product_name):
    if request.method == "POST":
        product_id = None, None
        quantity = 1
        if 'product_id' in request.form:
            product_id = request.form['product_id']
        if product_id is not None:
            if product_id in session['cart']:
                session['cart'][product_id] = int(session['cart'][product_id]) + int(quantity)
            else:
                session['cart'][product_id] = quantity
    product = Product.get_product_from_id(int(product_id))
    return render_template("productPage.html", product=product)

@app.route('/cart', methods=["GET", "POST"])
def cart():
    if request.method == "POST":
        if 'Clearcart' in request.form:
            # Clear cart
            session['cart'] = {}
        else:
            # Update cart
            quantity, product_id = None, None
            if 'quantity' in request.form:
                quantity = request.form['quantity']
            if 'product_id' in request.form:
                product_id = request.form['product_id']
            if quantity is not None and product_id is not None:
                if product_id in session['cart']:
                    if int(quantity) <= 0:
                        session['cart'].pop(product_id)
                    else:
                        session['cart'][product_id] = quantity
    cart = get_cart()
    num_of_items = len(cart)
    total = get_cart_total(cart)
    
    return render_template("cart.html", cart=cart, total=total, num_of_items=num_of_items)

@app.route('/checkout/info', methods=["GET", "POST"])
def checkout_info():
    form = CheckoutInfoForm(request.form)
    if request.method == 'POST' and form.validate():
        checkout_info = {"first_name":form.first_name.data, "surname":form.surname.data, "email":form.email.data, \
                         "number":form.phone_number.data, "country":form.country.data, "address":form.address.data, \
                         "apartment":form.apartment.data, "city":form.city.data, "postcode":form.postcode.data}
        session["checkout_info"] = checkout_info
        return redirect(url_for('checkout_shipping'))

    cart = get_cart()
    total = get_cart_total(cart)
    
    return render_template("checkout_info.html", form=form, cart=cart, total=total)

@app.route('/checkout/shipping', methods=["GET", "POST"])
def checkout_shipping():
    form = CheckoutShippingForm(request.form)
    if request.method == 'POST' and form.validate():
        shipping_info = {"shipping_type": form.shipping_type.data}
        session["checkout_shipping"] = shipping_info
        return redirect(url_for('checkout_payment'))
    
    return render_template("checkout_shipping.html", form=form)

@app.route('/checkout/payment', methods=["GET", "POST"])
def checkout_payment():
    form = CheckoutPaymentForm(request.form)
    items = None
    if request.method == 'POST' and form.validate():
        checkout_payment = {"card_number":form.card_number.data, "name_on_card":form.name_on_card.data, "expiry_date":form.expiry_date.data, "csv":form.csv.data}
        session["checkout_payment"] = checkout_payment
        # Check that all the relevant info is available in session
        # in case page is reached without previous steps
        if {'checkout_info', 'checkout_shipping', 'checkout_payment'} <= set(session):
            checkout_info = session['checkout_info']
            checkout_shipping = session['checkout_shipping']
            checkout_payment = session['checkout_payment']
            if 'cart' in session:
                cart = session['cart']
                if len(cart) > 0:
                    items = get_order_items(cart)
            if 'logged' in session:
                user = User.get_user_from_username(session['username'])
                if user is not None:
                    if items is not None:
                        customer_id = Customer.add_customer(user.id, checkout_info['first_name'], checkout_info['surname'], checkout_info['email'], checkout_info['number'], checkout_info['address'], checkout_info['apartment'], checkout_info['country'], checkout_info['city'], checkout_info['postcode'], checkout_payment['card_number'], checkout_payment['name_on_card'], checkout_payment['expiry_date'], checkout_payment['csv'])
                        Order.add_order(customer_id, items, checkout_shipping["shipping_type"])
                        #order_id = Order.add_order(user.id, items)
                        flash('Order successfull')
                        return redirect(url_for('profile'))
            else:
                # If not logged in
                if items is not None:
                    customer_id = Customer.add_customer(None, checkout_info['first_name'], checkout_info['surname'], checkout_info['email'], checkout_info['number'], checkout_info['address'], checkout_info['apartment'], checkout_info['country'], checkout_info['city'], checkout_info['postcode'], checkout_payment['card_number'], checkout_payment['name_on_card'], checkout_payment['expiry_date'], checkout_payment['csv'])
                    Order.add_order(customer_id, items, checkout_shipping["shipping_type"])
                    flash('Order successfull')
                    return redirect(url_for('index'))
    
    return render_template("checkout_payment.html", form=form)

# ACCOUNT RELATED ROUTES

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm(request.form)
    if request.method == 'POST' and form.validate():
        username = form.username.data
        password = form.password.data
        # Check for valid login here
        user = User.get_user_from_username(username)
        if user is not None:
            if user.verify_password(password):
                session['logged'] = True
                session['username'] = username
                return redirect(url_for('index'))
    return render_template('login.html', form=form)

@app.route('/create_account', methods=['GET', 'POST'])
def create_account():
    form = CreateAccountForm(request.form)
    if request.method == 'POST' and form.validate():
        # TODO - ADD OTHER ACCOUNT DETAILS TO DATABASE
        username = form.username.data
        password = form.password.data
        file = request.files[form.profile_pic.name]
        filename = file.filename
        # Check if an account with this username is already created
        user = User.get_user_from_username(username)
        if user is None:
            if filename == "" or filename is None:  
                User.register(username, password, default_pic)
            else:
                profile_pic = form_helper.upload_file(file)
                User.register(username, password, profile_pic)

            flash('Account created successfully')
            return redirect(url_for('login'))
        else:
            flash('Account with this username already exists')

    return render_template('create_account.html', form=form)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    form = EditProfileForm(request.form)
    current_pic = None
    orders = None
    if 'logged' in session:
        user = User.get_user_from_username(session['username'])

        orders = get_orders_into_display_format(user.id)
            
        current_pic = user.profile_pic
        if request.method == 'POST' and form.validate:
            file = request.files[form.profile_pic.name]
            profile_pic = form_helper.upload_file(file)
            
            if profile_pic is not None:
                # Store old profile pic
                old_profile_pic = user.profile_pic

                # Add new profile pic
                User.update_profile_pic(user, profile_pic)

                # Remove old profile pic
                old_pic_location = PROFILE_UPLOAD_FOLDER+"/"+old_profile_pic
                if os.path.exists(old_pic_location):
                    if old_profile_pic != default_pic:
                        os.remove(old_pic_location)
                else:
                    print("The file does not exist")

                # Redirect to refresh page so current pic no shows up on profile
                return redirect(url_for('profile'))
            
        return render_template('profile.html', form=form, orders=orders, current_pic=current_pic, logged=("logged" in session), user=user)
        
    return redirect(url_for('login'))

