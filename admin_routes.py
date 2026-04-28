from flask import render_template, request, redirect, url_for, flash, session, jsonify, send_file
from functools import wraps
from app import app, db
from models import User, Category, Product, Manufacturer, QuoteRequest, QuoteItem, product_categories, Order, OrderItem
from forms import AdminLoginForm, CategoryForm, ProductForm, ManufacturerForm, UserForm
from flask_login import current_user
from datetime import datetime
import os
import uuid
import math
import csv
import io
import re
import json
import tempfile
import urllib.parse
from werkzeug.utils import secure_filename
from sqlalchemy import text
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import logging
import boto3
from botocore.exceptions import ClientError
import trafilatura
from openai import OpenAI
from flask_wtf.csrf import validate_csrf
from wtforms import ValidationError

logger = logging.getLogger(__name__)

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

DO_SPACES_KEY = os.environ.get("DO_SPACES_KEY")
DO_SPACES_SECRET = os.environ.get("DO_SPACES_SECRET")
DO_SPACES_BUCKET = os.environ.get("DO_SPACES_BUCKET")
DO_SPACES_REGION = os.environ.get("DO_SPACES_REGION")

def _get_spaces_client():
    if all([DO_SPACES_KEY, DO_SPACES_SECRET, DO_SPACES_BUCKET, DO_SPACES_REGION]):
        return boto3.client(
            "s3",
            region_name=DO_SPACES_REGION,
            endpoint_url=f"https://{DO_SPACES_REGION}.digitaloceanspaces.com",
            aws_access_key_id=DO_SPACES_KEY,
            aws_secret_access_key=DO_SPACES_SECRET,
        )
    return None

def save_uploaded_image(file, folder):
    """Save uploaded image to DigitalOcean Spaces (or local fallback) and return the URL"""
    if file and file.filename:
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex[:8]}{ext}"
        object_key = f"images/{folder}/{unique_filename}"

        spaces_client = _get_spaces_client()
        if spaces_client:
            try:
                content_type = file.content_type or "application/octet-stream"
                spaces_client.upload_fileobj(
                    file,
                    DO_SPACES_BUCKET,
                    object_key,
                    ExtraArgs={"ACL": "public-read", "ContentType": content_type},
                )
                url = f"https://{DO_SPACES_BUCKET}.{DO_SPACES_REGION}.digitaloceanspaces.com/{object_key}"
                logger.info("Uploaded image to DigitalOcean Spaces: %s", url)
                return url
            except Exception:
                logger.exception("Failed to upload to DigitalOcean Spaces, falling back to local storage")
                file.stream.seek(0)
        else:
            logger.warning("DigitalOcean Spaces credentials not configured — saving image to local filesystem")
        upload_path = os.path.join("static", "images", folder)
        os.makedirs(upload_path, exist_ok=True)
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
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
    total_orders = Order.query.count()
    
    # Get unprocessed orders (pending status)
    unprocessed_orders = Order.query.filter_by(status='pending').order_by(Order.created_at.desc()).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_categories=total_categories,
                         total_products=total_products,
                         total_orders=total_orders,
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
        product.is_featured = form.is_featured.data
        product.requires_quote = form.requires_quote.data
        
        db.session.add(product)
        db.session.flush()  # Get the product ID
        
        # Add selected categories, ensuring primary category is always included
        selected_category_ids = set(form.category_ids.data or [])
        selected_category_ids.add(form.primary_category_id.data)
        selected_categories = Category.query.filter(Category.id.in_(selected_category_ids)).all()
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
        product.is_featured = form.is_featured.data
        product.requires_quote = form.requires_quote.data
        product.updated_at = datetime.now()
        
        # Update categories, ensuring primary category is always included
        product.categories.clear()
        selected_category_ids = set(form.category_ids.data or [])
        selected_category_ids.add(form.primary_category_id.data)
        selected_categories = Category.query.filter(Category.id.in_(selected_category_ids)).all()
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
    
    # Hide products with no price (NULL or 0)
    products_query = products_query.filter(
        Product.price.isnot(None),
        Product.price > 0
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

@app.route('/admin/image-url-search')
@admin_required
def admin_image_url_search():
    """Search products by image URL keyword"""
    from sqlalchemy import or_
    q = request.args.get('q', '').strip()
    products = []
    if q:
        search_term = f'%{q}%'
        products = Product.query.filter(
            or_(
                Product.thumb_image_url.ilike(search_term),
                Product.large_image_url.ilike(search_term)
            )
        ).order_by(Product.name).all()
    return render_template('admin/image_url_search.html', products=products, q=q)

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


def generate_slug(name):
    slug = name.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug)
    slug = slug.strip('-')
    return slug


