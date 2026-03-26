"""
One-time backfill script: ensures every product's primary_category_id is
present in the product_categories association table.

Run with:  python backfill_primary_categories.py
"""
from app import app, db
from models import Product, Category

with app.app_context():
    products = Product.query.all()
    fixed = 0
    for product in products:
        if product.primary_category_id:
            primary_cat = db.session.get(Category, product.primary_category_id)
            if primary_cat and primary_cat not in product.categories:
                product.categories.append(primary_cat)
                fixed += 1
                print(f'Fixed: {product.name!r} -> added category: {primary_cat.name!r}')
    db.session.commit()
    print(f'\nDone. Fixed {fixed} product(s).')
