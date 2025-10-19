from datetime import datetime
from pytz import timezone
from app import db
from flask_dance.consumer.storage.sqla import OAuthConsumerMixin
from flask_login import UserMixin
from sqlalchemy import UniqueConstraint

# Define Eastern Timezone
eastern_timezone = timezone('US/Eastern')

# Helper function to get current time in Eastern Time
def eastern_now():
    return datetime.now(eastern_timezone)

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=True)
    first_name = db.Column(db.String, nullable=True)
    last_name = db.Column(db.String, nullable=True)
    profile_image_url = db.Column(db.String, nullable=True)
    company_name = db.Column(db.String, nullable=True)
    phone = db.Column(db.String, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

    created_at = db.Column(db.DateTime, default=eastern_now)
    updated_at = db.Column(db.DateTime, default=eastern_now, onupdate=eastern_now)

    # Relationships
    cart_items = db.relationship('CartItem', backref='user', lazy=True)
    quote_requests = db.relationship('QuoteRequest', backref='user', lazy=True)
    orders = db.relationship('Order', backref='user', lazy=True)

# (IMPORTANT) This table is mandatory for Replit Auth, don't drop it.
class OAuth(OAuthConsumerMixin, db.Model):
    user_id = db.Column(db.String, db.ForeignKey(User.id))
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship(User)

    __table_args__ = (UniqueConstraint(
        'user_id',
        'browser_session_key',
        'provider',
        name='uq_user_browser_session_key_provider',
    ),)

class Manufacturer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=eastern_now)
    updated_at = db.Column(db.DateTime, default=eastern_now, onupdate=eastern_now)
    
    # Relationships
    products = db.relationship('Product', backref='manufacturer', lazy=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    slug = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    image_url = db.Column(db.String(500))
    is_featured = db.Column(db.Boolean, default=False)
    sort_order = db.Column(db.Integer, default=0)
    markup = db.Column(db.Numeric(10, 4), nullable=True)  # Markup percentage as decimal

    created_at = db.Column(db.DateTime, default=eastern_now)

    # Self-referential relationship for subcategories
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    primary_products = db.relationship('Product', backref='category', foreign_keys='Product.primary_category_id', lazy=True)

# Association table for many-to-many relationship between products and categories
product_categories = db.Table('product_categories',
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True),
    db.Column('category_id', db.Integer, db.ForeignKey('category.id'), primary_key=True)
)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(200), nullable=False, unique=True)
    sku = db.Column(db.String(50), nullable=False, unique=True)
    short_description = db.Column(db.String(500))
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    cost = db.Column(db.Numeric(10, 2))
    override_markup = db.Column(db.Numeric(10, 4), nullable=True)  # Override markup percentage as decimal
    primary_category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)  # Main category for display
    manufacturer_id = db.Column(db.Integer, db.ForeignKey('manufacturer.id'), nullable=True)
    thumb_image_url = db.Column(db.String(500))
    large_image_url = db.Column(db.String(500))
    additional_images = db.Column(db.Text)  # JSON string of image URLs
    weight = db.Column(db.Numeric(8, 2))
    dimensions = db.Column(db.String(100))
    in_stock = db.Column(db.Boolean, default=True)
    stock_quantity = db.Column(db.Integer, default=0)
    is_featured = db.Column(db.Boolean, default=False)
    requires_quote = db.Column(db.Boolean, default=False)
    
    # Document/Manual fields
    bullets = db.Column(db.Text)  # HTML formatted bullet points
    manual_url = db.Column(db.String(500))  # Link to product manual
    specsheet_url = db.Column(db.String(500))  # Link to specification sheet
    brochure_url = db.Column(db.String(500))  # Link to product brochure
    warranty_url = db.Column(db.String(500))  # Link to warranty document

    created_at = db.Column(db.DateTime, default=eastern_now)
    updated_at = db.Column(db.DateTime, default=eastern_now, onupdate=eastern_now)

    # Relationships
    primary_category = db.relationship('Category', foreign_keys=[primary_category_id])
    categories = db.relationship('Category', secondary=product_categories, backref='products')
    cart_items = db.relationship('CartItem', backref='product', lazy=True)
    quote_items = db.relationship('QuoteItem', backref='product', lazy=True)
    order_items = db.relationship('OrderItem', backref='product', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    created_at = db.Column(db.DateTime, default=eastern_now)
    updated_at = db.Column(db.DateTime, default=eastern_now, onupdate=eastern_now)

class QuoteRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    request_number = db.Column(db.String(20), nullable=False, unique=True)
    status = db.Column(db.String(20), default='pending')  # pending, quoted, converted, cancelled
    notes = db.Column(db.Text)
    special_requirements = db.Column(db.Text)
    delivery_date_needed = db.Column(db.Date)

    created_at = db.Column(db.DateTime, default=eastern_now)
    updated_at = db.Column(db.DateTime, default=eastern_now, onupdate=eastern_now)

    # Relationships
    items = db.relationship('QuoteItem', backref='quote_request', lazy=True)

class QuoteItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    quote_request_id = db.Column(db.Integer, db.ForeignKey('quote_request.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    quoted_price = db.Column(db.Numeric(10, 2))

    created_at = db.Column(db.DateTime, default=eastern_now)

class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    order_number = db.Column(db.String(20), nullable=False, unique=True)
    secure_token = db.Column(db.String(64), unique=True)  # Secure token for customer order view
    payment_link = db.Column(db.String(500))  # Secure payment link for offsite payment processing
    status = db.Column(db.String(20), default='pending')  # pending, sent, shipped, delivered, cancelled
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    shipping_amount = db.Column(db.Numeric(10, 2), default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    tax_after_shipping = db.Column(db.Boolean, default=False)  # True = tax calculated on subtotal + shipping, False = tax on subtotal only

    # Shipping Information
    shipping_name = db.Column(db.String(100))
    shipping_company = db.Column(db.String(100))
    shipping_address = db.Column(db.String(200))
    shipping_city = db.Column(db.String(100))
    shipping_state = db.Column(db.String(50))
    shipping_zip = db.Column(db.String(20))
    shipping_phone = db.Column(db.String(20))
    shipping_option = db.Column(db.String(50))

    created_at = db.Column(db.DateTime, default=eastern_now)
    updated_at = db.Column(db.DateTime, default=eastern_now, onupdate=eastern_now)

    # Relationships
    items = db.relationship('OrderItem', backref='order', lazy=True)

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)

    created_at = db.Column(db.DateTime, default=eastern_now)