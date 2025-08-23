from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, IntegerField, DateField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional

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
