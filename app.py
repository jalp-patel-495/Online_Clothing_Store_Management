from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import random
import string
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash


# ========== APP SETUP ==========
app = Flask(__name__)

app.config['SECRET_KEY'] = 'cloth-store-final-2026'

# Use SQLite - Simple and error-free
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:@localhost/cloth_store'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ========== DATABASE MODELS ==========
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Product(db.Model):
    __tablename__ = 'products'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, nullable=False)
    discount = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(255))

    category_id = db.Column(
        db.Integer,
        db.ForeignKey('categories.id'),
        nullable=False
    )

    gender = db.Column(db.String(20))
    size = db.Column(db.String(10))
    color = db.Column(db.String(30))
    stock = db.Column(db.Integer)
    image_url = db.Column(db.String(255))

    def get_discounted_price(self):
        if self.discount:
            return round(self.price - (self.price * self.discount / 100), 2)
        return self.price

    category = db.relationship('Category', backref='products')
    images = db.relationship('ProductImage', backref='product', cascade='all, delete-orphan')

    @property
    def discounted_price(self):
        if self.discount and self.discount > 0:
            return round(self.price - (self.price * self.discount / 100), 2)
        return self.price

class ProductImage(db.Model):
    __tablename__ = 'product_images'
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)

class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

# class Order(db.Model):
#     __tablename__ = 'orders'
#     id = db.Column(db.Integer, primary_key=True)

#     user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
#     user = db.relationship('User', backref='orders')   # ✅ ADD THIS

#     order_number = db.Column(db.String(20), unique=True, nullable=False)
#     id = db.Column(db.Integer, primary_key=True)
#     total_amount = db.Column(db.Float, nullable=False)
#     status = db.Column(db.String(20), default='Pending')
#     payment_status = db.Column(db.String(20), default='Pending')
#     payment_method = db.Column(db.String(50))
#     shipping_address = db.Column(db.Text)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Order(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    user = db.relationship('User', backref='orders')

    order_number = db.Column(db.String(20), unique=True, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='Pending')
    payment_status = db.Column(db.String(20), default='Pending')
    payment_method = db.Column(db.String(50))
    shipping_address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # ✅ ADD THIS (MOST IMPORTANT)
    order_items = db.relationship(
        'OrderItem',
        backref='order',
        lazy=True,
        cascade='all, delete-orphan'
    )

    @property
    def total_items(self):
        return sum(item.quantity for item in self.order_items)



class Category(db.Model):
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)


# class OrderItem(db.Model):
#     __tablename__ = 'order_items'
#     id = db.Column(db.Integer, primary_key=True)
#     order_id = db.Column(db.Integer, nullable=False)
#     product_id = db.Column(db.Integer, nullable=False)
#     quantity = db.Column(db.Integer, nullable=False)
#     price_at_time = db.Column(db.Float, nullable=False)
#     product_name = db.Column(db.String(100), nullable=False)

class OrderItem(db.Model):
    __tablename__ = 'order_items'

    id = db.Column(db.Integer, primary_key=True)

    # ✅ ADD ForeignKey
    order_id = db.Column(
        db.Integer,
        db.ForeignKey('orders.id'),
        nullable=False
    )

    product_id = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price_at_time = db.Column(db.Float, nullable=False)
    product_name = db.Column(db.String(100), nullable=False)


class Wishlist(db.Model):
    __tablename__ = 'wishlist'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)

    product = db.relationship('Product', backref='wishlisted')



# ========== HELPER FUNCTIONS ==========
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template('product_detail.html', product=product)


# @app.route('/add_to_cart/<int:product_id>')
# def add_to_cart(product_id):
#     cart = session.get('cart', [])
#     cart.append(product_id)
#     session['cart'] = cart
#     return redirect(url_for('cart'))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first', 'warning')
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

def generate_order_number():
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f'ORD-{timestamp}-{random_str}'

