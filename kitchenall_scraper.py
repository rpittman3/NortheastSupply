#!/usr/bin/env python3
"""
KitchenAll.com Web Scraper
Extracts categories, products, images, and documents from the website
"""

import requests
import re
import json
import time
import trafilatura
from urllib.parse import urljoin, urlparse, parse_qs
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import List, Dict, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class Category:
    name: str
    url: str
    description: str = ""
    parent_id: Optional[int] = None
    image_url: str = ""
    subcategories: List['Category'] = None
    
    def __post_init__(self):
        if self.subcategories is None:
            self.subcategories = []

@dataclass
class Product:
    name: str
    url: str
    sku: str = ""
    description: str = ""
    short_description: str = ""
    price: float = 0.0
    brand: str = ""
    model_number: str = ""
    image_url: str = ""
    additional_images: List[str] = None
    weight: Optional[float] = None
    dimensions: str = ""
    manual_url: str = ""
    spec_sheet_url: str = ""
    brochure_url: str = ""
    warranty_url: str = ""
    documents: List[Dict[str, str]] = None
    category_urls: List[str] = None
    
    def __post_init__(self):
        if self.additional_images is None:
            self.additional_images = []
        if self.documents is None:
            self.documents = []
        if self.category_urls is None:
            self.category_urls = []

