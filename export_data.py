#!/usr/bin/env python3
"""
Data Export Script for Professional Restaurant Supply
Exports development database data for migration to production
"""

import json
import os
from datetime import datetime
from app import app, db
from models import Category, Product, User, QuoteRequest

def export_categories():
    """Export all categories in hierarchical order"""
    print("Exporting categories...")
    
    categories = Category.query.order_by(Category.sort_order, Category.name).all()
    
    category_data = []
    for category in categories:
        category_dict = {
            'id': category.id,
            'name': category.name,
            'slug': category.slug,
            'description': category.description,
            'parent_id': category.parent_id,
            'image_url': category.image_url,
            'is_featured': category.is_featured,
            'sort_order': category.sort_order,
            'created_at': category.created_at.isoformat() if category.created_at else None,
            'updated_at': category.updated_at.isoformat() if category.updated_at else None
        }
        category_data.append(category_dict)
    
    print(f"Exported {len(category_data)} categories")
    return category_data

def export_products():
    """Export all products with category relationships"""
    print("Exporting products...")
    
    products = Product.query.all()
    
    product_data = []
    for product in products:
        product_dict = {
            'id': product.id,
            'name': product.name,
            'sku': product.sku,
            'description': product.description,
            'price': float(product.price) if product.price else None,
            'image_url': product.image_url,
            'primary_category_id': product.primary_category_id,
            'is_featured': product.is_featured,
            'requires_quote': product.requires_quote,
            'specification_sheet_url': product.specification_sheet_url,
            'warranty_url': product.warranty_url,
            'manual_url': product.manual_url,
            'created_at': product.created_at.isoformat() if product.created_at else None,
            'updated_at': product.updated_at.isoformat() if product.updated_at else None
        }
        product_data.append(product_dict)
    
    print(f"Exported {len(product_data)} products")
    return product_data

def export_users():
    """Export admin users (excluding OAuth tokens for security)"""
    print("Exporting users...")
    
    users = User.query.all()
    
    user_data = []
    for user in users:
        user_dict = {
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'profile_image_url': user.profile_image_url,
            'company_name': getattr(user, 'company_name', None),
            'phone': getattr(user, 'phone', None),
            'is_admin': getattr(user, 'is_admin', False),
            'created_at': user.created_at.isoformat() if user.created_at else None,
            'updated_at': user.updated_at.isoformat() if user.updated_at else None
        }
        user_data.append(user_dict)
    
    print(f"Exported {len(user_data)} users")
    return user_data

def export_all_data():
    """Export all data to JSON files"""
    print("Starting data export...")
    
    # Create exports directory if it doesn't exist
    os.makedirs('exports', exist_ok=True)
    
    # Export timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Export categories
    categories = export_categories()
    with open(f'exports/categories_{timestamp}.json', 'w') as f:
        json.dump(categories, f, indent=2, default=str)
    
    # Export products
    products = export_products()
    with open(f'exports/products_{timestamp}.json', 'w') as f:
        json.dump(products, f, indent=2, default=str)
    
    # Export users
    users = export_users()
    with open(f'exports/users_{timestamp}.json', 'w') as f:
        json.dump(users, f, indent=2, default=str)
    
    # Create a complete export file
    complete_export = {
        'export_timestamp': timestamp,
        'export_date': datetime.now().isoformat(),
        'categories': categories,
        'products': products,
        'users': users,
        'stats': {
            'total_categories': len(categories),
            'total_products': len(products),
            'total_users': len(users)
        }
    }
    
    with open(f'exports/complete_export_{timestamp}.json', 'w') as f:
        json.dump(complete_export, f, indent=2, default=str)
    
    print(f"\n✅ Export completed successfully!")
    print(f"📁 Files created in 'exports/' directory:")
    print(f"   - categories_{timestamp}.json")
    print(f"   - products_{timestamp}.json") 
    print(f"   - users_{timestamp}.json")
    print(f"   - complete_export_{timestamp}.json")
    print(f"\n📊 Export Summary:")
    print(f"   - {len(categories)} categories")
    print(f"   - {len(products)} products")
    print(f"   - {len(users)} users")
    
    return timestamp

if __name__ == '__main__':
    with app.app_context():
        try:
            timestamp = export_all_data()
            print(f"\n🎉 Data export successful! Use timestamp: {timestamp}")
        except Exception as e:
            print(f"❌ Export failed: {str(e)}")
            raise