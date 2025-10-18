from flask import session, render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from replit_auth import require_login, make_replit_blueprint
from flask_login import current_user
from models import Category, Product, CartItem, QuoteRequest, QuoteItem, Order, OrderItem, product_categories, User
from forms import QuoteRequestForm, CheckoutForm, AccountUpdateForm
from sqlalchemy import or_, func, and_
from datetime import datetime
import uuid
import logging
from email_utils import send_order_notification

# Import admin routes
import admin_routes

app.register_blueprint(make_replit_blueprint(), url_prefix="/auth")

# Make session permanent
@app.before_request
def make_session_permanent():
    session.permanent = True

@app.route('/')
def index():
    # Get featured categories
    featured_categories = Category.query.filter_by(is_featured=True).order_by(Category.sort_order).limit(8).all()
    
    # Get featured products (only show products with both cost and price > 0)
    featured_products = Product.query.filter_by(is_featured=True).filter(
        Product.cost > 0,
        Product.price > 0
    ).limit(12).all()
    
    # Get main categories (no parent)
    main_categories = Category.query.filter_by(parent_id=None).order_by(Category.sort_order).all()
    
    return render_template('index.html', 
                         featured_categories=featured_categories,
                         featured_products=featured_products,
                         main_categories=main_categories)

@app.route('/category/<slug>')
def category_view(slug):
    category = Category.query.filter_by(slug=slug).first_or_404()
    
    # Get subcategories (direct children)
    subcategories = Category.query.filter_by(parent_id=category.id).order_by(Category.sort_order).all()
    
    # Get sub-subcategories (grandchildren) - only if this is a second-level category
    sub_subcategories = []
    if subcategories:
        # If we have subcategories, collect all their children as well
        for sub in subcategories:
            sub_subs = Category.query.filter_by(parent_id=sub.id).order_by(Category.sort_order).all()
            sub_subcategories.extend(sub_subs)
    
    # Build complete list of category IDs for product filtering
    category_ids = [category.id]  # Always include current category
    
    if subcategories:
        # Add all subcategories
        category_ids.extend([sub.id for sub in subcategories])
        
        # Add all sub-subcategories  
        if sub_subcategories:
            category_ids.extend([subsub.id for subsub in sub_subcategories])
    
    # Get products from current category and all its descendant categories (only show products with both cost and price > 0)
    products = Product.query.join(product_categories).filter(
        product_categories.c.category_id.in_(category_ids),
        Product.cost > 0,
        Product.price > 0
    )
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 24
    products = products.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('category.html', 
                         category=category, 
                         subcategories=subcategories,
                         sub_subcategories=sub_subcategories,
                         products=products)

