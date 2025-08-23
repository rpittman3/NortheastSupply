from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DateField, BooleanField, DecimalField, FileField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional
from flask_wtf.file import FileAllowed

class QuoteRequestForm(FlaskForm):
    company_name = StringField('Company Name', validators=[DataRequired(), Length(min=2, max=100)])
    contact_name = StringField('Contact Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Phone', validators=[DataRequired(), Length(min=10, max=20)])
    delivery_date_needed = DateField('Delivery Date Needed', validators=[Optional()])
    special_requirements = TextAreaField('Special Requirements', validators=[Optional(), Length(max=1000)])
    notes = TextAreaField('Additional Notes', validators=[Optional(), Length(max=1000)])

class CheckoutForm(FlaskForm):
    shipping_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    shipping_company = StringField('Company Name', validators=[Optional(), Length(max=100)])
    shipping_address = StringField('Address', validators=[DataRequired(), Length(min=5, max=200)])
    shipping_city = StringField('City', validators=[DataRequired(), Length(min=2, max=100)])
    shipping_state = SelectField('State', validators=[DataRequired()], choices=[
        ('', 'Select State'),
        ('AL', 'Alabama'), ('AK', 'Alaska'), ('AZ', 'Arizona'), ('AR', 'Arkansas'),
        ('CA', 'California'), ('CO', 'Colorado'), ('CT', 'Connecticut'), ('DE', 'Delaware'),
        ('FL', 'Florida'), ('GA', 'Georgia'), ('HI', 'Hawaii'), ('ID', 'Idaho'),
        ('IL', 'Illinois'), ('IN', 'Indiana'), ('IA', 'Iowa'), ('KS', 'Kansas'),
        ('KY', 'Kentucky'), ('LA', 'Louisiana'), ('ME', 'Maine'), ('MD', 'Maryland'),
        ('MA', 'Massachusetts'), ('MI', 'Michigan'), ('MN', 'Minnesota'), ('MS', 'Mississippi'),
        ('MO', 'Missouri'), ('MT', 'Montana'), ('NE', 'Nebraska'), ('NV', 'Nevada'),
        ('NH', 'New Hampshire'), ('NJ', 'New Jersey'), ('NM', 'New Mexico'), ('NY', 'New York'),
        ('NC', 'North Carolina'), ('ND', 'North Dakota'), ('OH', 'Ohio'), ('OK', 'Oklahoma'),
        ('OR', 'Oregon'), ('PA', 'Pennsylvania'), ('RI', 'Rhode Island'), ('SC', 'South Carolina'),
        ('SD', 'South Dakota'), ('TN', 'Tennessee'), ('TX', 'Texas'), ('UT', 'Utah'),
        ('VT', 'Vermont'), ('VA', 'Virginia'), ('WA', 'Washington'), ('WV', 'West Virginia'),
        ('WI', 'Wisconsin'), ('WY', 'Wyoming')
    ])
    shipping_zip = StringField('ZIP Code', validators=[DataRequired(), Length(min=5, max=10)])
    shipping_phone = StringField('Phone', validators=[DataRequired(), Length(min=10, max=20)])

class AccountUpdateForm(FlaskForm):
    first_name = StringField('First Name', validators=[Optional(), Length(max=50)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=50)])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=100)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])

# Admin Forms
class AdminLoginForm(FlaskForm):
    admin_password = StringField('Admin Password', validators=[DataRequired()])

class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=100)])
    slug = StringField('URL Slug', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    parent_id = SelectField('Parent Category', coerce=int, validators=[Optional()])
    image_url = StringField('Image URL', validators=[Optional(), Length(max=500)])
    image_file = FileField('Upload Image', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')])
    is_featured = BooleanField('Featured Category')
    sort_order = IntegerField('Sort Order', validators=[Optional(), NumberRange(min=0)])

class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(min=2, max=200)])
    slug = StringField('URL Slug', validators=[DataRequired(), Length(min=2, max=200)])
    sku = StringField('SKU', validators=[DataRequired(), Length(min=2, max=50)])
    primary_category_id = SelectField('Primary Category', coerce=int, validators=[DataRequired()])
    category_ids = SelectMultipleField('Additional Categories', coerce=int)
    brand = StringField('Brand', validators=[Optional(), Length(max=100)])
    model_number = StringField('Model Number', validators=[Optional(), Length(max=100)])
    short_description = StringField('Short Description', validators=[Optional(), Length(max=500)])
    description = TextAreaField('Description', validators=[Optional()])
    price = DecimalField('Price', validators=[DataRequired(), NumberRange(min=0)])
    cost = DecimalField('Cost', validators=[Optional(), NumberRange(min=0)])
    image_url = StringField('Image URL', validators=[Optional(), Length(max=500)])
    image_file = FileField('Upload Image', validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Images only!')])
    weight = DecimalField('Weight (lbs)', validators=[Optional(), NumberRange(min=0)])
    dimensions = StringField('Dimensions', validators=[Optional(), Length(max=100)])
    in_stock = BooleanField('In Stock')
    stock_quantity = IntegerField('Stock Quantity', validators=[Optional(), NumberRange(min=0)])
    is_featured = BooleanField('Featured Product')
    requires_quote = BooleanField('Requires Quote')

class UserForm(FlaskForm):
    first_name = StringField('First Name', validators=[Optional(), Length(max=50)])
    last_name = StringField('Last Name', validators=[Optional(), Length(max=50)])
    email = StringField('Email', validators=[Optional(), Email()])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=100)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    is_admin = BooleanField('Admin User')
