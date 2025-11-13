from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from app import app, db
from models import User, Category, Product, Manufacturer, QuoteRequest, QuoteItem, product_categories, Order, OrderItem
from forms import AdminLoginForm, CategoryForm, ProductForm, ManufacturerForm, UserForm
from flask_login import current_user
from datetime import datetime
import os
import uuid
import math
from werkzeug.utils import secure_filename
from sqlalchemy import text
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

# Admin password (in production, this should be an environment variable)
ADMIN_PASSWORD = "admin123"

def save_uploaded_image(file, folder):
    """Save uploaded image and return the URL path"""
    if file and file.filename:
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        
        # Create the directory if it doesn't exist
        upload_path = os.path.join('static', 'images', folder)
        os.makedirs(upload_path, exist_ok=True)
        
        # Save the file
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
        
        # Return the URL path
        return f"/static/images/{folder}/{unique_filename}"
    return None

def compute_price(cost, override_markup, primary_category_id):
    """
    Compute product price using Decimal arithmetic for precision.
    
    Args:
        cost: Product cost as Decimal or convertible to Decimal
        override_markup: Override markup percentage (can be None, 0, or positive number)
        primary_category_id: ID of primary category to get default markup
        
    Returns:
        Decimal: Computed price with proper quantization (2 decimal places)
    """
    if not cost:
        return Decimal('0.00')
    
    # Convert cost to Decimal for precision
    cost_decimal = Decimal(str(cost))
    
    # Determine markup to use - explicit None check to allow 0% override
    markup_decimal = Decimal('0')
    if override_markup is not None:
        markup_decimal = Decimal(str(override_markup))
    else:
        # Get markup from primary category
        if primary_category_id:
            primary_category = Category.query.get(primary_category_id)
            if primary_category and primary_category.markup:
                markup_decimal = Decimal(str(primary_category.markup))
    
    # Calculate price: cost * (1 + markup/100)
    markup_multiplier = Decimal('1') + (markup_decimal / Decimal('100'))
    price = cost_decimal * markup_multiplier
    
    # Round up to nearest whole dollar, then quantize to 2 decimal places
    rounded_up_price = math.ceil(float(price))
    return Decimal(str(rounded_up_price)).quantize(Decimal('0.01'))

def admin_required(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    form = AdminLoginForm()
    if form.validate_on_submit():
        if form.admin_password.data == ADMIN_PASSWORD:
            session['admin_authenticated'] = True
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin password!', 'error')
    return render_template('admin/login.html', form=form)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_authenticated', None)
    flash('Admin logged out successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/admin')
@admin_required
def admin_dashboard():
    # Get statistics
    total_users = User.query.count()
    total_categories = Category.query.count()
    total_products = Product.query.count()
    
    # Get unprocessed orders (pending status)
    unprocessed_orders = Order.query.filter_by(status='pending').order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_categories=total_categories,
                         total_products=total_products,
                         unprocessed_orders=unprocessed_orders)

# Category Management
@app.route('/admin/categories')
@admin_required
def admin_categories():
    categories = Category.query.order_by(Category.sort_order, Category.name).all()
    return render_template('admin/categories.html', categories=categories)

