#!/usr/bin/env python3
"""
KitchenAll.com Category Scraper
Focused scraper to extract all categories and subcategories
"""

import requests
import json
import time
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import logging
from app import app, db
from models import Category

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KitchenAllCategoryScraper:
    def __init__(self):
        self.base_url = "https://www.kitchenall.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.categories = []
        self.all_category_urls = set()
        
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
    
    def extract_categories_from_page(self, url, is_subcategory=False, parent_name=""):
        """Extract categories from a page"""
        content = self.get_page_content(url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        found_categories = []
        
        # Look for navigation menus and category sections
        nav_selectors = [
            'nav',
            '.navigation',
            '.nav-menu', 
            '.category-menu',
            '.main-nav',
            '[class*="nav"]',
            '[class*="menu"]',
            '[class*="category"]'
        ]
        
        for selector in nav_selectors:
            nav_elements = soup.select(selector)
            for nav in nav_elements:
                links = nav.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if self.is_category_link(href, text):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in self.all_category_urls:
                            self.all_category_urls.add(full_url)
                            
                            category_data = {
                                'name': text,
                                'url': full_url,
                                'is_subcategory': is_subcategory,
                                'parent_name': parent_name,
                                'description': self.extract_category_description(link),
                                'image_url': self.extract_category_image(link)
                            }
                            found_categories.append(category_data)
                            logger.info(f"Found category: {text} ({'subcategory' if is_subcategory else 'main'})")
        
        # Also look for category listings on the page
        category_listing_selectors = [
            '.category-list',
            '.category-grid',
            '.categories',
            '[class*="category-item"]',
            '[class*="cat-item"]'
        ]
        
        for selector in category_listing_selectors:
            listings = soup.select(selector)
            for listing in listings:
                links = listing.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    if self.is_category_link(href, text):
                        full_url = urljoin(self.base_url, href)
                        if full_url not in self.all_category_urls:
                            self.all_category_urls.add(full_url)
                            
                            category_data = {
                                'name': text,
                                'url': full_url,
                                'is_subcategory': is_subcategory,
                                'parent_name': parent_name,
                                'description': self.extract_category_description(link),
                                'image_url': self.extract_category_image(link)
                            }
                            found_categories.append(category_data)
                            logger.info(f"Found category listing: {text}")
        
        return found_categories
    
    def is_category_link(self, href, text):
        """Check if a link is likely a category link"""
        if not href or not text or len(text) < 2:
            return False
        
        # Skip non-category links
        skip_keywords = [
            'javascript:', 'mailto:', 'tel:', '#', 'login', 'register', 'cart', 
            'checkout', 'account', 'contact', 'about', 'privacy', 'terms',
            'search', 'help', 'support', 'blog', 'news', 'faq'
        ]
        
        href_lower = href.lower()
        text_lower = text.lower()
        
        for skip in skip_keywords:
            if skip in href_lower or skip in text_lower:
                return False
        
        # Look for category indicators
        category_indicators = [
            '.html', '/category', '/categories', '/cat/', '/dept/', 
            'cooking', 'kitchen', 'restaurant', 'commercial', 'equipment',
            'refrigeration', 'beverage', 'display', 'prep', 'dish', 'wash',
            'warming', 'storage', 'table', 'sink', 'fryer', 'grill', 'oven',
            'mixer', 'slicer', 'cutter', 'scale', 'holder', 'rack'
        ]
        
        for indicator in category_indicators:
            if indicator in href_lower:
                return True
        
        # Check if text looks like a category name
        equipment_terms = [
            'equipment', 'supplies', 'kitchen', 'cooking', 'refrigeration',
            'beverage', 'display', 'prep', 'preparation', 'dishwash', 'warming',
            'storage', 'tables', 'commercial', 'professional', 'restaurant'
        ]
        
        for term in equipment_terms:
            if term in text_lower:
                return True
        
        return False
    
    def extract_category_description(self, link_element):
        """Extract description for a category"""
        # Look for title attributes or nearby description text
        description = link_element.get('title', '')
        if description:
            return description
        
        # Look in parent element for description
        parent = link_element.find_parent()
        if parent:
            desc_text = parent.get_text(strip=True)
            if len(desc_text) > len(link_element.get_text(strip=True)) + 10:
                # Remove the link text from description
                link_text = link_element.get_text(strip=True)
                description = desc_text.replace(link_text, '').strip()
                return description[:200]  # Limit length
        
        return ""
    
    def extract_category_image(self, link_element):
        """Extract image URL for a category"""
        # Look for img tag in or near the link
        img = link_element.find('img')
        if not img:
            img = link_element.find_parent().find('img') if link_element.find_parent() else None
        
        if img and img.get('src'):
            return urljoin(self.base_url, img.get('src'))
        
        return ""
    
    def scrape_all_categories(self):
        """Main method to scrape all categories"""
        logger.info("Starting category scraping from KitchenAll.com...")
        
        # Start with homepage
        main_categories = self.extract_categories_from_page(self.base_url)
        self.categories.extend(main_categories)
        
        # Get subcategories from each main category
        for main_cat in main_categories[:10]:  # Limit to first 10 to avoid timeout
            try:
                time.sleep(1)  # Be respectful to the server
                subcategories = self.extract_categories_from_page(
                    main_cat['url'], 
                    is_subcategory=True, 
                    parent_name=main_cat['name']
                )
                self.categories.extend(subcategories)
            except Exception as e:
                logger.error(f"Error processing {main_cat['name']}: {e}")
                continue
        
        # Remove duplicates based on URL
        unique_categories = []
        seen_urls = set()
        for cat in self.categories:
            if cat['url'] not in seen_urls:
                seen_urls.add(cat['url'])
                unique_categories.append(cat)
        
        self.categories = unique_categories
        logger.info(f"Found {len(self.categories)} unique categories")
        
        return self.categories
    
    def save_to_database(self):
        """Save scraped categories to database"""
        with app.app_context():
            logger.info("Saving categories to database...")
            
            # First pass: create all main categories
            main_categories = [cat for cat in self.categories if not cat['is_subcategory']]
            category_map = {}  # Maps category names to category objects
            
            for i, cat_data in enumerate(main_categories):
                name = cat_data['name'].strip()
                if not name or len(name) > 100:  # Skip invalid names
                    continue
                
                # Create slug
                slug = name.lower().replace(' & ', '-and-').replace(' ', '-').replace('/', '-')
                slug = ''.join(c for c in slug if c.isalnum() or c == '-')
                slug = slug.strip('-')
                
                # Ensure unique slug
                base_slug = slug
                counter = 1
                while Category.query.filter_by(slug=slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                category = Category(
                    name=name,
                    slug=slug,
                    description=cat_data.get('description', '')[:500],  # Limit description length
                    image_url=cat_data.get('image_url', ''),
                    is_featured=i < 8,  # First 8 are featured
                    sort_order=i
                )
                
                db.session.add(category)
                category_map[name] = category
                logger.info(f"Added main category: {name}")
            
            try:
                db.session.commit()
                logger.info(f"Saved {len(main_categories)} main categories")
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error saving main categories: {e}")
                return False
            
            # Second pass: create subcategories
            subcategories = [cat for cat in self.categories if cat['is_subcategory']]
            
            for cat_data in subcategories:
                name = cat_data['name'].strip()
                parent_name = cat_data.get('parent_name', '').strip()
                
                if not name or len(name) > 100:  # Skip invalid names
                    continue
                
                # Find parent category
                parent_category = category_map.get(parent_name)
                if not parent_category:
                    # Try to find by partial match
                    for parent_name_key in category_map.keys():
                        if parent_name.lower() in parent_name_key.lower() or parent_name_key.lower() in parent_name.lower():
                            parent_category = category_map[parent_name_key]
                            break
                
                # Create slug
                slug = name.lower().replace(' & ', '-and-').replace(' ', '-').replace('/', '-')
                slug = ''.join(c for c in slug if c.isalnum() or c == '-')
                slug = slug.strip('-')
                
                # Ensure unique slug
                base_slug = slug
                counter = 1
                while Category.query.filter_by(slug=slug).first():
                    slug = f"{base_slug}-{counter}"
                    counter += 1
                
                category = Category(
                    name=name,
                    slug=slug,
                    description=cat_data.get('description', '')[:500],
                    image_url=cat_data.get('image_url', ''),
                    parent_id=parent_category.id if parent_category else None,
                    is_featured=False,  # Subcategories not featured
                    sort_order=len(category_map)
                )
                
                db.session.add(category)
                logger.info(f"Added subcategory: {name} (parent: {parent_name})")
            
            try:
                db.session.commit()
                logger.info(f"Saved {len(subcategories)} subcategories")
                return True
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error saving subcategories: {e}")
                return False
    
    def save_to_json(self, filename="kitchenall_categories.json"):
        """Save scraped data to JSON file"""
        data = {
            'categories': self.categories,
            'total_categories': len(self.categories),
            'main_categories': len([c for c in self.categories if not c['is_subcategory']]),
            'subcategories': len([c for c in self.categories if c['is_subcategory']])
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved data to {filename}")

if __name__ == "__main__":
    scraper = KitchenAllCategoryScraper()
    categories = scraper.scrape_all_categories()
    
    # Save to both JSON and database
    scraper.save_to_json()
    scraper.save_to_database()
    
    print(f"Scraped {len(categories)} categories")
    main_count = len([c for c in categories if not c['is_subcategory']])
    sub_count = len([c for c in categories if c['is_subcategory']])
    print(f"Main categories: {main_count}")
    print(f"Subcategories: {sub_count}")