# ========== ALL ROUTES DEFINED HERE ==========
@app.route('/')
def index():
    products = Product.query.limit(8).all()
    return render_template('index.html', products=products)

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not username or not email or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('register'))
        
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('register'))
        
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already exists', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/add_to_wishlist/<int:product_id>')
@login_required
def add_to_wishlist(product_id):
    existing = Wishlist.query.filter_by(
        user_id=session['user_id'],
        product_id=product_id
    ).first()

    if not existing:
        wishlist_item = Wishlist(
            user_id=session['user_id'],
            product_id=product_id
        )
        db.session.add(wishlist_item)
        db.session.commit()

    flash("Added to wishlist ❤️", "success")
    return redirect(request.referrer or url_for('index'))


@app.route('/wishlist')
@login_required
def wishlist():
    items = Wishlist.query.filter_by(user_id=session['user_id']).all()
    return render_template('wishlist.html', items=items)

@app.context_processor
def inject_counts():
    wishlist_count = 0
    cart_count = 0

    if 'user_id' in session:
        wishlist_count = Wishlist.query.filter_by(
            user_id=session['user_id']
        ).count()

        cart_count = Cart.query.filter_by(
            user_id=session['user_id']
        ).count()

    return dict(
        wishlist_count=wishlist_count,
        cart_count=cart_count
    )


@app.route('/remove_wishlist/<int:id>')
@login_required
def remove_wishlist(id):
    item = Wishlist.query.get_or_404(id)

    if item.user_id == session['user_id']:
        db.session.delete(item)
        db.session.commit()

    return redirect(url_for('wishlist'))


@app.route('/products')
def products():
    gender = request.args.get('gender', 'all')
    category = request.args.get('category', 'all')

    query = Product.query

    if gender != 'all':
        query = query.filter(Product.gender == gender)

    if category != 'all':
        query = query.filter(Product.category_id == int(category))  # ✅ FIX

    products_list = query.all()
    categories = Category.query.all()

    return render_template(
        'products.html',
        products=products_list,
        categories=categories,
        selected_gender=gender,
        selected_category=int(category) if category != 'all' else None
    )

@app.route('/add_to_cart', methods=['POST'])
@login_required
def add_to_cart():
    """Add product to cart"""
    try:
        product_id = int(request.form.get('product_id', 0))
        quantity = int(request.form.get('quantity', 1))
        
        product = Product.query.get_or_404(product_id)
        
        # Check stock
        if quantity > product.stock:
            flash(f'Only {product.stock} items available', 'warning')
            quantity = product.stock
        
        # Check if already in cart
        cart_item = Cart.query.filter_by(
            user_id=session['user_id'], 
            product_id=product_id
        ).first()
        
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = Cart(
                user_id=session['user_id'],
                product_id=product_id,
                quantity=quantity
            )
            db.session.add(cart_item)
        
        db.session.commit()
        flash(f'{product.name} added to cart!', 'success')
        
    except Exception as e:
        flash('Error adding to cart', 'danger')
    
    return redirect(request.referrer or url_for('index'))

@app.route('/cart')
@login_required
def cart():
    """View cart"""
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    
    # Get product details and calculate total
    cart_details = []
    total = 0
    
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            item_price = product.discounted_price
            item_total = item_price * item.quantity

            total += item_total
            
            cart_details.append({
                'id': item.id,
                'product': product,
                'quantity': item.quantity,
                'item_price': item_price,      # ✅ item_price
                'item_total': item_total       # ✅ item_total
            })
    
    return render_template('cart.html', 
                         cart_items=cart_details, 
                         total=round(total, 2))