@app.route('/product/<slug>')
def product_view(slug):
    product = Product.query.filter_by(slug=slug).first_or_404()
    
    # Get related products using intelligent matching
    related_products = []
    
    # Strategy 1: Find products with similar names (keyword matching)
    if product.name:
        # Extract key words from product name (skip common words)
        skip_words = ['the', 'and', 'or', 'with', 'without', 'for', 'of', 'in', 'on', 'at', 'by', 'from']
        product_words = [word.lower() for word in product.name.split() 
                        if len(word) > 2 and word.lower() not in skip_words]
        
        if product_words:
            # Find products that share keywords in their name
            keyword_matches = Product.query.filter(
                Product.id != product.id,
                Product.cost > 0,
                Product.price > 0,
                or_(*[Product.name.ilike(f'%{word}%') for word in product_words[:3]])  # Use top 3 keywords
            ).filter(
                # Prioritize products with images
                or_(
                    and_(Product.large_image_url.isnot(None), Product.large_image_url != ''),
                    and_(Product.thumb_image_url.isnot(None), Product.thumb_image_url != '')
                )
            ).limit(4).all()
            
            related_products.extend(keyword_matches)
    
    # Strategy 2: If we don't have enough keyword matches, get from same category with images
    if len(related_products) < 4 and product.primary_category_id:
        remaining_needed = 4 - len(related_products)
        existing_ids = [p.id for p in related_products]
        
        category_matches = Product.query.filter(
            Product.primary_category_id == product.primary_category_id,
            Product.id != product.id,
            Product.cost > 0,
            Product.price > 0,
            ~Product.id.in_(existing_ids) if existing_ids else True
        ).filter(
            # Prioritize products with images
            or_(
                and_(Product.large_image_url.isnot(None), Product.large_image_url != ''),
                and_(Product.thumb_image_url.isnot(None), Product.thumb_image_url != '')
            )
        ).limit(remaining_needed).all()
        
        related_products.extend(category_matches)
    
    # Strategy 3: If still not enough, get from manufacturer with images
    if len(related_products) < 4 and product.manufacturer_id:
        remaining_needed = 4 - len(related_products)
        existing_ids = [p.id for p in related_products]
        
        manufacturer_matches = Product.query.filter(
            Product.manufacturer_id == product.manufacturer_id,
            Product.id != product.id,
            Product.cost > 0,
            Product.price > 0,
            ~Product.id.in_(existing_ids) if existing_ids else True
        ).filter(
            # Prioritize products with images
            or_(
                and_(Product.large_image_url.isnot(None), Product.large_image_url != ''),
                and_(Product.thumb_image_url.isnot(None), Product.thumb_image_url != '')
            )
        ).limit(remaining_needed).all()
        
        related_products.extend(manufacturer_matches)
    
    # Limit to 4 related products
    related_products = related_products[:4]
    
    return render_template('product.html', 
                         product=product,
                         related_products=related_products)

@app.route('/search')
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return redirect(url_for('index'))
    
    # Search in product names and descriptions (only show products with both cost and price > 0)
    products = Product.query.filter(
        Product.cost > 0,
        Product.price > 0,
        or_(
            Product.name.ilike(f'%{query}%'),
            Product.description.ilike(f'%{query}%'),
            Product.short_description.ilike(f'%{query}%')
        )
    )
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 24
    products = products.paginate(page=page, per_page=per_page, error_out=False)
    
    return render_template('search_results.html', 
                         products=products, 
                         query=query)

@app.route('/add_to_cart', methods=['POST'])
@require_login
def add_to_cart():
    product_id = request.form.get('product_id', type=int)
    quantity = request.form.get('quantity', 1, type=int)
    
    if not product_id:
        flash('Invalid product selected.', 'error')
        return redirect(request.referrer or url_for('index'))
    
    product = Product.query.get_or_404(product_id)
    
    # Check if item already in cart
    cart_item = CartItem.query.filter_by(
        user_id=current_user.id,
        product_id=product_id
    ).first()
    
    if cart_item:
        cart_item.quantity += quantity
        cart_item.updated_at = datetime.now()
    else:
        cart_item = CartItem(
            user_id=current_user.id,
            product_id=product_id,
            quantity=quantity
        )
        db.session.add(cart_item)
    
    db.session.commit()
    flash(f'{product.name} added to cart!', 'success')
    
    return redirect(request.referrer or url_for('product_view', slug=product.slug))

@app.route('/cart')
@require_login
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    total = 0
    for item in cart_items:
        total += float(item.product.price) * item.quantity
    
    return render_template('cart.html', cart_items=cart_items, total=total)

@app.route('/update_cart', methods=['POST'])
@require_login
def update_cart():
    item_id = request.form.get('item_id', type=int)
    quantity = request.form.get('quantity', type=int)
    
    if quantity and quantity > 0:
        cart_item = CartItem.query.filter_by(
            id=item_id,
            user_id=current_user.id
        ).first()
        
        if cart_item:
            cart_item.quantity = quantity
            cart_item.updated_at = datetime.now()
            db.session.commit()
            flash('Cart updated successfully!', 'success')
    
    return redirect(url_for('cart'))

@app.route('/remove_from_cart', methods=['POST'])
@require_login
def remove_from_cart():
    item_id = request.form.get('item_id', type=int)
    
    cart_item = CartItem.query.filter_by(
        id=item_id,
        user_id=current_user.id
    ).first()
    
    if cart_item:
        db.session.delete(cart_item)
        db.session.commit()
        flash('Item removed from cart!', 'success')
    
    return redirect(url_for('cart'))

