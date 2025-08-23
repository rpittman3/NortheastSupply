from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from app import app, db
from models import User, Category, Product, QuoteRequest, QuoteItem
from forms import AdminLoginForm, CategoryForm, ProductForm, UserForm
from flask_login import current_user
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename

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
    total_quotes = QuoteRequest.query.count()
    
    # Recent quotes
    recent_quotes = QuoteRequest.query.order_by(QuoteRequest.created_at.desc()).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_categories=total_categories,
                         total_products=total_products,
                         total_quotes=total_quotes,
                         recent_quotes=recent_quotes)

# Category Management
@app.route('/admin/categories')
@admin_required
def admin_categories():
    categories = Category.query.order_by(Category.sort_order, Category.name).all()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/categories/add', methods=['GET', 'POST'])
@admin_required
def admin_add_category():
    form = CategoryForm()
    
    # Populate parent category choices
    categories = Category.query.filter_by(parent_id=None).all()
    form.parent_id.choices = [(0, 'No Parent')] + [(c.id, c.name) for c in categories]
    
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
    
    # Populate parent category choices
    categories = Category.query.filter_by(parent_id=None).filter(Category.id != category_id).all()
    form.parent_id.choices = [(0, 'No Parent')] + [(c.id, c.name) for c in categories]
    
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
    page = request.args.get('page', 1, type=int)
    products = Product.query.paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    form = ProductForm()
    
    # Populate category choices
    categories = Category.query.order_by(Category.name).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
    if form.validate_on_submit():
        product = Product()
        product.name = form.name.data
        product.slug = form.slug.data
        product.sku = form.sku.data
        product.category_id = form.category_id.data
        product.brand = form.brand.data
        product.model_number = form.model_number.data
        product.short_description = form.short_description.data
        product.description = form.description.data
        product.price = form.price.data
        product.cost = form.cost.data
        
        # Handle image upload
        if form.image_file.data:
            image_url = save_uploaded_image(form.image_file.data, 'products')
            product.image_url = image_url
        else:
            product.image_url = form.image_url.data
            
        product.weight = form.weight.data
        product.dimensions = form.dimensions.data
        product.in_stock = form.in_stock.data
        product.stock_quantity = form.stock_quantity.data or 0
        product.is_featured = form.is_featured.data
        product.requires_quote = form.requires_quote.data
        
        db.session.add(product)
        db.session.commit()
        flash(f'Product "{product.name}" added successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/product_form.html', form=form, title='Add Product')

@app.route('/admin/products/<int:product_id>/edit', methods=['GET', 'POST'])
@admin_required
def admin_edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    form = ProductForm(obj=product)
    
    # Populate category choices
    categories = Category.query.order_by(Category.name).all()
    form.category_id.choices = [(c.id, c.name) for c in categories]
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.slug = form.slug.data
        product.sku = form.sku.data
        product.category_id = form.category_id.data
        product.brand = form.brand.data
        product.model_number = form.model_number.data
        product.short_description = form.short_description.data
        product.description = form.description.data
        product.price = form.price.data
        product.cost = form.cost.data
        
        # Handle image upload
        if form.image_file.data:
            image_url = save_uploaded_image(form.image_file.data, 'products')
            product.image_url = image_url
        elif form.image_url.data != product.image_url:
            product.image_url = form.image_url.data
            
        product.weight = form.weight.data
        product.dimensions = form.dimensions.data
        product.in_stock = form.in_stock.data
        product.stock_quantity = form.stock_quantity.data or 0
        product.is_featured = form.is_featured.data
        product.requires_quote = form.requires_quote.data
        product.updated_at = datetime.now()
        
        db.session.commit()
        flash(f'Product "{product.name}" updated successfully!', 'success')
        return redirect(url_for('admin_products'))
    
    return render_template('admin/product_form.html', form=form, title='Edit Product', product=product)

@app.route('/admin/products/<int:product_id>/delete', methods=['POST'])
@admin_required
def admin_delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    db.session.delete(product)
    db.session.commit()
    flash(f'Product "{product.name}" deleted successfully!', 'success')
    return redirect(url_for('admin_products'))

# Quote Management
@app.route('/admin/quotes')
@admin_required
def admin_quotes():
    page = request.args.get('page', 1, type=int)
    quotes = QuoteRequest.query.order_by(QuoteRequest.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/quotes.html', quotes=quotes)

@app.route('/admin/quotes/<int:quote_id>')
@admin_required
def admin_quote_detail(quote_id):
    quote = QuoteRequest.query.get_or_404(quote_id)
    return render_template('admin/quote_detail.html', quote=quote)

@app.route('/admin/quotes/<int:quote_id>/delete', methods=['POST'])
@admin_required
def admin_delete_quote(quote_id):
    quote = QuoteRequest.query.get_or_404(quote_id)
    db.session.delete(quote)
    db.session.commit()
    flash(f'Quote request {quote.request_number} deleted successfully!', 'success')
    return redirect(url_for('admin_quotes'))

# User Management
@app.route('/admin/users')
@admin_required
def admin_users():
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20, error_out=False)
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