@app.route('/update_cart', methods=['POST'])
@login_required
def update_cart():
    """Update cart item quantity"""
    try:
        cart_item_id = int(request.form.get('cart_item_id', 0))
        quantity = int(request.form.get('quantity', 1))
        
        cart_item = Cart.query.get_or_404(cart_item_id)
        
        if cart_item.user_id != session['user_id']:
            flash('Unauthorized action', 'danger')
            return redirect(url_for('cart'))
        
        if quantity <= 0:
            db.session.delete(cart_item)
            flash('Item removed from cart', 'info')
        else:
            product = Product.query.get(cart_item.product_id)
            if product and quantity > product.stock:
                 flash(f'Only {product.stock} items available', 'warning')
                 quantity = product.stock
            
            cart_item.quantity = quantity
        
        db.session.commit()
        
    except Exception as e:
        flash('Error updating cart', 'danger')
    
    return redirect(url_for('cart'))

@app.route('/remove_from_cart/<int:cart_item_id>')
@login_required
def remove_from_cart(cart_item_id):
    """Remove item from cart"""
    cart_item = Cart.query.get_or_404(cart_item_id)
    
    if cart_item.user_id != session['user_id']:
        flash('Unauthorized action', 'danger')
        return redirect(url_for('cart'))
    
    db.session.delete(cart_item)
    db.session.commit()
    
    flash('Item removed from cart', 'info')
    return redirect(url_for('cart'))

