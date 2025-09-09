#!/usr/bin/env python3
"""
Data Import Script for Professional Restaurant Supply
Imports exported data into production database
"""

import json
import os
import sys
from datetime import datetime
from app import app, db
from models import Category, Product, User

def import_categories(categories_data):
    """Import categories in correct hierarchical order"""
    print("Importing categories...")
    
    # Clear existing categories
    Category.query.delete()
    db.session.commit()
    
    # Import in order: main categories first, then subcategories, then sub-subcategories
    imported_count = 0
    
    # Track original ID to new ID mapping
    id_mapping = {}
    
    # Sort categories by hierarchy level
    main_categories = [cat for cat in categories_data if cat['parent_id'] is None]
    sub_categories = [cat for cat in categories_data if cat['parent_id'] is not None]
    
    # Import main categories first
    for cat_data in main_categories:
        category = Category()
        category.name = cat_data['name']
        category.slug = cat_data['slug']
        category.description = cat_data['description']
        category.parent_id = None
        category.image_url = cat_data['image_url']
        category.is_featured = cat_data['is_featured']
        category.sort_order = cat_data['sort_order']
        
        db.session.add(category)
        db.session.flush()  # Get the new ID
        
        # Track ID mapping
        id_mapping[cat_data['id']] = category.id
        imported_count += 1
    
    db.session.commit()
    
    # Import subcategories and sub-subcategories
    remaining_categories = sub_categories[:]
    max_iterations = 10  # Prevent infinite loops
    iteration = 0
    
    while remaining_categories and iteration < max_iterations:
        iteration += 1
        categories_to_remove = []
        
        for cat_data in remaining_categories:
            # Check if parent has been imported
            parent_id = cat_data['parent_id']
            if parent_id in id_mapping:
                category = Category()
                category.name = cat_data['name']
                category.slug = cat_data['slug'] 
                category.description = cat_data['description']
                category.parent_id = id_mapping[parent_id]
                category.image_url = cat_data['image_url']
                category.is_featured = cat_data['is_featured']
                category.sort_order = cat_data['sort_order']
                
                db.session.add(category)
                db.session.flush()  # Get the new ID
                
                # Track ID mapping
                id_mapping[cat_data['id']] = category.id
                categories_to_remove.append(cat_data)
                imported_count += 1
        
        # Remove imported categories from remaining list
        for cat_data in categories_to_remove:
            remaining_categories.remove(cat_data)
        
        db.session.commit()
    
    if remaining_categories:
        print(f"⚠️  Warning: {len(remaining_categories)} categories could not be imported due to missing parents")
    
    print(f"✅ Imported {imported_count} categories")
    return id_mapping

def import_products(products_data, category_id_mapping):
    """Import products with updated category references"""
    print("Importing products...")
    
    # Clear existing products
    Product.query.delete()
    db.session.commit()
    
    imported_count = 0
    
    for prod_data in products_data:
        product = Product()
        product.name = prod_data['name']
        product.sku = prod_data['sku']
        product.description = prod_data['description']
        product.price = prod_data['price']
        product.image_url = prod_data['image_url']
        
        # Map old category ID to new category ID
        old_category_id = prod_data['primary_category_id']
        if old_category_id and old_category_id in category_id_mapping:
            product.primary_category_id = category_id_mapping[old_category_id]
        else:
            product.primary_category_id = None
            if old_category_id:
                print(f"⚠️  Warning: Product '{product.name}' references unknown category ID {old_category_id}")
        
        product.is_featured = prod_data['is_featured']
        product.requires_quote = prod_data['requires_quote']
        product.specification_sheet_url = prod_data['specification_sheet_url']
        product.warranty_url = prod_data['warranty_url']
        product.manual_url = prod_data['manual_url']
        
        db.session.add(product)
        imported_count += 1
    
    db.session.commit()
    print(f"✅ Imported {imported_count} products")

def import_users(users_data):
    """Import users (admin users only, regular users will sign up themselves)"""
    print("Importing users...")
    
    # Clear existing users
    User.query.delete()
    db.session.commit()
    
    imported_count = 0
    
    for user_data in users_data:
        # Only import admin users
        if user_data.get('is_admin', False):
            user = User()
            user.id = user_data['id']
            user.email = user_data['email']
            user.first_name = user_data['first_name']
            user.last_name = user_data['last_name']
            user.profile_image_url = user_data['profile_image_url']
            
            # Set additional fields if they exist
            if hasattr(User, 'company_name'):
                user.company_name = user_data.get('company_name')
            if hasattr(User, 'phone'):
                user.phone = user_data.get('phone')
            if hasattr(User, 'is_admin'):
                user.is_admin = user_data.get('is_admin', False)
            
            db.session.add(user)
            imported_count += 1
    
    db.session.commit()
    print(f"✅ Imported {imported_count} admin users")

def import_from_file(file_path):
    """Import data from a complete export file"""
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return False
    
    print(f"📁 Loading data from: {file_path}")
    
    with open(file_path, 'r') as f:
        data = json.load(f)
    
    print(f"📊 Import Summary:")
    print(f"   - {len(data['categories'])} categories")
    print(f"   - {len(data['products'])} products")
    print(f"   - {len(data['users'])} users")
    print(f"   - Export date: {data['export_date']}")
    
    # Confirm import
    response = input("\n⚠️  This will DELETE all existing data and import new data. Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Import cancelled")
        return False
    
    try:
        # Import in correct order
        category_id_mapping = import_categories(data['categories'])
        import_products(data['products'], category_id_mapping)
        import_users(data['users'])
        
        print(f"\n🎉 Import completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {str(e)}")
        db.session.rollback()
        raise

def list_export_files():
    """List available export files"""
    if not os.path.exists('exports'):
        print("❌ No exports directory found. Run export_data.py first.")
        return []
    
    files = [f for f in os.listdir('exports') if f.startswith('complete_export_') and f.endswith('.json')]
    files.sort(reverse=True)  # Most recent first
    
    if not files:
        print("❌ No export files found. Run export_data.py first.")
        return []
    
    print("📋 Available export files:")
    for i, file in enumerate(files, 1):
        print(f"   {i}. {file}")
    
    return files

if __name__ == '__main__':
    with app.app_context():
        if len(sys.argv) > 1:
            # File specified as argument
            file_path = sys.argv[1]
            if not file_path.startswith('exports/'):
                file_path = f'exports/{file_path}'
            import_from_file(file_path)
        else:
            # Interactive mode
            files = list_export_files()
            if files:
                print("\nSelect a file to import:")
                try:
                    choice = int(input("Enter number: ")) - 1
                    if 0 <= choice < len(files):
                        file_path = f'exports/{files[choice]}'
                        import_from_file(file_path)
                    else:
                        print("❌ Invalid choice")
                except (ValueError, KeyboardInterrupt):
                    print("❌ Import cancelled")