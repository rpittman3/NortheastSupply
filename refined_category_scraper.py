#!/usr/bin/env python3
"""
Refined KitchenAll.com Category Scraper
Focuses on main categories and subcategories, not individual products
"""

import requests
import json
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import logging
from app import app, db
from models import Category

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RefinedCategoryScraper:
    def __init__(self):
        self.base_url = "https://www.kitchenall.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_page_content(self, url):
        """Fetch page content with error handling"""
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def is_valid_category(self, name, url):
        """Check if this is a valid category (not a product)"""
        name_lower = name.lower()
        url_lower = url.lower()
        
        # Skip obvious product names (too specific)
        skip_patterns = [
            'model', 'inch', '"', "'", 'series', 'pro', 'deluxe', 'standard',
            'volt', 'amp', 'btu', 'cfm', 'gauge', 'stainless steel',
            'page1', 'page2', 'page3', 'page4', 'page5', 'next', 'previous'
        ]
        
        for pattern in skip_patterns:
            if pattern in name_lower:
                return False
        
        # Skip URLs that look like product pages
        if '/product' in url_lower or '/item' in url_lower:
            return False
        
        # Skip overly long names (likely product descriptions)
        if len(name) > 60:
            return False
        
        # Keep categories that contain equipment-related terms
        valid_terms = [
            'commercial', 'restaurant', 'kitchen', 'cooking', 'equipment',
            'refrigeration', 'beverage', 'display', 'preparation', 'prep',
            'dishwashing', 'washing', 'warming', 'storage', 'tables',
            'ranges', 'ovens', 'fryers', 'grills', 'steamers', 'mixers',
            'slicers', 'cutters', 'scales', 'sinks', 'hoods', 'ventilation',
            'ice', 'coffee', 'espresso', 'blenders', 'food', 'serve',
            'buffet', 'catering', 'bar', 'supplies', 'smallwares',
            'gas', 'electric', 'natural', 'propane', 'stainless'
        ]
        
        for term in valid_terms:
            if term in name_lower:
                return True
        
        # Also check brands (but be selective)
        brand_terms = [
            'american range', 'atosa', 'true', 'beverage air', 'turbo air',
            'continental', 'vollrath', 'winco', 'cambro', 'rubbermaid',
            'imperial', 'southbend', 'blodgett', 'hobart', 'manitowoc'
        ]
        
        for brand in brand_terms:
            if brand in name_lower and len(name) < 40:  # Keep short brand categories
                return True
        
        return False
    
    def extract_main_categories(self):
        """Extract main categories from homepage navigation"""
        logger.info("Extracting main categories from homepage...")
        content = self.get_page_content(self.base_url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        categories = []
        
        # Look for main navigation
        nav_selectors = ['nav', '.main-nav', '.primary-nav', '.category-nav', '.top-nav']
        
        for selector in nav_selectors:
            nav_elements = soup.select(selector)
            for nav in nav_elements:
                # Look for dropdown menus or category lists
                category_links = nav.find_all('a', href=True)
                
                for link in category_links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if href and text and self.is_valid_category(text, href):
                        full_url = urljoin(self.base_url, href)
                        
                        # Extract image if available
                        img = link.find('img') or link.find_parent().find('img') if link.find_parent() else None
                        image_url = urljoin(self.base_url, img.get('src')) if img and img.get('src') else ""
                        
                        category_data = {
                            'name': text,
                            'url': full_url,
                            'image_url': image_url,
                            'description': link.get('title', '')
                        }
                        
                        # Avoid duplicates
                        if not any(cat['url'] == full_url for cat in categories):
                            categories.append(category_data)
                            logger.info(f"Found main category: {text}")
        
        # Also look for dedicated category sections on homepage
        category_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'category' in x.lower() if x else False)
        
        for section in category_sections:
            links = section.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if href and text and self.is_valid_category(text, href):
                    full_url = urljoin(self.base_url, href)
                    
                    if not any(cat['url'] == full_url for cat in categories):
                        img = link.find('img') or section.find('img')
                        image_url = urljoin(self.base_url, img.get('src')) if img and img.get('src') else ""
                        
                        category_data = {
                            'name': text,
                            'url': full_url,
                            'image_url': image_url,
                            'description': link.get('title', '')
                        }
                        categories.append(category_data)
                        logger.info(f"Found section category: {text}")
        
        return categories
    
    def extract_subcategories(self, main_category):
        """Extract subcategories from a main category page"""
        logger.info(f"Extracting subcategories from: {main_category['name']}")
        content = self.get_page_content(main_category['url'])
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        subcategories = []
        
        # Look for subcategory navigation or filters
        subcategory_selectors = [
            '.subcategories', '.sub-categories', '.category-filters',
            '.refinement', '.facets', '.categories', '.category-list'
        ]
        
        for selector in subcategory_selectors:
            sections = soup.select(selector)
            for section in sections:
                links = section.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if href and text and self.is_valid_category(text, href):
                        full_url = urljoin(self.base_url, href)
                        
                        # Skip if it's the same as parent URL
                        if full_url == main_category['url']:
                            continue
                        
                        subcategory_data = {
                            'name': text,
                            'url': full_url,
                            'parent_name': main_category['name'],
                            'image_url': "",
                            'description': link.get('title', '')
                        }
                        
                        if not any(sub['url'] == full_url for sub in subcategories):
                            subcategories.append(subcategory_data)
                            logger.info(f"Found subcategory: {text}")
        
        return subcategories
    
    def save_to_database(self, main_categories, all_subcategories):
        """Save categories to database with improved error handling"""
        with app.app_context():
            logger.info("Saving categories to database...")
            
            # Clear existing data
            logger.info("Clearing existing categories...")
            db.session.execute(db.text("DELETE FROM product_categories"))
            db.session.execute(db.text("DELETE FROM product"))
            db.session.execute(db.text("DELETE FROM category"))
            db.session.commit()
            
            category_map = {}
            
            # First pass: create main categories
            for i, cat_data in enumerate(main_categories):
                name = cat_data['name'].strip()[:100]  # Limit name length
                if not name:
                    continue
                
                # Create unique slug
                slug = name.lower().replace(' & ', '-and-').replace(' ', '-').replace('/', '-')
                slug = ''.join(c for c in slug if c.isalnum() or c == '-').strip('-')
                
                # Ensure unique slug and name
                base_slug = slug
                base_name = name
                counter = 1
                while Category.query.filter_by(slug=slug).first() or Category.query.filter_by(name=name).first():
                    slug = f"{base_slug}-{counter}"
                    name = f"{base_name} {counter}"
                    counter += 1
                
                category = Category(
                    name=name,
                    slug=slug,
                    description=cat_data.get('description', '')[:500],
                    image_url=cat_data.get('image_url', ''),
                    is_featured=i < 8,
                    sort_order=i
                )
                
                db.session.add(category)
                category_map[cat_data['name']] = category
                logger.info(f"Added main category: {name}")
            
            try:
                db.session.commit()
                logger.info(f"Saved {len(main_categories)} main categories")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error saving main categories: {e}")
                return False
            
            # Second pass: create subcategories
            subcategory_count = 0
            for sub_data in all_subcategories:
                name = sub_data['name'].strip()[:100]
                parent_name = sub_data.get('parent_name', '').strip()
                
                if not name:
                    continue
                
                parent_category = category_map.get(parent_name)
                if not parent_category:
                    continue
                
                # Create unique slug and name
                slug = name.lower().replace(' & ', '-and-').replace(' ', '-').replace('/', '-')
                slug = ''.join(c for c in slug if c.isalnum() or c == '-').strip('-')
                
                base_slug = slug
                base_name = name
                counter = 1
                while Category.query.filter_by(slug=slug).first() or Category.query.filter_by(name=name).first():
                    slug = f"{base_slug}-{counter}"
                    name = f"{base_name} {counter}"
                    counter += 1
                
                category = Category(
                    name=name,
                    slug=slug,
                    description=sub_data.get('description', '')[:500],
                    image_url=sub_data.get('image_url', ''),
                    parent_id=parent_category.id,
                    is_featured=False,
                    sort_order=subcategory_count
                )
                
                db.session.add(category)
                subcategory_count += 1
                logger.info(f"Added subcategory: {name}")
            
            try:
                db.session.commit()
                logger.info(f"Saved {subcategory_count} subcategories")
                return True
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error saving subcategories: {e}")
                return False
    
    def scrape_categories(self):
        """Main scraping method"""
        logger.info("Starting refined category scraping...")
        
        # Get main categories
        main_categories = self.extract_main_categories()
        logger.info(f"Found {len(main_categories)} main categories")
        
        # Get subcategories (limit to avoid timeouts)
        all_subcategories = []
        for main_cat in main_categories[:8]:  # Limit to first 8 main categories
            try:
                time.sleep(1)  # Be respectful
                subcategories = self.extract_subcategories(main_cat)
                all_subcategories.extend(subcategories)
            except Exception as e:
                logger.error(f"Error processing {main_cat['name']}: {e}")
        
        logger.info(f"Found {len(all_subcategories)} subcategories total")
        
        # Save to database
        success = self.save_to_database(main_categories, all_subcategories)
        
        if success:
            logger.info("Category scraping completed successfully!")
            return True
        else:
            logger.error("Category scraping failed")
            return False

if __name__ == "__main__":
    scraper = RefinedCategoryScraper()
    success = scraper.scrape_categories()
    
    if success:
        print("✅ Category scraping completed successfully!")
    else:
        print("❌ Category scraping failed")