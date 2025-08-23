
from app import app, db
from models import Product, Category, product_categories

def migrate_product_categories():
    """Migrate existing category_id to the new many-to-many structure"""
    with app.app_context():
        print("Starting migration...")
        
        # Get all products with their current category_id
        products = db.session.execute(
            db.text("SELECT id, category_id FROM product WHERE category_id IS NOT NULL")
        ).fetchall()
        
        print(f"Found {len(products)} products to migrate")
        
        # First, add primary_category_id column if it doesn't exist
        try:
            db.session.execute(
                db.text("ALTER TABLE product ADD COLUMN primary_category_id INTEGER")
            )
            db.session.commit()
            print("Added primary_category_id column")
        except Exception as e:
            print(f"Column might already exist: {e}")
            db.session.rollback()
        
        # Update primary_category_id with existing category_id values
        for product_id, category_id in products:
            db.session.execute(
                db.text("UPDATE product SET primary_category_id = :cat_id WHERE id = :prod_id"),
                {"cat_id": category_id, "prod_id": product_id}
            )
            
            # Also add to the many-to-many table
            db.session.execute(
                db.text("INSERT OR IGNORE INTO product_categories (product_id, category_id) VALUES (:prod_id, :cat_id)"),
                {"prod_id": product_id, "cat_id": category_id}
            )
        
        db.session.commit()
        
        # Drop the old category_id column
        try:
            db.session.execute(db.text("ALTER TABLE product DROP COLUMN category_id"))
            db.session.commit()
            print("Dropped old category_id column")
        except Exception as e:
            print(f"Error dropping column: {e}")
            db.session.rollback()
        
        print("Migration completed successfully!")

if __name__ == '__main__':
    migrate_product_categories()