class KitchenAllScraper:
    def __init__(self):
        self.base_url = "https://www.kitchenall.com"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.categories = []
        self.products = []
        
    def get_page_content(self, url: str, retries: int = 3) -> Optional[str]:
        """Fetch page content with retries"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                return response.text
            except requests.RequestException as e:
                logger.warning(f"Attempt {attempt + 1} failed for {url}: {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"Failed to fetch {url} after {retries} attempts")
                    return None
    
    def extract_main_categories(self) -> List[Category]:
        """Extract main categories from the homepage"""
        logger.info("Extracting main categories...")
        content = self.get_page_content(self.base_url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        categories = []
        
        # Look for category links in the main navigation or category sections
        category_sections = soup.find_all(['div', 'section'], class_=re.compile(r'categ|menu|nav', re.I))
        
        for section in category_sections:
            links = section.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and ('.html' in href or '/category' in href or any(cat in href.lower() for cat in ['cooking', 'beverage', 'display', 'prep', 'dishwash', 'warming', 'storage', 'refriger'])):
                    full_url = urljoin(self.base_url, href)
                    name = link.get_text(strip=True)
                    if name and len(name) > 2:  # Filter out empty or very short names
                        # Try to find associated image
                        img_tag = link.find('img') or link.find_parent().find('img')
                        image_url = ""
                        if img_tag and img_tag.get('src'):
                            image_url = urljoin(self.base_url, img_tag.get('src'))
                        
                        categories.append(Category(
                            name=name,
                            url=full_url,
                            image_url=image_url
                        ))
        
        # Remove duplicates based on URL
        seen_urls = set()
        unique_categories = []
        for cat in categories:
            if cat.url not in seen_urls:
                seen_urls.add(cat.url)
                unique_categories.append(cat)
        
        logger.info(f"Found {len(unique_categories)} main categories")
        return unique_categories
    
    def extract_subcategories(self, category: Category) -> List[Category]:
        """Extract subcategories from a category page"""
        logger.info(f"Extracting subcategories for: {category.name}")
        content = self.get_page_content(category.url)
        if not content:
            return []
        
        soup = BeautifulSoup(content, 'html.parser')
        subcategories = []
        
        # Look for subcategory links
        subcategory_sections = soup.find_all(['div', 'ul', 'li'], class_=re.compile(r'subcateg|child|menu', re.I))
        
        for section in subcategory_sections:
            links = section.find_all('a', href=True)
            for link in links:
                href = link.get('href')
                if href and ('.html' in href):
                    full_url = urljoin(self.base_url, href)
                    name = link.get_text(strip=True)
                    if name and len(name) > 2 and full_url != category.url:
                        img_tag = link.find('img') or link.find_parent().find('img')
                        image_url = ""
                        if img_tag and img_tag.get('src'):
                            image_url = urljoin(self.base_url, img_tag.get('src'))
                        
                        subcategories.append(Category(
                            name=name,
                            url=full_url,
                            image_url=image_url
                        ))
        
        # Remove duplicates
        seen_urls = set()
        unique_subcategories = []
        for subcat in subcategories:
            if subcat.url not in seen_urls:
                seen_urls.add(subcat.url)
                unique_subcategories.append(subcat)
        
        logger.info(f"Found {len(unique_subcategories)} subcategories for {category.name}")
        return unique_subcategories
    
    def extract_products_from_category(self, category: Category, max_pages: int = 10) -> List[Product]:
        """Extract products from a category page with pagination"""
        logger.info(f"Extracting products from category: {category.name}")
        products = []
        page = 1
        
        while page <= max_pages:
            # Construct URL with pagination
            if '?' in category.url:
                page_url = f"{category.url}&p={page}"
            else:
                page_url = f"{category.url}?p={page}"
            
            content = self.get_page_content(page_url)
            if not content:
                break
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Look for product listings
            product_elements = soup.find_all(['div', 'li'], class_=re.compile(r'product|item', re.I))
            
            page_products = []
            for element in product_elements:
                product = self.extract_product_details(element, category.url)
                if product:
                    page_products.append(product)
            
            if not page_products:
                logger.info(f"No products found on page {page} for {category.name}")
                break
            
            products.extend(page_products)
            logger.info(f"Extracted {len(page_products)} products from page {page} of {category.name}")
            
            # Check if there's a next page
            next_page = soup.find('a', {'class': re.compile(r'next', re.I)}) or soup.find('a', string=re.compile(r'next|→', re.I))
            if not next_page:
                break
            
            page += 1
            time.sleep(1)  # Be respectful to the server
        
        logger.info(f"Total products extracted from {category.name}: {len(products)}")
        return products
    
    def extract_product_details(self, element, category_url: str) -> Optional[Product]:
        """Extract detailed product information from a product element"""
        try:
            # Find product link
            link = element.find('a', href=True)
            if not link:
                return None
            
            product_url = urljoin(self.base_url, link.get('href'))
            
            # Get product name
            name_element = element.find(['h1', 'h2', 'h3', 'h4'], class_=re.compile(r'name|title|product', re.I))
            if not name_element:
                name_element = link
            name = name_element.get_text(strip=True) if name_element else ""
            
            if not name:
                return None
            
            # Get price
            price = 0.0
            price_element = element.find(['span', 'div'], class_=re.compile(r'price', re.I))
            if price_element:
                price_text = price_element.get_text(strip=True)
                price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                if price_match:
                    try:
                        price = float(price_match.group())
                    except ValueError:
                        pass
            
            # Get image
            img_element = element.find('img')
            image_url = ""
            if img_element and img_element.get('src'):
                image_url = urljoin(self.base_url, img_element.get('src'))
            
            # Create basic product - detailed info will be extracted from product page
            product = Product(
                name=name,
                url=product_url,
                price=price,
                image_url=image_url,
                category_urls=[category_url]
            )
            
            # Extract detailed product information from product page
            self.extract_detailed_product_info(product)
            
            return product
            
        except Exception as e:
            logger.error(f"Error extracting product details: {e}")
            return None
    
    def extract_detailed_product_info(self, product: Product):
        """Extract detailed information from the product page"""
        try:
            content = self.get_page_content(product.url)
            if not content:
                return
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract SKU/Model
            sku_element = soup.find(['span', 'div'], string=re.compile(r'sku|model|item', re.I))
            if sku_element:
                sku_text = sku_element.find_parent().get_text(strip=True) if sku_element.find_parent() else sku_element.get_text(strip=True)
                sku_match = re.search(r'(?:sku|model|item)[:\s]*([a-zA-Z0-9\-]+)', sku_text, re.I)
                if sku_match:
                    product.sku = sku_match.group(1)
            
            # Extract brand
            brand_element = soup.find(['span', 'div'], string=re.compile(r'brand|manufacturer', re.I))
            if brand_element:
                brand_text = brand_element.find_parent().get_text(strip=True) if brand_element.find_parent() else brand_element.get_text(strip=True)
                brand_match = re.search(r'(?:brand|manufacturer)[:\s]*([a-zA-Z\s]+)', brand_text, re.I)
                if brand_match:
                    product.brand = brand_match.group(1).strip()
            
            # Extract description
            desc_element = soup.find(['div', 'section'], class_=re.compile(r'description|detail|content', re.I))
            if desc_element:
                product.description = desc_element.get_text(strip=True)[:2000]  # Limit length
            
            # Extract additional images
            img_elements = soup.find_all('img')
            for img in img_elements:
                if img.get('src'):
                    img_url = urljoin(self.base_url, img.get('src'))
                    if img_url != product.image_url and img_url not in product.additional_images:
                        product.additional_images.append(img_url)
            
            # Extract document links (PDFs, manuals, spec sheets)
            doc_links = soup.find_all('a', href=re.compile(r'\.pdf$', re.I))
            for link in doc_links:
                doc_url = urljoin(self.base_url, link.get('href'))
                doc_name = link.get_text(strip=True)
                
                # Categorize documents based on keywords
                doc_lower = doc_name.lower()
                if any(word in doc_lower for word in ['manual', 'instruction', 'guide']):
                    product.manual_url = doc_url
                elif any(word in doc_lower for word in ['spec', 'specification', 'datasheet']):
                    product.spec_sheet_url = doc_url
                elif any(word in doc_lower for word in ['brochure', 'catalog', 'flyer']):
                    product.brochure_url = doc_url
                elif any(word in doc_lower for word in ['warranty', 'guarantee']):
                    product.warranty_url = doc_url
                else:
                    product.documents.append({"name": doc_name, "url": doc_url})
            
            time.sleep(0.5)  # Small delay between requests
            
        except Exception as e:
            logger.error(f"Error extracting detailed product info for {product.url}: {e}")
    
    def scrape_all_data(self):
        """Main method to scrape all categories and products"""
        logger.info("Starting KitchenAll scraping...")
        
        # Extract main categories
        main_categories = self.extract_main_categories()
        
        for main_cat in main_categories:
            # Add main category to our list
            self.categories.append(main_cat)
            
            # Extract subcategories
            subcategories = self.extract_subcategories(main_cat)
            main_cat.subcategories = subcategories
            self.categories.extend(subcategories)
            
            # Extract products from main category
            products = self.extract_products_from_category(main_cat, max_pages=5)
            self.products.extend(products)
            
            # Extract products from subcategories
            for subcat in subcategories:
                subcat_products = self.extract_products_from_category(subcat, max_pages=3)
                self.products.extend(subcat_products)
        
        logger.info(f"Scraping completed! Found {len(self.categories)} categories and {len(self.products)} products")
    
    def save_to_json(self, filename: str = "kitchenall_data.json"):
        """Save scraped data to JSON file"""
        data = {
            "categories": [
                {
                    "name": cat.name,
                    "url": cat.url,
                    "description": cat.description,
                    "image_url": cat.image_url,
                    "subcategories": [sub.name for sub in cat.subcategories]
                }
                for cat in self.categories
            ],
            "products": [
                {
                    "name": prod.name,
                    "url": prod.url,
                    "sku": prod.sku,
                    "description": prod.description,
                    "price": prod.price,
                    "brand": prod.brand,
                    "model_number": prod.model_number,
                    "image_url": prod.image_url,
                    "additional_images": prod.additional_images,
                    "manual_url": prod.manual_url,
                    "spec_sheet_url": prod.spec_sheet_url,
                    "brochure_url": prod.brochure_url,
                    "warranty_url": prod.warranty_url,
                    "documents": prod.documents,
                    "category_urls": prod.category_urls
                }
                for prod in self.products
            ]
        }
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data saved to {filename}")

if __name__ == "__main__":
    scraper = KitchenAllScraper()
    scraper.scrape_all_data()
    scraper.save_to_json()