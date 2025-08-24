#!/usr/bin/env python3
"""
Simplified KitchenAll.com Web Scraper
Extracts categories and products from the website
"""

import requests
import re
import json
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KitchenAllScraper:
    def __init__(self):
        self.base_url = "https://www.kitchenall.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_page_content(self, url):
        """Fetch page content"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def extract_categories_from_homepage(self):
        """Extract category structure from the homepage"""
        logger.info("Extracting categories from homepage...")
        content = self.get_page_content(self.base_url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        categories = []
        
        # Look for the main category section
        category_sections = soup.find_all('div', class_=lambda x: x and 'category' in x.lower() if x else False)
        
        # Also look for navigation menus
        nav_sections = soup.find_all(['nav', 'ul', 'div'], class_=lambda x: x and any(term in x.lower() for term in ['nav', 'menu', 'category']) if x else False)
        
        all_sections = category_sections + nav_sections
        
        for section in all_sections:
            if section:
                links = section.find_all('a', href=True)
                for link in links:
                    href = link.get('href', '')
                    text = link.get_text(strip=True)
                    
                    # Filter for category-like links
                    if (href and text and len(text) > 2 and
                        ('.html' in href or '/category' in href or 
                         any(cat in href.lower() for cat in ['cooking', 'beverage', 'display', 'prep', 'dish', 'warm', 'storage', 'refriger']))):
                        
                        full_url = urljoin(self.base_url, href)
                        
                        # Find associated image
                        img = link.find('img')
                        img_url = ""
                        if img and img.get('src'):
                            img_url = urljoin(self.base_url, img.get('src'))
                        
                        category_data = {
                            'name': text,
                            'url': full_url,
                            'image_url': img_url,
                            'description': ''
                        }
                        categories.append(category_data)
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_categories = []
        for cat in categories:
            if cat['url'] not in seen_urls:
                seen_urls.add(cat['url'])
                unique_categories.append(cat)
        
        logger.info(f"Found {len(unique_categories)} categories")
        return unique_categories
    
    def extract_products_from_category(self, category_url, max_pages=5):
        """Extract products from a category page"""
        logger.info(f"Extracting products from: {category_url}")
        all_products = []
        
        for page in range(1, max_pages + 1):
            # Construct page URL
            if '?' in category_url:
                page_url = f"{category_url}&p={page}"
            else:
                page_url = f"{category_url}?p={page}"
            
            content = self.get_page_content(page_url)
            if not content:
                break
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Find product containers
            product_containers = []
            
            # Try different selectors for product listings
            selectors = [
                'div[class*="product"]',
                'li[class*="product"]',
                'div[class*="item"]',
                '.product-item',
                '.product-listing'
            ]
            
            for selector in selectors:
                containers = soup.select(selector)
                if containers:
                    product_containers = containers
                    break
            
            if not product_containers:
                logger.info(f"No products found on page {page}")
                break
            
            page_products = []
            for container in product_containers:
                product = self.extract_product_from_container(container, category_url)
                if product:
                    page_products.append(product)
            
            all_products.extend(page_products)
            logger.info(f"Found {len(page_products)} products on page {page}")
            
            # Check if there are more pages
            next_link = soup.find('a', class_=lambda x: x and 'next' in x.lower() if x else False)
            if not next_link and len(page_products) == 0:
                break
            
            time.sleep(1)  # Be respectful
        
        logger.info(f"Total products from category: {len(all_products)}")
        return all_products
    
    def extract_product_from_container(self, container, category_url):
        """Extract product info from a product container element"""
        try:
            # Find product link
            link = container.find('a', href=True)
            if not link:
                return None
            
            product_url = urljoin(self.base_url, link.get('href'))
            
            # Extract name
            name_selectors = ['h1', 'h2', 'h3', 'h4', '.product-name', '.title']
            name = ""
            for selector in name_selectors:
                name_elem = container.select_one(selector)
                if name_elem:
                    name = name_elem.get_text(strip=True)
                    break
            
            if not name:
                name = link.get_text(strip=True)
            
            if not name:
                return None
            
            # Extract price
            price = 0.0
            price_selectors = ['.price', '[class*="price"]', '.cost', '.amount']
            for selector in price_selectors:
                price_elem = container.select_one(selector)
                if price_elem:
                    price_text = price_elem.get_text(strip=True)
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                    if price_match:
                        try:
                            price = float(price_match.group())
                            break
                        except ValueError:
                            pass
            
            # Extract image
            img = container.find('img')
            image_url = ""
            if img and img.get('src'):
                image_url = urljoin(self.base_url, img.get('src'))
            
            # Extract basic info first
            product = {
                'name': name,
                'url': product_url,
                'price': price,
                'image_url': image_url,
                'category_url': category_url,
                'sku': '',
                'brand': '',
                'description': '',
                'model_number': '',
                'additional_images': [],
                'manual_url': '',
                'spec_sheet_url': '',
                'brochure_url': '',
                'warranty_url': '',
                'documents': []
            }
            
            # Get detailed info from product page
            self.extract_product_details(product)
            
            return product
            
        except Exception as e:
            logger.error(f"Error extracting product: {e}")
            return None
    
    def extract_product_details(self, product):
        """Extract detailed information from product page"""
        try:
            content = self.get_page_content(product['url'])
            if not content:
                return
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract SKU/Model number
            sku_patterns = [
                r'(?:sku|model|item)[:\s]*([a-zA-Z0-9\-_]+)',
                r'model[:\s]*([a-zA-Z0-9\-_]+)',
                r'item[:\s]*#?([a-zA-Z0-9\-_]+)'
            ]
            
            text_content = soup.get_text()
            for pattern in sku_patterns:
                match = re.search(pattern, text_content, re.I)
                if match:
                    product['sku'] = match.group(1)
                    product['model_number'] = match.group(1)
                    break
            
            # Extract brand
            brand_patterns = [
                r'(?:brand|manufacturer)[:\s]*([a-zA-Z\s]+)',
                r'by\s+([a-zA-Z\s]+)',
                r'made\s+by\s+([a-zA-Z\s]+)'
            ]
            
            for pattern in brand_patterns:
                match = re.search(pattern, text_content, re.I)
                if match:
                    brand = match.group(1).strip()
                    if len(brand) < 50:  # Reasonable brand name length
                        product['brand'] = brand
                        break
            
            # Extract description
            desc_selectors = [
                '.description',
                '.product-description',
                '.details',
                '.content',
                '[class*="description"]'
            ]
            
            for selector in desc_selectors:
                desc_elem = soup.select_one(selector)
                if desc_elem:
                    description = desc_elem.get_text(strip=True)
                    if len(description) > 50:  # Reasonable description length
                        product['description'] = description[:2000]  # Limit length
                        break
            
            # Extract additional images
            images = soup.find_all('img')
            for img in images:
                if img.get('src'):
                    img_url = urljoin(self.base_url, img.get('src'))
                    if (img_url != product['image_url'] and 
                        img_url not in product['additional_images'] and
                        any(ext in img_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.gif'])):
                        product['additional_images'].append(img_url)
            
            # Extract document links
            doc_links = soup.find_all('a', href=True)
            for link in doc_links:
                href = link.get('href', '')
                if href.lower().endswith('.pdf'):
                    doc_url = urljoin(self.base_url, href)
                    doc_name = link.get_text(strip=True)
                    
                    # Categorize documents
                    doc_lower = doc_name.lower()
                    if any(word in doc_lower for word in ['manual', 'instruction', 'guide']):
                        product['manual_url'] = doc_url
                    elif any(word in doc_lower for word in ['spec', 'specification', 'datasheet']):
                        product['spec_sheet_url'] = doc_url
                    elif any(word in doc_lower for word in ['brochure', 'catalog', 'flyer']):
                        product['brochure_url'] = doc_url
                    elif any(word in doc_lower for word in ['warranty', 'guarantee']):
                        product['warranty_url'] = doc_url
                    else:
                        product['documents'].append({
                            'name': doc_name or 'Document',
                            'url': doc_url
                        })
            
            time.sleep(0.5)  # Small delay
            
        except Exception as e:
            logger.error(f"Error extracting product details for {product['url']}: {e}")
    
    def scrape_sample_data(self):
        """Scrape a sample of categories and products for testing"""
        logger.info("Starting sample scraping...")
        
        # Get categories from homepage
        categories = self.extract_categories_from_homepage()
        
        # Limit to first few categories for testing
        sample_categories = categories[:5]
        all_products = []
        
        for category in sample_categories:
            # Get products from this category (limit to 1 page for testing)
            products = self.extract_products_from_category(category['url'], max_pages=1)
            
            # Add category info to products
            for product in products:
                product['category_name'] = category['name']
            
            all_products.extend(products)
        
        return sample_categories, all_products
    
    def save_data(self, categories, products, filename="kitchenall_sample.json"):
        """Save scraped data to JSON file"""
        data = {
            'categories': categories,
            'products': products,
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_categories': len(categories),
            'total_products': len(products)
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {filename}")

if __name__ == "__main__":
    scraper = KitchenAllScraper()
    categories, products = scraper.scrape_sample_data()
    scraper.save_data(categories, products)
    print(f"Scraped {len(categories)} categories and {len(products)} products")