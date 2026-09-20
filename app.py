import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1) # needed for url_for to generate with https

# configure the database, relative to the app instance folder
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
# initialize the app with the extension, flask-sqlalchemy >= 3.0.x
db.init_app(app)

with app.app_context():
    # Make sure to import the models here or their tables won't be created
    import models  # noqa: F401
    db.create_all()
    logging.info("Database tables created")

    # Schema migration: drop stock_quantity column if it still exists
    from sqlalchemy import text, inspect
    inspector = inspect(db.engine)
    if 'product' in inspector.get_table_names():
        columns = [col['name'] for col in inspector.get_columns('product')]
        if 'stock_quantity' in columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE product DROP COLUMN stock_quantity"))
                conn.commit()
            logging.info("Dropped stock_quantity column from product table")
        if 'in_stock' in columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE product DROP COLUMN in_stock"))
                conn.commit()
            logging.info("Dropped in_stock column from product table")
        if 'meta_title' not in columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE product ADD COLUMN meta_title VARCHAR(160)"))
                conn.commit()
            logging.info("Added meta_title column to product table")
        if 'meta_description' not in columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE product ADD COLUMN meta_description VARCHAR(320)"))
                conn.commit()
            logging.info("Added meta_description column to product table")
    if 'category' in inspector.get_table_names():
        cat_columns = [col['name'] for col in inspector.get_columns('category')]
        if 'meta_title' not in cat_columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE category ADD COLUMN meta_title VARCHAR(160)"))
                conn.commit()
            logging.info("Added meta_title column to category table")
        if 'meta_description' not in cat_columns:
            with db.engine.connect() as conn:
                conn.execute(text("ALTER TABLE category ADD COLUMN meta_description VARCHAR(320)"))
                conn.commit()
            logging.info("Added meta_description column to category table")
    if 'order' in inspector.get_table_names():
        order_columns = [col['name'] for col in inspector.get_columns('order')]
        order_column_migrations = {
            'discount_code': 'VARCHAR(50)',
            'discount_percentage': 'NUMERIC(5, 2)',
            'undiscounted_subtotal': 'NUMERIC(10, 2)',
            'discount_amount': 'NUMERIC(10, 2) DEFAULT 0 NOT NULL',
        }
        with db.engine.connect() as conn:
            for column_name, column_type in order_column_migrations.items():
                if column_name not in order_columns:
                    conn.execute(text(
                        f'ALTER TABLE "order" ADD COLUMN {column_name} {column_type}'
                    ))
                    logging.info("Added %s column to order table", column_name)
            conn.commit()