def ensure_unique_slug(base_slug):
    slug = base_slug
    counter = 1
    while Product.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


@app.route('/admin/csv-template')
@admin_required
def admin_download_csv_template():
    template_path = os.path.join(app.root_path, 'static', 'csv', 'product_import_template.csv')
    return send_file(template_path, as_attachment=True, download_name='product_import_template.csv', mimetype='text/csv')


@app.route('/admin/csv-import', methods=['GET', 'POST'])
@admin_required
def admin_csv_import():
    categories = Category.query.order_by(Category.name).all()

    if request.method == 'GET':
        return render_template('admin/csv_import.html', categories=categories, preview_data=None)

    csv_file = request.files.get('csv_file')
    default_category_id = request.form.get('default_category', type=int)

    if not csv_file or not csv_file.filename:
        flash('Please select a CSV file to upload.', 'error')
        return render_template('admin/csv_import.html', categories=categories, preview_data=None)

    if not csv_file.filename.lower().endswith('.csv'):
        flash('File must be a CSV file (.csv extension).', 'error')
        return render_template('admin/csv_import.html', categories=categories, preview_data=None)

    try:
        content = csv_file.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            csv_file.seek(0)
            content = csv_file.read().decode('latin-1')
        except Exception:
            flash('Could not read the CSV file. Please ensure it is saved as UTF-8.', 'error')
            return render_template('admin/csv_import.html', categories=categories, preview_data=None)

    reader = csv.DictReader(io.StringIO(content))

    if not reader.fieldnames:
        flash('CSV file appears to be empty or has no header row.', 'error')
        return render_template('admin/csv_import.html', categories=categories, preview_data=None)

    headers_lower = [h.strip().lower().replace(' ', '_') for h in reader.fieldnames]

    if 'sku' not in headers_lower or 'name' not in headers_lower:
        flash('CSV file must contain at least "sku" and "name" columns.', 'error')
        return render_template('admin/csv_import.html', categories=categories, preview_data=None)

    all_categories = Category.query.all()
    category_lookup = {}
    for cat in all_categories:
        category_lookup[cat.name.lower().strip()] = cat

    existing_skus = {p.sku.lower(): p for p in Product.query.all()}

    preview_data = []
    raw_rows = []
    stats = {'new': 0, 'existing': 0, 'errors': 0}

    for row_num, row in enumerate(reader, start=2):
        cleaned = {}
        for key, val in row.items():
            if key:
                cleaned[key.strip().lower().replace(' ', '_')] = (val or '').strip()

        sku = cleaned.get('sku', '')
        name = cleaned.get('name', '')
        brand = cleaned.get('brand', '')
        category_name = cleaned.get('category', '')
        cost = cleaned.get('cost', '')
        map_price = cleaned.get('map_price', '')
        short_description = cleaned.get('short_description', '')
        description = cleaned.get('description', '')
        weight = cleaned.get('weight', '')
        dimensions = cleaned.get('dimensions', '')
        thumb_image_url = cleaned.get('thumb_image_url', '')
        large_image_url = cleaned.get('large_image_url', '')
        requires_quote = cleaned.get('requires_quote', '').lower() in ('yes', 'true', '1', 'y')

        notes = []
        status = 'new'

        if not sku:
            status = 'error'
            notes.append('Missing SKU')
        if not name:
            status = 'error'
            notes.append('Missing name')

        if sku and sku.lower() in existing_skus:
            status = 'existing'
            notes.append('SKU already exists')

        if cost:
            try:
                float(cost.replace('$', '').replace(',', ''))
            except ValueError:
                notes.append('Invalid cost format')
                cost = ''

        if map_price:
            try:
                float(map_price.replace('$', '').replace(',', ''))
            except ValueError:
                notes.append('Invalid MAP price format')
                map_price = ''

        category_match = False
        matched_cat_name = category_name
        if category_name and category_name.lower().strip() in category_lookup:
            category_match = True
            matched_cat_name = category_lookup[category_name.lower().strip()].name
        elif category_name:
            notes.append('Category not found, will use default')

        if status == 'new':
            stats['new'] += 1
        elif status == 'existing':
            stats['existing'] += 1
        else:
            stats['errors'] += 1

        preview_data.append({
            'row_num': row_num,
            'status': status,
            'sku': sku,
            'name': name,
            'brand': brand,
            'category_name': matched_cat_name,
            'category_match': category_match,
            'cost': cost,
            'map_price': map_price,
            'notes': '; '.join(notes) if notes else ''
        })

        raw_rows.append(cleaned)

    import_id = uuid.uuid4().hex[:16]
    temp_path = os.path.join(tempfile.gettempdir(), f'csv_import_{import_id}.json')
    with open(temp_path, 'w') as f:
        json.dump(raw_rows, f)

    return render_template('admin/csv_import.html',
                         categories=categories,
                         preview_data=preview_data,
                         stats=stats,
                         import_id=import_id,
                         default_category_id=default_category_id or '')