@app.route('/checkout')
@require_login
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    
    if not cart_items:
        flash('Your cart is empty!', 'error')
        return redirect(url_for('cart'))
    
    total = sum(float(item.product.price) * item.quantity for item in cart_items)
    form = CheckoutForm()
    
    return render_template('checkout.html', 
                         cart_items=cart_items, 
                         total=total, 
                         form=form)

@app.route('/process_order', methods=['POST'])
@require_login
def process_order():
    form = CheckoutForm()
    
    if form.validate_on_submit():
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        
        if not cart_items:
            flash('Your cart is empty!', 'error')
            return redirect(url_for('cart'))
        
        # Calculate totals
        subtotal = sum(float(item.product.price) * item.quantity for item in cart_items)
        tax_amount = subtotal * 0.08  # 8% tax
        shipping_amount = 25.00 if subtotal < 500 else 0  # Free shipping over $500
        total_amount = subtotal + tax_amount + shipping_amount
        
        # Create order with secure token
        import secrets
        order = Order(
            user_id=current_user.id,
            order_number=f'ORD-{uuid.uuid4().hex[:8].upper()}',
            secure_token=secrets.token_urlsafe(32),
            subtotal=subtotal,
            tax_amount=0,
            shipping_amount=0,
            total_amount=subtotal,
            shipping_name=form.shipping_name.data,
            shipping_company=form.shipping_company.data,
            shipping_address=form.shipping_address.data,
            shipping_city=form.shipping_city.data,
            shipping_state=form.shipping_state.data,
            shipping_zip=form.shipping_zip.data,
            shipping_phone=form.shipping_phone.data,
            shipping_option=form.shipping_option.data
        )
        db.session.add(order)
        db.session.flush()  # Get the order ID
        
        # Create order items
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.price,
                total_price=float(cart_item.product.price) * cart_item.quantity
            )
            db.session.add(order_item)
        
        # Clear cart
        for cart_item in cart_items:
            db.session.delete(cart_item)
        
        db.session.commit()
        
        # Send order notification email
        try:
            user = User.query.get(current_user.id)
            send_order_notification(order, user)
            logging.info(f"Order notification email sent for order {order.order_number}")
        except Exception as e:
            logging.error(f"Failed to send order notification email: {str(e)}")
        
        flash(f'Order {order.order_number} placed successfully!', 'success')
        return redirect(url_for('account'))
    
    # If form validation fails
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(float(item.product.price) * item.quantity for item in cart_items)
    
    return render_template('checkout.html', 
                         cart_items=cart_items, 
                         total=total, 
                         form=form)

@app.route('/request_quote')
@require_login
def request_quote():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    form = QuoteRequestForm()
    
    # Pre-populate form with user data
    if current_user.first_name and current_user.last_name:
        form.contact_name.data = f"{current_user.first_name} {current_user.last_name}"
    if current_user.email:
        form.email.data = current_user.email
    if current_user.company_name:
        form.company_name.data = current_user.company_name
    if current_user.phone:
        form.phone.data = current_user.phone
    
    return render_template('quote_request.html', 
                         cart_items=cart_items, 
                         form=form)

@app.route('/submit_quote', methods=['POST'])
@require_login
def submit_quote():
    form = QuoteRequestForm()
    
    if form.validate_on_submit():
        cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
        
        if not cart_items:
            flash('Your cart is empty!', 'error')
            return redirect(url_for('cart'))
        
        # Create quote request
        quote_request = QuoteRequest(
            user_id=current_user.id,
            request_number=f'QUO-{uuid.uuid4().hex[:8].upper()}',
            notes=form.notes.data,
            special_requirements=form.special_requirements.data,
            delivery_date_needed=form.delivery_date_needed.data
        )
        db.session.add(quote_request)
        db.session.flush()  # Get the quote ID
        
        # Create quote items
        for cart_item in cart_items:
            quote_item = QuoteItem(
                quote_request_id=quote_request.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity
            )
            db.session.add(quote_item)
        
        # Clear cart
        for cart_item in cart_items:
            db.session.delete(cart_item)
        
        db.session.commit()
        
        flash(f'Quote request {quote_request.request_number} submitted successfully! We will contact you within 24 hours.', 'success')
        return redirect(url_for('account'))
    
    # If form validation fails
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    return render_template('quote_request.html', 
                         cart_items=cart_items, 
                         form=form)