def get_hierarchical_category_choices(exclude_category_id=None):
    """Get hierarchical category choices for dropdown selection"""
    choices = [(0, 'No Parent')]
    
    # Get all categories ordered by hierarchy
    all_categories = Category.query.order_by(Category.sort_order, Category.name).all()
    
    # Build hierarchy dictionary
    hierarchy = {}
    for cat in all_categories:
        if exclude_category_id and cat.id == exclude_category_id:
            continue
        if cat.parent_id is None:
            hierarchy[cat.id] = {
                'category': cat,
                'children': []
            }
    
    # Add second level
    for cat in all_categories:
        if exclude_category_id and cat.id == exclude_category_id:
            continue
        if cat.parent_id and cat.parent_id in hierarchy:
            hierarchy[cat.parent_id]['children'].append({
                'category': cat,
                'children': []
            })
    
    # Add third level
    for cat in all_categories:
        if exclude_category_id and cat.id == exclude_category_id:
            continue
        if cat.parent_id:
            for main_id, main_data in hierarchy.items():
                for sub_data in main_data['children']:
                    if sub_data['category'].id == cat.parent_id:
                        sub_data['children'].append(cat)
    
    # Build choices with hierarchy
    for main_id, main_data in hierarchy.items():
        main_cat = main_data['category']
        choices.append((main_cat.id, main_cat.name))
        
        for sub_data in main_data['children']:
            sub_cat = sub_data['category'] 
            choices.append((sub_cat.id, f"  → {sub_cat.name}"))
            
            for subsub_cat in sub_data['children']:
                choices.append((subsub_cat.id, f"    → → {subsub_cat.name}"))
    
    return choices

@app.route('/admin/categories/add', methods=['GET', 'POST'])
@admin_required
def admin_add_category():
    form = CategoryForm()
    
    # Populate parent category choices with hierarchy
    form.parent_id.choices = get_hierarchical_category_choices()
    
    if form.validate_on_submit():
        category = Category()
        category.name = form.name.data
        category.slug = form.slug.data
        category.description = form.description.data
        category.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        
        # Handle image upload
        if form.image_file.data:
            image_url = save_uploaded_image(form.image_file.data, 'categories')
            category.image_url = image_url
        else:
            category.image_url = form.image_url.data
            
        category.is_featured = form.is_featured.data
        category.sort_order = form.sort_order.data or 0
        category.markup = form.markup.data
        
        db.session.add(category)
        db.session.commit()
        flash(f'Category "{category.name}" added successfully!', 'success')
        return redirect(url_for('admin_categories'))
    
    return render_template('admin/category_form.html', form=form, title='Add Category')