@app.route('/admin/csv-process', methods=['POST'])
@admin_required
def admin_csv_process():
    import_id = request.form.get('import_id', '')
    default_category_id = request.form.get('default_category', type=int)
    selected_rows = request.form.getlist('import_rows', type=int)

    if not import_id or not selected_rows:
        flash('No products selected for import.', 'error')
        return redirect(url_for('admin_csv_import'))

    temp_path = os.path.join(tempfile.gettempdir(), f'csv_import_{import_id}.json')
    if not os.path.exists(temp_path):
        flash('Import session expired. Please upload the CSV file again.', 'error')
        return redirect(url_for('admin_csv_import'))

    with open(temp_path, 'r') as f:
        raw_rows = json.load(f)

    all_categories = Category.query.all()
    category_lookup = {}
    for cat in all_categories:
        category_lookup[cat.name.lower().strip()] = cat

    existing_skus = {p.sku.lower() for p in Product.query.all()}

    imported_count = 0
    skipped_count = 0
    error_count = 0

    for row_num in selected_rows:
        idx = row_num - 2
        if idx < 0 or idx >= len(raw_rows):
            continue

        row = raw_rows[idx]
        sku = row.get('sku', '').strip()
        name = row.get('name', '').strip()

        if not sku or not name:
            error_count += 1
            continue

        if sku.lower() in existing_skus:
            skipped_count += 1
            continue

        category_name = row.get('category', '').strip()
        category_id = default_category_id

        if category_name and category_name.lower() in category_lookup:
            category_id = category_lookup[category_name.lower()].id

        if not category_id:
            first_cat = Category.query.first()
            if first_cat:
                category_id = first_cat.id
            else:
                error_count += 1
                continue

        brand = row.get('brand', '').strip()

        manufacturer_id = None
        if brand:
            manufacturer = Manufacturer.query.filter(
                db.func.lower(Manufacturer.name) == brand.lower()
            ).first()
            if not manufacturer:
                mfr_slug = generate_slug(brand)
                existing_mfr = Manufacturer.query.filter_by(slug=mfr_slug).first()
                if existing_mfr:
                    manufacturer_id = existing_mfr.id
                else:
                    manufacturer = Manufacturer(name=brand, slug=mfr_slug)
                    db.session.add(manufacturer)
                    db.session.flush()
                    manufacturer_id = manufacturer.id
            else:
                manufacturer_id = manufacturer.id

        cost_str = row.get('cost', '').strip()
        cost = None
        if cost_str:
            try:
                cost = Decimal(cost_str.replace('$', '').replace(',', ''))
            except (InvalidOperation, ValueError):
                cost = None

        map_price_str = row.get('map_price', '').strip()
        map_price = None
        if map_price_str:
            try:
                map_price = Decimal(map_price_str.replace('$', '').replace(',', ''))
            except (InvalidOperation, ValueError):
                map_price = None

        price = None
        if cost and cost > 0:
            price = compute_price(cost, None, category_id)

        weight_str = row.get('weight', '').strip()
        weight = None
        if weight_str:
            try:
                weight = Decimal(weight_str.replace(',', ''))
            except (InvalidOperation, ValueError):
                weight = None

        requires_quote = row.get('requires_quote', '').strip().lower() in ('yes', 'true', '1', 'y')

        slug = ensure_unique_slug(generate_slug(name))

        product = Product(
            name=name,
            slug=slug,
            sku=sku,
            primary_category_id=category_id,
            manufacturer_id=manufacturer_id,
            short_description=row.get('short_description', '').strip() or None,
            description=row.get('description', '').strip() or None,
            cost=cost,
            map_price=map_price,
            price=price,
            weight=weight,
            dimensions=row.get('dimensions', '').strip() or None,
            thumb_image_url=row.get('thumb_image_url', '').strip() or None,
            large_image_url=row.get('large_image_url', '').strip() or None,
            is_featured=False,
            requires_quote=requires_quote,
            price_not_available=(price is None and not cost)
        )

        db.session.add(product)
        db.session.flush()

        category_obj = Category.query.get(category_id)
        if category_obj:
            product.categories.append(category_obj)

        existing_skus.add(sku.lower())
        imported_count += 1

    db.session.commit()

    try:
        os.remove(temp_path)
    except OSError:
        pass

    if imported_count > 0:
        flash(f'Successfully imported {imported_count} products.', 'success')
    if skipped_count > 0:
        flash(f'Skipped {skipped_count} products (SKU already exists).', 'warning')
    if error_count > 0:
        flash(f'{error_count} products had errors and were not imported.', 'error')

    return redirect(url_for('admin_products'))