@app.route('/account')
@require_login
def account():
    # Get user's orders
    orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    # Get user's quote requests
    quote_requests = QuoteRequest.query.filter_by(user_id=current_user.id).order_by(QuoteRequest.created_at.desc()).all()
    
    form = AccountUpdateForm()
    
    return render_template('account.html', 
                         orders=orders, 
                         quote_requests=quote_requests,
                         form=form)

@app.route('/update_account', methods=['POST'])
@require_login
def update_account():
    form = AccountUpdateForm()
    
    if form.validate_on_submit():
        current_user.first_name = form.first_name.data
        current_user.last_name = form.last_name.data
        current_user.company_name = form.company_name.data
        current_user.phone = form.phone.data
        current_user.updated_at = datetime.now()
        
        db.session.commit()
        flash('Account updated successfully!', 'success')
    
    return redirect(url_for('account'))

@app.route('/get_cart_count')
def get_cart_count():
    if current_user.is_authenticated:
        count = CartItem.query.filter_by(user_id=current_user.id).count()
        return jsonify({'count': count})
    return jsonify({'count': 0})

@app.context_processor
def inject_cart_count():
    if current_user.is_authenticated:
        cart_count = CartItem.query.filter_by(user_id=current_user.id).count()
    else:
        cart_count = 0
    return {'cart_count': cart_count}

@app.context_processor
def inject_categories():
    main_categories = Category.query.filter_by(parent_id=None).order_by(Category.sort_order).all()
    return {'main_categories': main_categories}

# Customer Order View (Public)
@app.route('/order/<secure_token>')
def customer_order_view(secure_token):
    order = Order.query.filter_by(secure_token=secure_token).first_or_404()
    return render_template('customer_order.html', order=order)

# Email Test Page
@app.route('/test_email', methods=['GET', 'POST'])
def test_email():
    import os
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    message = None
    
    if request.method == 'POST':
        try:
            from_email = request.form.get('from_email')
            subject = request.form.get('subject')
            body = request.form.get('body')
            to_email = os.environ.get('DEV_EMAIL', 'rpittman3@gmail.com')
            
            smtp_host = os.environ.get('SMTP_HOST')
            smtp_port = int(os.environ.get('SMTP_PORT', 587))
            smtp_user = os.environ.get('SMTP_USER')
            smtp_pass = os.environ.get('SMTP_PASS')
            
            logging.info(f"Attempting to send test email to {to_email}")
            logging.info(f"SMTP Host: {smtp_host}, Port: {smtp_port}")
            
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email
            msg['To'] = to_email
            
            part = MIMEText(body, 'plain')
            msg.attach(part)
            
            # Port 465 requires SSL, port 587 requires STARTTLS
            if smtp_port == 465:
                logging.info("Using SMTP_SSL for port 465")
                server = smtplib.SMTP_SSL(smtp_host, smtp_port)
                server.set_debuglevel(1)
            else:
                logging.info("Using SMTP with STARTTLS for port 587")
                server = smtplib.SMTP(smtp_host, smtp_port)
                server.set_debuglevel(1)
                server.starttls()
            
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
            server.quit()
            
            message = f"Email sent successfully to {to_email}!"
            logging.info(message)
            flash(message, 'success')
            
        except Exception as e:
            message = f"Error sending email: {str(e)}"
            logging.error(message)
            flash(message, 'error')
    
    default_from = os.environ.get('FROM_EMAIL', '')
    dev_email = os.environ.get('DEV_EMAIL', 'rpittman3@gmail.com')
    
    return render_template('test_email.html', 
                         default_from=default_from,
                         dev_email=dev_email,
                         message=message)
