from flask import render_template, request, redirect, url_for, flash, session, jsonify
from functools import wraps
from app import app, db
from models import User, Category, Product, QuoteRequest, QuoteItem, product_categories
from forms import AdminLoginForm, CategoryForm, ProductForm, UserForm
from flask_login import current_user
from datetime import datetime
import os
import uuid
from werkzeug.utils import secure_filename
from sqlalchemy import text

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
    products = Product.query.all()
    return render_template('admin/products.html', products=products)

@app.route('/admin/products/add', methods=['GET', 'POST'])
@admin_required
def admin_add_product():
    form = ProductForm()
    
    # Populate category choices
    categories = Category.query.order_by(Category.name).all()
    form.primary_category_id.choices = [(c.id, c.name) for c in categories]
    form.category_ids.choices = [(c.id, c.name) for c in categories]
    
    if form.validate_on_submit():
        product = Product()
        product.name = form.name.data
        product.slug = form.slug.data
        product.sku = form.sku.data
        product.primary_category_id = form.primary_category_id.data
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
        db.session.flush()  # Get the product ID
        
        # Add selected categories
        selected_categories = Category.query.filter(Category.id.in_(form.category_ids.data)).all()
        product.categories.extend(selected_categories)
        
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
    form.primary_category_id.choices = [(c.id, c.name) for c in categories]
    form.category_ids.choices = [(c.id, c.name) for c in categories]
    
    # Pre-populate form with current category assignments
    if request.method == 'GET':
        form.category_ids.data = [c.id for c in product.categories]
    
    if form.validate_on_submit():
        product.name = form.name.data
        product.slug = form.slug.data
        product.sku = form.sku.data
        product.primary_category_id = form.primary_category_id.data
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
        
        # Update categories
        product.categories.clear()
        selected_categories = Category.query.filter(Category.id.in_(form.category_ids.data)).all()
        product.categories.extend(selected_categories)
        
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
    quotes = QuoteRequest.query.order_by(QuoteRequest.created_at.desc()).all()
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
@app.route('/admin/bulk-category-assignment')
@admin_required
def admin_bulk_category_assignment():
    """Display bulk category assignment page"""
    categories = Category.query.order_by(Category.name).all()
    
    # Get search query and category filter from request
    search_query = request.args.get('search', '')
    category_id = request.args.get('category_id', type=int)
    
    # Start with all products query
    products_query = Product.query
    
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
                         selected_category_id=category_id)

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