def _scrape_url(url):
    """Scrape text content from a URL using trafilatura. Returns text or empty string."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded)
            return text or ''
    except Exception as e:
        logger.warning("Failed to scrape %s: %s", url, e)
    return ''


def _extract_product_links(html_bytes, base_domain):
    """Extract product page links from a raw HTML search results page."""
    try:
        text = html_bytes.decode('utf-8', errors='replace') if isinstance(html_bytes, bytes) else html_bytes
        pattern = r'href=["\']([^"\']+/products/[^"\']+)["\']'
        raw_links = re.findall(pattern, text)
        seen = set()
        links = []
        for href in raw_links:
            if href.startswith('/'):
                href = base_domain.rstrip('/') + href
            elif not href.startswith('http'):
                continue
            if href not in seen:
                seen.add(href)
                links.append(href)
        return links[:3]
    except Exception:
        return []


def _extract_links_from_html(html_bytes, base_url, keywords):
    """Extract hrefs from HTML that contain any of the given keywords (case-insensitive)."""
    try:
        text = html_bytes.decode('utf-8', errors='replace') if isinstance(html_bytes, bytes) else html_bytes
        pattern = r'href=["\']([^"\'#?][^"\']*)["\']'
        raw_links = re.findall(pattern, text)
        seen = set()
        matches = []
        kw_lower = [k.lower() for k in keywords if k]
        base = base_url.rstrip('/')
        for href in raw_links:
            if href.startswith('/'):
                href = base + href
            elif not href.startswith('http'):
                continue
            lower_href = href.lower()
            if href not in seen and any(kw in lower_href for kw in kw_lower):
                seen.add(href)
                matches.append(href)
        return matches[:3]
    except Exception:
        return []


def _find_manufacturer_product_url(mfr_base_url, sku, product_name):
    """
    Try to locate a product-specific or search-results page on a manufacturer's site.
    Returns (url, scraped_text) for the best match, or (None, '') if nothing useful found.
    """
    search_term = ' '.join(filter(None, [sku, product_name]))
    encoded = urllib.parse.quote_plus(search_term)
    encoded_sku = urllib.parse.quote_plus(sku) if sku else None
    base = mfr_base_url.rstrip('/')

    candidate_search_paths = [
        f"/search?q={encoded}",
        f"/search?query={encoded}",
        f"/search?keywords={encoded}",
        f"/catalogsearch/result/?q={encoded}",
        f"/products/search?q={encoded}",
        f"/en/search?q={encoded}",
        f"/us/search?q={encoded}",
    ]
    if encoded_sku:
        candidate_search_paths += [
            f"/search?q={encoded_sku}",
            f"/search?query={encoded_sku}",
        ]

    for path in candidate_search_paths:
        candidate_url = base + path
        try:
            raw = trafilatura.fetch_url(candidate_url)
            if not raw:
                continue
            page_text = trafilatura.extract(raw) or ''
            if len(page_text) < 100:
                continue
            sku_lower = sku.lower() if sku else ''
            name_words = [w for w in product_name.lower().split() if len(w) > 3]
            relevance = sum(1 for w in name_words if w in page_text.lower())
            if sku_lower and sku_lower in page_text.lower():
                relevance += 5
            if relevance >= 2:
                product_links = _extract_links_from_html(raw, base, [sku] + name_words[:3])
                for detail_link in product_links[:2]:
                    detail_text = _scrape_url(detail_link)
                    if detail_text and len(detail_text) > 200:
                        logger.info("Found manufacturer product detail page: %s", detail_link)
                        return detail_link, detail_text
                logger.info("Using manufacturer search results page: %s", candidate_url)
                return candidate_url, page_text
        except Exception as e:
            logger.debug("Candidate URL %s failed: %s", candidate_url, e)
            continue

    return None, ''


def _get_openai_client():
    """Create an OpenAI client using Replit AI Integrations."""
    return OpenAI(
        api_key=os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY"),
        base_url=os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL"),
    )


@app.route('/admin/products/generate-description', methods=['POST'])
@admin_required
def admin_generate_description():
    """Generate a product description using web scraping + OpenAI."""
    try:
        validate_csrf(request.headers.get('X-CSRFToken'))
    except ValidationError:
        return jsonify({'error': 'Invalid or missing CSRF token.'}), 400

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    product_name = (data.get('product_name') or '').strip()
    sku = (data.get('sku') or '').strip()
    manufacturer_name = (data.get('manufacturer_name') or '').strip()
    primary_category = (data.get('primary_category') or '').strip()

    if not product_name:
        return jsonify({'error': 'Product name is required'}), 400

    scraped_sections = []

    # Search restaurantsupply.com and scrape both search results and product detail pages
    search_terms = ' '.join(filter(None, [product_name, sku, manufacturer_name, primary_category]))
    encoded_terms = urllib.parse.quote_plus(search_terms)
    rs_base = 'https://www.restaurantsupply.com'
    rs_search_url = f"{rs_base}/search?q={encoded_terms}"
    logger.info("Scraping restaurantsupply.com search: %s", rs_search_url)

    try:
        rs_html = trafilatura.fetch_url(rs_search_url)
        if rs_html:
            rs_search_text = trafilatura.extract(rs_html) or ''
            if rs_search_text:
                scraped_sections.append(f"[restaurantsupply.com search results]\n{rs_search_text[:2000]}")
            product_links = _extract_product_links(rs_html, rs_base)
            for link in product_links[:2]:
                logger.info("Scraping restaurantsupply.com product page: %s", link)
                page_text = _scrape_url(link)
                if page_text:
                    scraped_sections.append(f"[restaurantsupply.com product page: {link}]\n{page_text[:2500]}")
    except Exception as e:
        logger.warning("Error scraping restaurantsupply.com: %s", e)

    # Scrape the manufacturer's website — prefer a product/search page over the homepage
    if manufacturer_name:
        mfr_slug = re.sub(r'[^a-z0-9]', '', manufacturer_name.lower())
        candidate_bases = [
            f"https://www.{mfr_slug}.com",
            f"https://{mfr_slug}.com",
        ]
        for mfr_base in candidate_bases:
            logger.info("Trying manufacturer site: %s", mfr_base)
            # Attempt targeted product/search page regardless of homepage availability
            product_url, product_text = _find_manufacturer_product_url(mfr_base, sku, product_name)
            if product_url and product_text:
                logger.info("Using manufacturer product/search page: %s", product_url)
                scraped_sections.append(f"[{product_url}]\n{product_text[:2500]}")
                break
            # Fall back to homepage if no targeted page was found
            mfr_homepage_text = _scrape_url(mfr_base)
            if mfr_homepage_text:
                logger.info("Falling back to manufacturer homepage: %s", mfr_base)
                scraped_sections.append(f"[{mfr_base}]\n{mfr_homepage_text[:2000]}")
                break

    # Build prompt for OpenAI
    product_context = f"Product Name: {product_name}"
    if sku:
        product_context += f"\nSKU: {sku}"
    if manufacturer_name:
        product_context += f"\nManufacturer: {manufacturer_name}"
    if primary_category:
        product_context += f"\nCategory: {primary_category}"

    scraped_content = "\n\n".join(scraped_sections) if scraped_sections else "No scraped content available."

    prompt = f"""You are a professional product copywriter for a restaurant supply e-commerce store.