@app.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    """Checkout page"""
    cart_items = Cart.query.filter_by(user_id=session['user_id']).all()
    
    if not cart_items:
        flash('Your cart is empty', 'warning')
        return redirect(url_for('cart'))

    # Validate stock before proceeding
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product and item.quantity > product.stock:
             flash(f'Stock changed for {product.name}. Only {product.stock} available.', 'warning')
             # Auto-fix quantity
             item.quantity = product.stock
             db.session.commit()
             return redirect(url_for('cart'))

    
    # Calculate total
    total = 0
    cart_details = []
    
    for item in cart_items:
        product = Product.query.get(item.product_id)
        if product:
            item_total = product.discounted_price * item.quantity
            total += item_total
            cart_details.append({
                'product': product,
                'quantity': item.quantity,
                'item_total': item_total
            })
    
    # if request.method == 'POST':
    #     shipping_address = request.form.get('shipping_address', '').strip()
    #     payment_method = request.form.get('payment_method', 'Cash on Delivery')
        
    #     if not shipping_address:
    #         flash('Shipping address is required', 'danger')
    #         return render_template('checkout.html', 
    #                              cart_items=cart_details, 
    #                              total=round(total, 2))

    # In the checkout route, update the POST section slightly:

    if request.method == 'POST':
        shipping_address = request.form.get('shipping_address', '').strip()
        payment_method = request.form.get('payment_method', 'Cash on Delivery')
        
        # Add payment validation (optional for demo)
        if payment_method in ['Credit Card', 'Debit Card']:
            card_number = request.form.get('card_number', '').strip()
            # Demo validation - in real app, you'd use proper validation
            # if card_number and not card_number.replace(' ', '').startswith('4'):
            #     flash('For demo: Use card starting with 4111...', 'info')
        
    # Continue with existing code...
        
        try:
            # Create order
            order_number = generate_order_number()
            order = Order(
                user_id=session['user_id'],
                order_number=order_number,
                total_amount=round(total, 2),
                payment_method=payment_method,
                shipping_address=shipping_address,
                status='Processing',
                payment_status='Completed'
            )
            
            db.session.add(order)
            db.session.commit()
            
            # Create order items
            for item in cart_items:
                product = Product.query.get(item.product_id)
                if product:
                    order_item = OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=item.quantity,
                    price_at_time=product.discounted_price,
                    product_name=product.name)
                    db.session.add(order_item)
                    
                    # Update stock
                    product.stock -= item.quantity
            
            # Clear cart
            Cart.query.filter_by(user_id=session['user_id']).delete()
            
            db.session.commit()
            
            # Save to order history
            product_names = [f"{item['product'].name} (Qty: {item['quantity']})" for item in cart_details]
            products_str = ", ".join(product_names)
            current_user = session.get('username', 'Guest')
            
            with open('order_history.txt', 'a') as f:
                f.write(f"\n{'='*40}\n")
                f.write(f"Order ID:   {order_number}\n")
                f.write(f"Customer:   {current_user}\n")
                f.write(f"Items:      {products_str}\n")
                f.write(f"Total:      rs {total:.2f}\n")
                f.write(f"Date:       {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"{'='*40}\n")
            
            flash('Order placed successfully!', 'success')
            return redirect(url_for('order_confirmation', order_id=order.id))
            
        except Exception as e:
            db.session.rollback()
            flash('Error processing order', 'danger')
            return redirect(url_for('cart'))
    
    return render_template('checkout.html', 
                         cart_items=cart_details, 
                         total=round(total, 2))

@app.route('/order_confirmation/<int:order_id>')
@login_required
def order_confirmation(order_id):
    """Order confirmation page"""
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != session['user_id'] and not session.get('is_admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    
    return render_template('order_confirmation.html', order=order)

@app.route('/orders')
@login_required
def orders():
    """User orders history"""
    user_orders = Order.query.filter_by(user_id=session['user_id'])\
                            .order_by(Order.created_at.desc())\
                            .all()
    return render_template('orders.html', orders=user_orders)

@app.route('/cancel_order/<int:order_id>')
@login_required
def cancel_order(order_id):
    """Cancel order"""
    order = Order.query.get_or_404(order_id)
    
    if order.user_id != session['user_id']:
        flash('Unauthorized action', 'danger')
        return redirect(url_for('orders'))
    
    if order.status not in ['Cancelled', 'Shipped', 'Delivered']:
        order.status = 'Cancelled'
        
        # Restore stock
        order_items = OrderItem.query.filter_by(order_id=order.id).all()
        for item in order_items:
            product = Product.query.get(item.product_id)
            if product:
                product.stock += item.quantity
        
        db.session.commit()
        flash('Order cancelled successfully', 'success')
    else:
        flash('Cannot cancel this order', 'warning')
    
    return redirect(url_for('orders'))

# ========== ADMIN ROUTES ==========
@app.route('/admin')
@admin_required
def admin():
    """Admin dashboard"""
    total_orders = Order.query.count()
    total_users = User.query.count()
    total_products = Product.query.count()
    
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    return render_template('admin.html',
                         total_orders=total_orders,
                         total_users=total_users,
                         total_products=total_products,
                         recent_orders=recent_orders)

@app.route('/admin/products')
@admin_required
def admin_products():
    """Admin: View all products"""
    products = Product.query.all()
    return render_template('admin_products.html', products=products)

@app.route('/admin/add_product', methods=['GET', 'POST'])
@admin_required
def add_product():

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        price = float(request.form.get('price', 0))
        discount = int(request.form.get('discount', 0))
        category_id = request.form.get('category_id')   # ✅ FIX
        gender = request.form.get('gender', '')
        size = request.form.get('size', '')
        color = request.form.get('color', '').strip()
        stock = int(request.form.get('stock', 0))
        
        # Handle multiple images
        image_urls = request.form.getlist('image_urls')
        image_urls = [url.strip() for url in image_urls if url.strip()]
        
        main_image_url = image_urls[0] if image_urls else 'https://via.placeholder.com/300x400'

        # ✅ FIXED validation
        if not name or price <= 0 or not category_id:
            flash('Please fill all required fields', 'danger')
            return redirect(url_for('add_product'))

        product = Product(
            name=name,
            description=description,
            price=price,
            discount=discount,
            category_id=category_id,   # ✅ FIX
            gender=gender,
            size=size,
            color=color,
            stock=stock,
            image_url=main_image_url
        )

        db.session.add(product)
        db.session.commit()
        
        # Save all images
        for url in image_urls:
            new_img = ProductImage(product_id=product.id, image_url=url)
            db.session.add(new_img)
        
        db.session.commit()

        flash('Product added successfully', 'success')
        return redirect(url_for('admin_products'))

    categories = Category.query.all()
    return render_template('add_product.html', categories=categories)

@app.route('/admin/orders')
@admin_required
def admin_orders():
    """Admin: View all orders"""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin_orders.html', orders=orders)


@app.route('/admin/users')
@admin_required
def view_all_users():
    """Admin: View all users"""
    users = User.query.all()
    return render_template('admin_users.html', users=users)


# ========== API ROUTES ==========
@app.route('/api/cart_count')
@login_required
def cart_count():
    """API: Get cart item count"""
    count = Cart.query.filter_by(user_id=session['user_id']).count()
    return jsonify({'count': count})

from flask import send_file

@app.route('/view_order_history')
def view_order_history():
    try:
        return send_file(
            "order_history.txt",
            as_attachment=False,
            mimetype='text/plain'
        )
    except FileNotFoundError:
        return "order_history.txt not found", 404

# @app.route('/admin/edit-product/<int:product_id>', methods=['GET', 'POST'])
# def edit_product(product_id):
#     product = Product.query.get_or_404(product_id)

#     if request.method == 'POST':
#         product.name = request.form['name']
#         product.price = request.form['price']
#         product.description = request.form['description']
#         # product.category = request.form['category']
#         product.category_id = int(request.form['category_id'])
#         # category = Category.query.get(request.form['category_id'])
#         # product.category = category



#         db.session.commit()
#         flash("Product updated successfully!", "success")
#         return redirect(url_for('admin_products'))

#     return render_template('edit_product.html', product=product)

@app.route('/admin/edit-product/<int:product_id>', methods=['GET', 'POST'])
@admin_required
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    categories = Category.query.all()

    if request.method == 'POST':
        product.name = request.form.get('name')
        product.price = float(request.form.get('price', 0))
        product.description = request.form.get('description')
        product.size = request.form.get('size')
        product.color = request.form.get('color')
        product.stock = int(request.form.get('stock', 0))
        product.discount = int(request.form.get('discount', 0))
        product.gender = request.form.get('gender')

        category_id = request.form.get('category_id')
        if not category_id:
            flash("Please select a category", "danger")
            return redirect(request.url)

        product.category_id = int(category_id)

        db.session.commit()
        flash("Product updated successfully!", "success")
        return redirect(url_for('admin_products'))

    return render_template(
        'edit_product.html',
        product=product,
        categories=categories
    )


@app.route('/admin/delete-product/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    db.session.delete(product)
    db.session.commit()

    flash("Product deleted successfully!", "danger")
    return redirect(url_for('admin_products'))



# ========== DATABASE INITIALIZATION ==========
def init_database():
    """Initialize database with sample data"""
    with app.app_context():
        # Create all tables
        db.create_all()
        print("✓ Database tables created")
        
        # Add admin user
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email='admin@clothstore.com',
                is_admin=True
            )
            admin.set_password('admin123')
            db.session.add(admin)
            print("✓ Admin user created: admin / admin123")
        
            
            for product in products:
                db.session.add(product)
            
            print("✓ 5 sample products added")
        
        db.session.commit()

# ========== RUN APPLICATION ==========
if __name__ == '__main__':
    import logging
    from flask import cli
    
    # Suppress Werkzeug logs
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    
    # Suppress Flask server banner
    cli.show_server_banner = lambda *_: None

    # print("=" * 60)
    # print("CLOTH STORE - ERROR FREE VERSION")
    # print("=" * 60)
    # print("Features:")
    # print("• User Registration & Login")
    # print("• Product Browsing with Filters")
    # print("• Shopping Cart")
    # print("• Checkout & Orders")
    # print("• Admin Panel")
    # print("• Order History")
    # print("• Wishlist Management")
    # print("=" * 60)
    
    # Initialize database
    # init_database()
    
    print("\nStarting application...")
    print("URL: http://localhost:5001")
    # print("Admin login: username='admin', password='admin123'")
    print("=" * 60)
    
    # Run app
    app.run(debug=True, port=5001, use_reloader=True)