@app.route('/admin/categories/<int:category_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_category(category_id):
    category = Category.query.get_or_404(category_id)
    form = CategoryForm(obj=category)
    
    # Populate parent category choices with hierarchy (excluding current category)
    form.parent_id.choices = get_hierarchical_category_choices(exclude_category_id=category_id)
    
    if form.validate_on_submit():
        category.name = form.name.data
        category.slug = form.slug.data
        category.description = form.description.data
        category.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        
        # Handle image upload
        if form.image_file.data:
            image_url = save_uploaded_image(form.image_file.data, 'categories')
            category.image_url = image_url
        elif form.image_url.data != category.image_url:
            category.image_url = form.image_url.data
            
        category.is_featured = form.is_featured.data
        category.sort_order = form.sort_order.data or 0
        category.markup = form.markup.data
        
        db.session.commit()
        flash(f'Category "{category.name}" updated successfully!', 'success')
        return redirect(url_for('admin_categories'))
    
    return render_template('admin/category_form.html', form=form, title='Edit Category', category=category)

@app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
@admin_required
def admin_delete_category(category_id):
    category = Category.query.get_or_404(category_id)
    
    # Check if category has products
    if category.products:
        flash(f'Cannot delete category "{category.name}" - it has {len(category.products)} products assigned.', 'error')
        return redirect(url_for('admin_categories'))
    
    db.session.delete(category)
    db.session.commit()
    flash(f'Category "{category.name}" deleted successfully!', 'success')
    return redirect(url_for('admin_categories'))

# Product Management
@app.route('/admin/products')
@admin_required
def admin_products():
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    form = ProductForm()
    
    # Populate category and manufacturer choices
    categories = Category.query.order_by(Category.name).all()
    manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
    form.primary_category_id.choices = [(c.id, c.name) for c in categories]
    form.category_ids.choices = [(c.id, c.name) for c in categories]
    form.manufacturer_id.choices = [(0, 'No Manufacturer')] + [(m.id, m.name) for m in manufacturers]
    
    # Calculate price for display using helper function
    calculated_price = compute_price(
        form.cost.data,
        form.override_markup.data,
        form.primary_category_id.data
    )
    
    # Determine markup source for display
    markup_source = 'override' if form.override_markup.data is not None else 'category'
    
    if form.validate_on_submit():
        product = Product()
        product.name = form.name.data
        product.slug = form.slug.data
        product.sku = form.sku.data
        product.primary_category_id = form.primary_category_id.data
        product.manufacturer_id = form.manufacturer_id.data if form.manufacturer_id.data != 0 else None
        product.short_description = form.short_description.data
        product.description = form.description.data
        
        # Calculate and set price using helper function
        product.price = compute_price(
            form.cost.data,
            form.override_markup.data,
            form.primary_category_id.data
        )
        product.cost = form.cost.data
        product.map_price = form.map_price.data
        product.override_markup = form.override_markup.data
        
        # Handle image upload
        if form.image_file.data:
            image_url = save_uploaded_image(form.image_file.data, 'products')
            product.thumb_image_url = image_url
            product.large_image_url = image_url  # Use same image for both initially
        else:
            product.thumb_image_url = form.image_url.data
            product.large_image_url = form.image_url.data
            
        product.weight = form.weight.data
        product.dimensions = form.dimensions.data
        product.in_stock = form.in_stock.data
        product.stock_quantity = form.stock_quantity.data or 0
        product.is_featured = form.is_featured.data
        product.requires_quote = form.requires_quote.data
        
        db.session.add(product)
        db.session.flush()  # Get the product ID
        
        # Add selected categories
        selected_categories = Category.query.filter(Category.id.in_(form.category_ids.data)).all()
        product.categories.extend(selected_categories)
        
        db.session.commit()
        flash(f'Product "{product.name}" added successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/product_form.html', form=form, title='Add Product', calculated_price=f'{calculated_price:.2f}', markup_source=markup_source)

@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    
    # Populate category and manufacturer choices
    categories = Category.query.order_by(Category.name).all()
    manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
    form.primary_category_id.choices = [(c.id, c.name) for c in categories]
    form.category_ids.choices = [(c.id, c.name) for c in categories]
    form.manufacturer_id.choices = [(0, 'No Manufacturer')] + [(m.id, m.name) for m in manufacturers]
    
    # Pre-populate form with current category assignments, manufacturer, and image URL
    if request.method == 'GET':
        form.category_ids.data = [c.id for c in product.categories]
        form.manufacturer_id.data = product.manufacturer_id or 0
        form.image_url.data = product.thumb_image_url
    
    # Calculate price for display using helper function
    calculated_price = compute_price(
        form.cost.data,
        form.override_markup.data,
        form.primary_category_id.data
    )
    
    # Determine markup source for display
    markup_source = 'override' if form.override_markup.data is not None else 'category'
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.slug = form.slug.data
        product.sku = form.sku.data
        product.primary_category_id = form.primary_category_id.data
        product.manufacturer_id = form.manufacturer_id.data if form.manufacturer_id.data != 0 else None
        product.short_description = form.short_description.data
        product.description = form.description.data
        
        # Calculate and set price using helper function
        product.price = compute_price(
            form.cost.data,
            form.override_markup.data,
            form.primary_category_id.data
        )
        product.cost = form.cost.data
        product.map_price = form.map_price.data
        product.override_markup = form.override_markup.data
        
        # Handle image upload
        if form.image_file.data:
            image_url = save_uploaded_image(form.image_file.data, 'products')
            product.thumb_image_url = image_url
            product.large_image_url = image_url  # Use same image for both initially
        elif form.image_url.data != (product.thumb_image_url or ''):
            product.thumb_image_url = form.image_url.data
            product.large_image_url = form.image_url.data
            
        product.weight = form.weight.data
        product.dimensions = form.dimensions.data
        product.in_stock = form.in_stock.data
        product.stock_quantity = form.stock_quantity.data or 0
        product.is_featured = form.is_featured.data
        product.requires_quote = form.requires_quote.data
        product.updated_at = datetime.now()
        
        # Update categories
        product.categories.clear()
        selected_categories = Category.query.filter(Category.id.in_(form.category_ids.data)).all()
        product.categories.extend(selected_categories)
        
        db.session.commit()
        flash(f'Product "{product.name}" updated successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/product_form.html', form=form, title='Edit Product', product=product, calculated_price=f'{calculated_price:.2f}', markup_source=markup_source)

@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{product.name}" deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

# Manufacturer Management
@app.route('/admin/manufacturers')
@admin_required
def admin_manufacturers():
    manufacturers = Manufacturer.query.order_by(Manufacturer.name).all()
    return render_template('admin/manufacturers.html', manufacturers=manufacturers)

@app.route('/admin/manufacturers/add', methods=['GET', 'POST'])
@admin_required
def admin_add_manufacturer():
    form = ManufacturerForm()
    
    if form.validate_on_submit():
        manufacturer = Manufacturer()
        manufacturer.name = form.name.data
        manufacturer.slug = form.slug.data
        
        db.session.add(manufacturer)
        db.session.commit()
        flash(f'Manufacturer "{manufacturer.name}" added successfully!', 'success')
        return redirect(url_for('admin_manufacturers'))
    
    return render_template('admin/manufacturer_form.html', form=form, title='Add Manufacturer')

@app.route('/admin/manufacturers/<int:manufacturer_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_manufacturer(manufacturer_id):
    manufacturer = Manufacturer.query.get_or_404(manufacturer_id)
    form = ManufacturerForm(obj=manufacturer)
    
    if form.validate_on_submit():
        manufacturer.name = form.name.data
        manufacturer.slug = form.slug.data
        manufacturer.updated_at = datetime.now()
        
        db.session.commit()
        flash(f'Manufacturer "{manufacturer.name}" updated successfully!', 'success')
        return redirect(url_for('admin_manufacturers'))
    
    return render_template('admin/manufacturer_form.html', form=form, title='Edit Manufacturer', manufacturer=manufacturer)

@app.route('/admin/manufacturers/<int:manufacturer_id>/delete', methods=['POST'])
@admin_required
def admin_delete_manufacturer(manufacturer_id):
    manufacturer = Manufacturer.query.get_or_404(manufacturer_id)
    
    # Check if manufacturer has products
    if manufacturer.products:
        flash(f'Cannot delete manufacturer "{manufacturer.name}" - it has {len(manufacturer.products)} products assigned.', 'error')
        return redirect(url_for('admin_manufacturers'))
    
    db.session.delete(manufacturer)
    db.session.commit()
    flash(f'Manufacturer "{manufacturer.name}" deleted successfully!', 'success')
    return redirect(url_for('admin_manufacturers'))


# Category Sorting
@app.route('/admin/categories/sort')
@admin_required
def admin_sort_categories():
    # Get all parent categories
    parent_categories = Category.query.filter_by(parent_id=None).order_by(Category.sort_order, Category.name).all()
    return render_template('admin/category_sort.html', parent_categories=parent_categories)

@app.route('/admin/categories/sort/update', methods=['POST'])
@admin_required
def admin_update_category_sort():
    data = request.get_json()
    
    for item in data:
        category = Category.query.get(item['id'])
        if category:
            category.sort_order = item['sort_order']
    
    db.session.commit()
    return jsonify({'success': True})

# User Management
@app.route('/admin/users')
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin/users.html', users=users)

@app.route('/admin/users/<user_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_user(user_id):
    user = User.query.get_or_404(user_id)
    form = UserForm(obj=user)
    
    if form.validate_on_submit():
        user.first_name = form.first_name.data
        user.last_name = form.last_name.data
        user.email = form.email.data
        user.company_name = form.company_name.data
        user.phone = form.phone.data
        user.is_admin = form.is_admin.data
        user.updated_at = datetime.now()
        
        db.session.commit()
        flash(f'User {user.email or user.id} updated successfully!', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/user_form.html', form=form, title='Edit User', user=user)

# Bulk Category Assignment
def get_hierarchical_categories_for_assignment():
    """Get hierarchical category structure for bulk assignment"""
    all_categories = Category.query.order_by(Category.sort_order, Category.name).all()
    
    # Build hierarchy structure
    hierarchy = []
    
    # First, get all main categories (no parent)
    main_categories = [cat for cat in all_categories if cat.parent_id is None]
    
    for main_cat in main_categories:
        main_data = {
            'category': main_cat,
            'subcategories': []
        }
        
        # Get subcategories for this main category
        subcategories = [cat for cat in all_categories if cat.parent_id == main_cat.id]
        
        for sub_cat in subcategories:
            sub_data = {
                'category': sub_cat,
                'sub_subcategories': []
            }
            
            # Get sub-subcategories for this subcategory
            sub_subcategories = [cat for cat in all_categories if cat.parent_id == sub_cat.id]
            sub_data['sub_subcategories'] = sub_subcategories
            
            main_data['subcategories'].append(sub_data)
        
        hierarchy.append(main_data)
    
    return hierarchy

@app.route('/admin/bulk-category-assignment')
@admin_required
def admin_bulk_category_assignment():
    """Display bulk category assignment page"""
    categories = get_hierarchical_categories_for_assignment()
    
    # Get search query and category filter from request
    search_query = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    uncategorized_only = request.args.get('uncategorized', type=int)
    
    # Start with all products query
    products_query = Product.query
    
    # Apply uncategorized filter if requested
    if uncategorized_only:
        # Find products that have no categories using a subquery
        uncategorized_subquery = text(
            "SELECT product_id FROM product_categories"
        )
        products_query = products_query.filter(
            ~Product.id.in_(db.session.execute(uncategorized_subquery).scalars())
        )
    
    # Apply search filter if provided
    if search_query:
        products_query = products_query.filter(
            Product.name.ilike(f'%{search_query}%') |
            Product.sku.ilike(f'%{search_query}%')
        )
    
    # Get paginated products
    page = request.args.get('page', 1, type=int)
    products = products_query.order_by(Product.name).paginate(
        page=page, per_page=50, error_out=False
    )
    
    return render_template('admin/bulk_category_assignment.html',
                         categories=categories,
                         products=products,
                         search_query=search_query,
                         selected_category_id=category_id,
                         uncategorized_only=uncategorized_only)

@app.route('/admin/bulk-category-assignment', methods=['POST'])
@admin_required
def admin_process_bulk_category_assignment():
    """Process bulk category assignment form submission"""
    category_id = request.form.get('category_id', type=int)
    product_ids = request.form.getlist('product_ids', type=int)
    
    if not category_id:
        flash('Please select a category.', 'error')
        return redirect(url_for('admin_bulk_category_assignment'))
    
    if not product_ids:
        flash('Please select at least one product.', 'error')
        return redirect(url_for('admin_bulk_category_assignment'))
    
    category = Category.query.get_or_404(category_id)
    
    # Add products to the selected category
    success_count = 0
    for product_id in product_ids:
        product = Product.query.get(product_id)
        if product:
            # Check if product is already in this category
            existing = db.session.execute(
                text("SELECT 1 FROM product_categories WHERE product_id = :pid AND category_id = :cid"),
                {'pid': product_id, 'cid': category_id}
            ).first()
            
            if not existing:
                # Add product to category
                db.session.execute(
                    text("INSERT INTO product_categories (product_id, category_id) VALUES (:pid, :cid)"),
                    {'pid': product_id, 'cid': category_id}
                )
                success_count += 1
            
            # Update primary category if not set
            if not product.primary_category_id:
                product.primary_category_id = category_id
    
    db.session.commit()
    
    flash(f'Successfully assigned {success_count} products to "{category.name}" category.', 'success')
    return redirect(url_for('admin_bulk_category_assignment'))

@app.route('/admin/markups')
@admin_required
def admin_markups():
    """Display category markup management page"""
    from flask_wtf.csrf import generate_csrf
    from sqlalchemy.orm import aliased
    
    # Create alias for parent category to avoid self-join conflict
    parent_category = aliased(Category)
    
    # Get only second-level categories (have a parent, but parent has no parent)
    categories = Category.query.join(
        parent_category, Category.parent_id == parent_category.id
    ).filter(
        Category.parent_id.isnot(None),  # Category has a parent
        parent_category.parent_id.is_(None)  # Parent has no parent (is first-level)
    ).order_by(Category.name).all()
    return render_template('admin/markups.html', categories=categories, csrf_token=generate_csrf())

@app.route('/admin/product-costs')
@admin_required
def admin_product_costs():
    """Display product cost management page"""
    from flask_wtf.csrf import generate_csrf
    
    # Get all products including those without categories for filtering
    products = Product.query.outerjoin(Category, Product.primary_category_id == Category.id).order_by(Product.name).all()
    
    # Get all categories for filtering
    categories = Category.query.order_by(Category.name).all()
    
    return render_template('admin/product_costs.html', products=products, categories=categories, csrf_token=generate_csrf())

@app.route('/admin/products/<int:product_id>/cost', methods=['PATCH', 'POST'])
@admin_required
def admin_update_product_cost(product_id):
    """Update product cost via AJAX"""
    from flask_wtf.csrf import validate_csrf
    
    try:
        # Validate CSRF token
        validate_csrf(request.headers.get('X-CSRFToken'))
        
        product = Product.query.get_or_404(product_id)
        
        # Get new cost from request (allow empty to clear cost)
        new_cost = request.form.get('cost', '').strip()
        
        if new_cost == '':
            # Clear the cost
            cost_decimal = None
        else:
            try:
                cost_decimal = Decimal(str(new_cost))
                if cost_decimal < 0:
                    return jsonify({'success': False, 'error': 'Cost cannot be negative'}), 400
            except (ValueError, InvalidOperation):
                return jsonify({'success': False, 'error': 'Invalid cost format'}), 400
        
        # Update product cost
        product.cost = cost_decimal
        
        # Recalculate price using existing compute_price function
        if cost_decimal is not None:
            new_price = compute_price(
                cost_decimal,
                product.override_markup,
                product.primary_category_id
            )
            product.price = new_price
        else:
            # If cost is cleared, set price to None for consistency
            product.price = None
            new_price = None
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'cost': float(cost_decimal) if cost_decimal is not None else None,
            'price': float(new_price) if new_price is not None else None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/products/<int:product_id>/map-price', methods=['PATCH', 'POST'])
@admin_required
def admin_update_product_map_price(product_id):
    """Update product MAP price via AJAX"""
    from flask_wtf.csrf import validate_csrf
    
    try:
        # Validate CSRF token
        validate_csrf(request.headers.get('X-CSRFToken'))
        
        product = Product.query.get_or_404(product_id)
        
        # Get new MAP price from request (allow empty to clear MAP price)
        new_map_price = request.form.get('map_price', '').strip()
        
        if new_map_price == '':
            # Clear the MAP price
            map_price_decimal = None
        else:
            try:
                map_price_decimal = Decimal(str(new_map_price))
                if map_price_decimal < 0:
                    return jsonify({'success': False, 'error': 'MAP price cannot be negative'}), 400
            except (ValueError, InvalidOperation):
                return jsonify({'success': False, 'error': 'Invalid MAP price format'}), 400
        
        # Update product MAP price
        product.map_price = map_price_decimal
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'map_price': float(map_price_decimal) if map_price_decimal is not None else None
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/products/<int:product_id>/price-not-available', methods=['PATCH', 'POST'])
@admin_required
def admin_update_product_price_not_available(product_id):
    """Update product price not available checkbox via AJAX"""
    from flask_wtf.csrf import validate_csrf
    
    try:
        # Validate CSRF token
        validate_csrf(request.headers.get('X-CSRFToken'))
        
        product = Product.query.get_or_404(product_id)
        
        # Get checkbox value from request
        price_not_available = request.form.get('price_not_available', 'false').strip().lower()
        
        # Convert to boolean
        product.price_not_available = price_not_available == 'true'
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'price_not_available': product.price_not_available
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/admin/categories/<int:category_id>/markup', methods=['PATCH', 'POST'])
@admin_required
def admin_update_category_markup(category_id):
    """Update category markup via AJAX"""
    from flask_wtf.csrf import validate_csrf
    try:
        # Validate CSRF token
        validate_csrf(request.headers.get('X-CSRFToken'))
        
        category = Category.query.get_or_404(category_id)
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        markup_value = data.get('markup')
        
        # Handle empty string or null as None (clear markup)
        if markup_value == '' or markup_value is None:
            markup_decimal = None
        else:
            try:
                # Convert to Decimal and validate range
                markup_decimal = Decimal(str(markup_value))
                markup_decimal = markup_decimal.quantize(Decimal('0.0001'))  # 4 decimal places
                
                if markup_decimal < 0 or markup_decimal > 300:
                    return jsonify({'error': 'Markup must be between 0% and 300%'}), 400
                    
            except (ValueError, TypeError, InvalidOperation):
                return jsonify({'error': 'Invalid markup value'}), 400
        
        # Update category markup
        old_markup = category.markup
        category.markup = markup_decimal
        
        # Recompute prices for products that use this category's markup (no override)
        products_to_update = Product.query.filter(
            Product.primary_category_id == category_id,
            Product.override_markup.is_(None)
        ).all()
        
        updated_count = 0
        for product in products_to_update:
            if product.cost:  # Only update if product has a cost
                new_price = compute_price(product.cost, None, category_id)
                product.price = new_price
                updated_count += 1
        
        db.session.commit()
        
        # Log the change
        app.logger.info(f'Updated category "{category.name}" markup from {old_markup}% to {markup_decimal}%. Updated {updated_count} product prices.')
        
        return jsonify({
            'success': True,
            'markup': float(markup_decimal) if markup_decimal is not None else None,
            'updated_count': updated_count
        })
        
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Error updating category markup: {str(e)}')
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/products/without-images')
@admin_required
def admin_products_without_images():
    """Display products that do not have either image URL or uploaded image"""
    from sqlalchemy import or_
    
    # Query products where both thumb_image_url and large_image_url are NULL or empty
    products = Product.query.filter(
        or_(
            Product.thumb_image_url.is_(None),
            Product.thumb_image_url == ''
        ),
        or_(
            Product.large_image_url.is_(None),
            Product.large_image_url == ''
        )
    ).order_by(Product.name).all()
    
    return render_template('admin/products_without_images.html', products=products)

@app.route('/admin/products/featured')
@admin_required
def admin_featured_products():
    """Display all featured products"""
    products = Product.query.filter_by(is_featured=True).order_by(Product.name).all()
    return render_template('admin/featured_products.html', products=products)

@app.route('/admin/products/<int:product_id>/toggle-featured', methods=['POST'])
@admin_required
def admin_toggle_featured(product_id):
    """Toggle featured status of a product"""
    product = Product.query.get_or_404(product_id)
    product.is_featured = not product.is_featured
    db.session.commit()
    
    status = "featured" if product.is_featured else "unfeatured"
    flash(f'Product "{product.name}" is now {status}!', 'success')
    
    # Return to the referring page or featured products page
    return redirect(request.referrer or url_for('admin_featured_products'))

# Orders Management
@app.route('/admin/orders')
@admin_required
def admin_orders():
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)

@app.route('/admin/orders/<int:order_id>')
@admin_required
def admin_order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    return render_template('admin/order_detail.html', order=order)

@app.route('/admin/orders/<int:order_id>/update_status', methods=['POST'])
@admin_required
def admin_update_order_status(order_id):
    from models import OrderStatusHistory
    
    order = Order.query.get_or_404(order_id)
    new_status = request.form.get('status')
    
    if new_status in ['pending', 'sent', 'shipped', 'delivered', 'cancelled']:
        old_status = order.status
        
        if old_status != new_status:
            order.status = new_status
            
            # Create status history entry
            status_change = OrderStatusHistory(
                order_id=order.id,
                status=new_status,
                changed_by='admin',
                notes=f'Status changed from {old_status} to {new_status}'
            )
            db.session.add(status_change)
            
        db.session.commit()
        flash(f'Order {order.order_number} status updated to {new_status}!', 'success')
    else:
        flash('Invalid status!', 'error')
    
    return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/orders/<int:order_id>/update_costs', methods=['POST'])
@admin_required
def admin_update_order_costs(order_id):
    order = Order.query.get_or_404(order_id)
    
    try:
        tax_amount = float(request.form.get('tax_amount', 0))
        shipping_amount = float(request.form.get('shipping_amount', 0))
        tax_after_shipping = request.form.get('tax_after_shipping', 'false') == 'true'
        
        order.tax_amount = tax_amount
        order.shipping_amount = shipping_amount
        order.tax_after_shipping = tax_after_shipping
        
        # Calculate total based on tax calculation method
        # Note: The tax_amount entered by admin is already the calculated amount,
        # this flag is just for display purposes to show the order of calculation
        order.total_amount = float(order.subtotal) + tax_amount + shipping_amount
        
        db.session.commit()
        flash('Tax and shipping costs updated successfully!', 'success')
    except (ValueError, TypeError):
        flash('Invalid tax or shipping amount!', 'error')
    
    return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/orders/<int:order_id>/update_payment_link', methods=['POST'])
@admin_required
def admin_update_payment_link(order_id):
    order = Order.query.get_or_404(order_id)
    
    payment_link = request.form.get('payment_link', '').strip()
    order.payment_link = payment_link if payment_link else None
    
    db.session.commit()
    flash('Payment link updated successfully!', 'success')
    
    return redirect(url_for('admin_order_detail', order_id=order_id))

@app.route('/admin/orders/<int:order_id>/send_email', methods=['POST'])
@admin_required
def admin_send_customer_email(order_id):
    from email_utils import send_customer_order_email
    from datetime import datetime
    from models import OrderStatusHistory
    
    order = Order.query.get_or_404(order_id)
    user = User.query.get(order.user_id)
    
    # Generate the customer order view URL
    order_url = url_for('customer_order_view', secure_token=order.secure_token, _external=True)
    base_url = request.url_root
    
    # Send the email
    success = send_customer_order_email(order, user, order_url, base_url)
    
    if success:
        old_status = order.status
        
        # Record when email was sent
        order.sent_at = datetime.now()
        
        # Automatically change status to "sent" when email is sent
        if old_status != 'sent':
            order.status = 'sent'
            
            # Create status history entry
            status_change = OrderStatusHistory(
                order_id=order.id,
                status='sent',
                changed_by='admin',
                notes='Order email sent to customer'
            )
            db.session.add(status_change)
        
        db.session.commit()
        flash('Email sent successfully to customer! Order status updated to "Sent".', 'success')
    else:
        flash('Failed to send email. Please check your email configuration.', 'error')
    
    return redirect(url_for('admin_order_detail', order_id=order_id))