#!/usr/bin/env python3
"""
Database Population Script
Populates the database with scraped KitchenAll data
"""

import json
import re
import logging
from app import app, db
from models import Category, Product
from slugify import slugify

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabasePopulator:
    def __init__(self):
        self.category_map = {}  # Maps URLs to category IDs
        
    def slugify_name(self, name):
        """Create a URL-friendly slug from a name"""
        # Basic slugify function
        slug = re.sub(r'[^\w\s-]', '', name.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug.strip('-')
    
    def load_data(self, filename="kitchenall_sample.json"):
        """Load scraped data from JSON file"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"Loaded data from {filename}")
            return data
        except FileNotFoundError:
            logger.error(f"File {filename} not found")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON: {e}")
            return None
    
    def create_categories(self, categories_data):
        """Create categories in the database"""
        logger.info("Creating categories...")
        
        # Sort categories to handle parent-child relationships
        # First create all categories without parent relationships
        created_categories = []
        
        for i, cat_data in enumerate(categories_data):
            name = cat_data.get('name', '').strip()
            if not name:
                continue
            
            # Create unique slug
            base_slug = self.slugify_name(name)
            slug = base_slug
            counter = 1
            while Category.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            category = Category(
                name=name,
                slug=slug,
                description=cat_data.get('description', ''),
                image_url=cat_data.get('image_url', ''),
                is_featured=(i < 8),  # Mark first 8 as featured
                sort_order=i
            )
            
            db.session.add(category)
            created_categories.append((category, cat_data))
            
            # Map URL to category for later product assignment
            self.category_map[cat_data.get('url', '')] = category
        
        try:
            db.session.commit()
            logger.info(f"Created {len(created_categories)} categories")
            return created_categories
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating categories: {e}")
            return []
    
    def create_products(self, products_data, categories):
        """Create products in the database"""
        logger.info("Creating products...")
        
        created_products = []
        
        for i, prod_data in enumerate(products_data):
            name = prod_data.get('name', '').strip()
            if not name:
                continue
            
            # Create unique slug
            base_slug = self.slugify_name(name)
            slug = base_slug
            counter = 1
            while Product.query.filter_by(slug=slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
            
            # Create unique SKU
            sku = prod_data.get('sku', '') or f"PRS-{i+1000:04d}"
            base_sku = sku
            counter = 1
            while Product.query.filter_by(sku=sku).first():
                sku = f"{base_sku}-{counter}"
                counter += 1
            
            # Find primary category
            category_url = prod_data.get('category_url', '')
            primary_category = self.category_map.get(category_url)
            if not primary_category and categories:
                primary_category = categories[0][0]  # Default to first category
            
            if not primary_category:
                continue
            
            # Clean up price
            price = prod_data.get('price', 0)
            if isinstance(price, str):
                price_match = re.search(r'[\d,]+\.?\d*', price.replace(',', ''))
                price = float(price_match.group()) if price_match else 0.0
            
            # Prepare additional images as JSON
            additional_images = prod_data.get('additional_images', [])
            additional_images_json = json.dumps(additional_images) if additional_images else None
            
            # Prepare documents as JSON
            documents = prod_data.get('documents', [])
            documents_json = json.dumps(documents) if documents else None
            
            product = Product(
                name=name,
                slug=slug,
                sku=sku,
                short_description=prod_data.get('description', '')[:500] if prod_data.get('description') else '',
                description=prod_data.get('description', ''),
                price=price,
                primary_category_id=primary_category.id,
                brand=prod_data.get('brand', ''),
                model_number=prod_data.get('model_number', ''),
                image_url=prod_data.get('image_url', ''),
                additional_images=additional_images_json,
                weight=None,  # Not extracted
                dimensions=prod_data.get('dimensions', ''),
                in_stock=True,
                stock_quantity=10,  # Default stock
                is_featured=(i < 12),  # Mark first 12 as featured
                requires_quote=price == 0 or price > 5000,  # Large items require quote
                manual_url=prod_data.get('manual_url', ''),
                spec_sheet_url=prod_data.get('spec_sheet_url', ''),
                brochure_url=prod_data.get('brochure_url', ''),
                warranty_url=prod_data.get('warranty_url', ''),
                documents=documents_json
            )
            
            db.session.add(product)
            created_products.append(product)
        
        try:
            db.session.commit()
            logger.info(f"Created {len(created_products)} products")
            return created_products
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating products: {e}")
            return []
    
    def populate_database(self, filename="kitchenall_sample.json"):
        """Main method to populate the database"""
        with app.app_context():
            # Load scraped data
            data = self.load_data(filename)
            if not data:
                return False
            
            categories_data = data.get('categories', [])
            products_data = data.get('products', [])
            
            logger.info(f"Found {len(categories_data)} categories and {len(products_data)} products in data file")
            
            # Create categories
            categories = self.create_categories(categories_data)
            
            # Create products
            products = self.create_products(products_data, categories)
            
            logger.info(f"Database population completed: {len(categories)} categories, {len(products)} products")
            return True

def create_sample_data():
    """Create sample data if no scraped data is available"""
    with app.app_context():
        logger.info("Creating sample data...")
        
        # Sample categories
        sample_categories = [
            {"name": "Commercial Cooking Equipment", "description": "Professional cooking equipment for restaurants"},
            {"name": "Commercial Refrigeration", "description": "Commercial refrigerators and freezers"},
            {"name": "Food Preparation Equipment", "description": "Equipment for food prep and processing"},
            {"name": "Dishwashing Equipment", "description": "Commercial dishwashers and sinks"},
            {"name": "Food Display Cases", "description": "Display cases for bakeries and delis"},
            {"name": "Beverage Equipment", "description": "Coffee machines and beverage dispensers"},
            {"name": "Food Warming Equipment", "description": "Steam tables and food warmers"},
            {"name": "Storage & Work Tables", "description": "Stainless steel tables and storage solutions"}
        ]
        
        # Sample products
        sample_products = [
            {"name": "6 Burner Gas Range", "price": 1299.99, "brand": "Cookline", "sku": "CR-6B-NG"},
            {"name": "Two Door Reach-In Refrigerator", "price": 1695.00, "brand": "Coldline", "sku": "C-2RE"},
            {"name": "Commercial Deep Fryer", "price": 695.00, "brand": "Cookline", "sku": "CF40-NG"},
            {"name": "3 Compartment Sink", "price": 899.99, "brand": "Prepline", "sku": "PS-3C"},
            {"name": "Bakery Display Case", "price": 2495.00, "brand": "Marchia", "sku": "BDC-48"},
            {"name": "Commercial Mixer", "price": 1199.99, "brand": "Hobart", "sku": "HM-20"},
            {"name": "Steam Table", "price": 799.99, "brand": "Prepline", "sku": "ST-3W"},
            {"name": "Work Table", "price": 399.99, "brand": "Prepline", "sku": "WT-3024"}
        ]
        
        # Create categories
        categories = []
        for i, cat_data in enumerate(sample_categories):
            slug = cat_data['name'].lower().replace(' ', '-').replace('&', 'and')
            category = Category(
                name=cat_data['name'],
                slug=slug,
                description=cat_data['description'],
                is_featured=True,
                sort_order=i
            )
            db.session.add(category)
            categories.append(category)
        
        db.session.commit()
        
        # Create products
        for i, prod_data in enumerate(sample_products):
            slug = prod_data['name'].lower().replace(' ', '-')
            category = categories[i % len(categories)]  # Distribute across categories
            
            product = Product(
                name=prod_data['name'],
                slug=slug,
                sku=prod_data['sku'],
                description=f"Professional {prod_data['name'].lower()} for commercial kitchens.",
                price=prod_data['price'],
                primary_category_id=category.id,
                brand=prod_data['brand'],
                in_stock=True,
                stock_quantity=5,
                is_featured=True,
                requires_quote=prod_data['price'] > 2000
            )
            db.session.add(product)
        
        db.session.commit()
        logger.info(f"Created {len(categories)} sample categories and {len(sample_products)} sample products")

if __name__ == "__main__":
    populator = DatabasePopulator()
    
    # Try to use scraped data first, fall back to sample data
    if not populator.populate_database():
        logger.info("No scraped data found, creating sample data instead...")
        create_sample_data()