Using the product details and any scraped reference content below, write a rich, well-formatted HTML product description suitable for a CKEditor field. The description should:
- Be informative and professional, targeted at restaurant and foodservice buyers
- Include a brief intro paragraph, key features as a bulleted list (<ul>/<li>), and any relevant specifications
- Be formatted with proper HTML tags (h3, p, ul, li, strong)
- Draw from the scraped content where relevant, but write in your own words
- Be 200-400 words total
- NOT include the product name as an <h1> or <h2> heading (the page already has a title)
- NOT include placeholder text or mention that content was "scraped"

{product_context}

Reference content gathered from the web:
{scraped_content[:6000]}

Return ONLY the HTML content, no markdown fences or explanatory text."""

    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model="gpt-5",
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=8192,
        )
        description_html = response.choices[0].message.content or ''
        description_html = description_html.strip()
        # Strip markdown code fences if the model wrapped output anyway
        if description_html.startswith('```'):
            description_html = re.sub(r'^```[a-z]*\n?', '', description_html)
            description_html = re.sub(r'\n?```$', '', description_html).strip()
        # Remove any script or iframe tags from generated content
        description_html = re.sub(r'<script[\s\S]*?</script>', '', description_html, flags=re.IGNORECASE)
        description_html = re.sub(r'<iframe[\s\S]*?</iframe>', '', description_html, flags=re.IGNORECASE)
        return jsonify({'description': description_html})
    except Exception as e:
        logger.exception("OpenAI generation failed")
        error_msg = str(e)
        if 'FREE_CLOUD_BUDGET_EXCEEDED' in error_msg:
            return jsonify({'error': 'AI credits budget exceeded. Please upgrade your plan to continue using AI generation.'}), 402
        return jsonify({'error': 'Description generation failed. Please try again.'}), 500