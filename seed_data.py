"""
Seed data script for Professional Restaurant Supply
Run this script to populate the database with sample data
"""

from app import app, db
from models import Category, Product
import random

def create_categories():
    """Create product categories"""
    categories_data = [
        {
            'name': 'Restaurant Equipment',
            'slug': 'restaurant-equipment',
            'description': 'Professional cooking equipment for commercial kitchens',
            'image_url': 'https://pixabay.com/get/gc9ff3afa396f9345e1af7a4b675b547642163ffdb3b99b3699d63d9c0b2135055ea7fe917986cfb0f182e3c89658d507c6eb8d31115ad0e524e76893289561f7_1280.jpg',
            'is_featured': True,
            'sort_order': 1,
            'children': [
                {
                    'name': 'Commercial Ovens',
                    'slug': 'commercial-ovens',
                    'description': 'Convection, deck, and specialty ovens for professional kitchens',
                    'image_url': 'https://pixabay.com/get/ga54f5834253bc0697e0b25702993bcee631895bfe5dd943445ab220e28d98c3eaedcf74ddf9a4122c0a872ef93aea20fc06091f245423a81194bc666282dc414_1280.jpg',
                    'sort_order': 1
                },
                {
                    'name': 'Commercial Fryers',
                    'slug': 'commercial-fryers',
                    'description': 'Deep fryers and frying equipment for high-volume cooking',
                    'image_url': 'https://pixabay.com/get/ge16afaee6f473ad149f1fd9e24e366d38ae1037fe123f3c3952e0fc90a35c17dd3093638d90740db766240b6b187cd4d94d1e7c57f168e094faf69416e029bfc_1280.jpg',
                    'sort_order': 2
                },
                {
                    'name': 'Commercial Grills',
                    'slug': 'commercial-grills',
                    'description': 'Charbroilers, griddles, and specialty grills',
                    'image_url': 'https://pixabay.com/get/g80f9817735b20dcf583f39537cc16e845bea80ff449d98c5a80aed57cd1713684cf14e3dc4e52883b823c8894ac9f5bd87d1a628aa07f7312ffffbf00eb58df8_1280.jpg',
                    'sort_order': 3
                },
                {
                    'name': 'Commercial Ranges',
                    'slug': 'commercial-ranges',
                    'description': 'Gas and electric ranges for professional cooking',
                    'image_url': 'https://pixabay.com/get/geb49094e8c6a65e7eaf77fab0a34f5d0845a1d31874b79db767dc8877db110c5839e5d8008af7150c3d0f99a3809bd6be4beb13712fea2a0f77a3c4558cb14bd_1280.jpg',
                    'sort_order': 4
                },
                {
                    'name': 'Food Preparation Equipment',
                    'slug': 'food-prep-equipment',
                    'description': 'Mixers, slicers, and food processing equipment',
                    'image_url': 'https://pixabay.com/get/g962218f7395369778de71175e196a7c0ef157f897c72d0a8f0ed0a40b4f773a6c5520b0e154a77870036d09d5677c01e9d5d989389a83cb24d96dbb07eb5e1db_1280.jpg',
                    'sort_order': 5
                },
                {
                    'name': 'Specialty Cooking Equipment',
                    'slug': 'specialty-cooking-equipment',
                    'description': 'Pizza ovens, steamers, and specialized cooking equipment',
                    'image_url': 'https://pixabay.com/get/gf2a88f8afd58accab1167ef381d69aba9b83efcd2012c554723868e28552629529fe5cac0c223adf7753e73861339ae7a138550e2550d321f9cc9e8e36ec9a20_1280.jpg',
                    'sort_order': 6
                }
            ]
        },
        {
            'name': 'Commercial Refrigeration',
            'slug': 'commercial-refrigeration',
            'description': 'Professional refrigeration solutions for restaurants',
            'image_url': 'https://pixabay.com/get/gad05af8e2967992efb30dfe8d66c2bd60d504496aae6ef5108b10fac1a4c582c554b7b25cf9b4121a37c17e72c318b641d41aa409a91efd60402292cb46b23a1_1280.jpg',
            'is_featured': True,
            'sort_order': 2,
            'children': [
                {
                    'name': 'Walk-In Coolers',
                    'slug': 'walk-in-coolers',
                    'description': 'Large capacity walk-in refrigeration units',
                    'image_url': 'https://pixabay.com/get/gd1454a8140943ebc496331b11e9e3599e19c9498042536926cc0150c2f7da748e45edf8410f00ffd251404f522b219b9de348d5ca68291a5e2dd226b09cc2ff1_1280.jpg',
                    'sort_order': 1
                },
                {
                    'name': 'Reach-In Refrigerators',
                    'slug': 'reach-in-refrigerators',
                    'description': 'Upright commercial refrigerators and freezers',
                    'image_url': 'https://pixabay.com/get/gef9b78219a080271116447a27bccfb713c5b191a286935c1d853905e7706c0a290535b73f100008656ff0fefaa585ca6abb1cde13e184bd21a8407e139a5d820_1280.jpg',
                    'sort_order': 2
                },
                {
                    'name': 'Under-Counter Refrigeration',
                    'slug': 'under-counter-refrigeration',
                    'description': 'Space-saving under-counter coolers and freezers',
                    'image_url': 'https://pixabay.com/get/gff5e6fa4dd8634b84a6977f1f433aa8f1f24fd433a92c059a88228d6b796662dc980a210b566bac66f8fd8dc1569c6ded78ada3ad3c76b661d932cb8d21476a9_1280.jpg',
                    'sort_order': 3
                },
                {
                    'name': 'Display Cases',
                    'slug': 'display-cases',
                    'description': 'Refrigerated display cases for retail and foodservice',
                    'image_url': 'https://pixabay.com/get/gad05af8e2967992efb30dfe8d66c2bd60d504496aae6ef5108b10fac1a4c582c554b7b25cf9b4121a37c17e72c318b641d41aa409a91efd60402292cb46b23a1_1280.jpg',
                    'sort_order': 4
                }
            ]
        },
        {
            'name': 'Restaurant Furniture',
            'slug': 'restaurant-furniture',
            'description': 'Commercial dining furniture and seating solutions',
            'image_url': 'https://pixabay.com/get/g499e5c9350e9bb8a8f95df60ca09214fee7bf731a37d3f47a375e15e5e0e8557f3f782fc8c70f2e764a4b43a456b46f66118f6e7ffe4abb6d8a922e7e89e9ef6_1280.jpg',
            'is_featured': True,
            'sort_order': 3,
            'children': [
                {
                    'name': 'Restaurant Tables',
                    'slug': 'restaurant-tables',
                    'description': 'Commercial dining tables in various sizes and styles',
                    'image_url': 'https://pixabay.com/get/gce0b6e86f3c5767917b1939a38ee34d756891736b90d2fb49d40a9761e148d2f926b84ecdf534dfacab38ea1643d02801857c1398ac6088a23ad2427ee696584_1280.jpg',
                    'sort_order': 1
                },
                {
                    'name': 'Restaurant Chairs',
                    'slug': 'restaurant-chairs',
                    'description': 'Comfortable and durable dining chairs for restaurants',
                    'image_url': 'https://pixabay.com/get/g422c8ed9cf799e1ef03e8e59ca53c98cefb8eab9c43030359274fd83b324b38a39987022d6bc8808db39dee49a4feb1010af659ee9ee0b2598399f8a529189f7_1280.jpg',
                    'sort_order': 2
                },
                {
                    'name': 'Restaurant Booths',
                    'slug': 'restaurant-booths',
                    'description': 'Custom and standard restaurant booth seating',
                    'image_url': 'https://pixabay.com/get/gca97dfdbbf65dd0176181d79ef6817fda54d004890c4b01cdf4e7f38f4cebfdd2751a24d914b4e2c0e8c1ac3dadb0afc860769ea13ebd4ad18772103ca2636fa_1280.jpg',
                    'sort_order': 3
                },
                {
                    'name': 'Bar Stools',
                    'slug': 'bar-stools',
                    'description': 'Commercial bar stools and counter height seating',
                    'image_url': 'https://pixabay.com/get/g2e78645540c9f0055b030eff0db90268d92d14d9a65d268ee4a9f1fcb5075fa50fded69b955b0e2fd3bfcd095da42235193e3d936eb00521b8ae407b0dde9dc2_1280.jpg',
                    'sort_order': 4
                },
                {
                    'name': 'Outdoor Furniture',
                    'slug': 'outdoor-furniture',
                    'description': 'Weather-resistant outdoor dining furniture',
                    'image_url': 'https://pixabay.com/get/g6f138a1e59b35b23730b0e91d7835d65fd8d4c3a703090e63a1576bbeba6d0459e43ff5ddbe4ed87b37aa03326c1c8522d18ebfe1a86d513735da029fa1c2235_1280.jpg',
                    'sort_order': 5
                }
            ]
        },
        {
            'name': 'Smallwares',
            'slug': 'smallwares',
            'description': 'Essential kitchen tools and small equipment',
            'image_url': 'https://pixabay.com/get/gc00468883f7687522738492f7b9167fca5dcb35eba1623167aeba8e2ddf4edaa1d7ed2581acafa6df076bf847511e19c37214339c285106bc1e2b797f76f78d7_1280.jpg',
            'is_featured': True,
            'sort_order': 4,
            'children': [
                {
                    'name': 'Cookware',
                    'slug': 'cookware',
                    'description': 'Commercial pots, pans, and cooking vessels',
                    'image_url': 'https://pixabay.com/get/ga08707e2d705b69f9abc3564f002408a64598d01603bc2c4651129f59063ad782edde966c7213a29996d5d21f6d709576c374a11af42b2e10d38412493c9c822_1280.jpg',
                    'sort_order': 1
                },
                {
                    'name': 'Cutlery',
                    'slug': 'cutlery',
                    'description': 'Professional knives and cutting tools',
                    'image_url': 'https://pixabay.com/get/g2aa9607d8edf43e183a793ff4698cc6d3789e788b26f13ff884af19930033534eed27b4125f2e8fb3b7086e3627e278001d92fa8a788423365b04e6982556f95_1280.jpg',
                    'sort_order': 2
                },
                {
                    'name': 'Kitchen Utensils',
                    'slug': 'kitchen-utensils',
                    'description': 'Essential cooking utensils and tools',
                    'image_url': 'https://pixabay.com/get/g54320d69517ebd52081b7aedda02cf6892cd3e60992b880d7251ffc557697dfdc9bf7868f45598d76de264b4268ea7268189ac0054966aeae7e07b44c840b5f1_1280.jpg',
                    'sort_order': 3
                },
                {
                    'name': 'Food Storage',
                    'slug': 'food-storage',
                    'description': 'Containers and storage solutions for food service',
                    'image_url': 'https://pixabay.com/get/gc5197ae6715945ac845dc69c40d191d624a99b683eb0e5ce53dfeed2bd6c13d37d6657c1fbf4f4304087b5c05bb514295e3180bb80d9329b119ce708ec161e32_1280.jpg',
                    'sort_order': 4
                },
                {
                    'name': 'Kitchen Tools',
                    'slug': 'kitchen-tools',
                    'description': 'Specialized tools for food preparation',
                    'image_url': 'https://pixabay.com/get/g17ee3b4bb74fe4a47b80244c5230f7999a3547a4213b8700d4ac98c3bd21378f984c4fb4d9d6a33c617558bd7a027630fbac75aceee3f57ffb24f507455a6672_1280.jpg',
                    'sort_order': 5
                },
                {
                    'name': 'Serving Supplies',
                    'slug': 'serving-supplies',
                    'description': 'Plates, bowls, and serving equipment',
                    'image_url': 'https://pixabay.com/get/g24d123ae4ad6f3f1e7def57f2058664eda498f12f9a6432e3b39ebda62d806fa19cf6c5df4066be1223fd6237540133662d6e489cef79f01f01d6c5dd23db15e_1280.jpg',
                    'sort_order': 6
                }
            ]
        },
        {
            'name': 'Disposables',
            'slug': 'disposables',
            'description': 'Disposable foodservice supplies and packaging',
            'image_url': 'https://pixabay.com/get/gc00468883f7687522738492f7b9167fca5dcb35eba1623167aeba8e2ddf4edaa1d7ed2581acafa6df076bf847511e19c37214339c285106bc1e2b797f76f78d7_1280.jpg',
            'is_featured': False,
            'sort_order': 5
        },
        {
            'name': 'Bar Equipment',
            'slug': 'bar-equipment',
            'description': 'Commercial bar and beverage equipment',
            'image_url': 'https://pixabay.com/get/gc9ff3afa396f9345e1af7a4b675b547642163ffdb3b99b3699d63d9c0b2135055ea7fe917986cfb0f182e3c89658d507c6eb8d31115ad0e524e76893289561f7_1280.jpg',
            'is_featured': False,
            'sort_order': 6
        },
        {
            'name': 'Janitorial Supplies',
            'slug': 'janitorial-supplies',
            'description': 'Cleaning supplies and sanitation equipment',
            'image_url': 'https://pixabay.com/get/ga08707e2d705b69f9abc3564f002408a64598d01603bc2c4651129f59063ad782edde966c7213a29996d5d21f6d709576c374a11af42b2e10d38412493c9c822_1280.jpg',
            'is_featured': False,
            'sort_order': 7
        },
        {
            'name': 'Warewashing',
            'slug': 'warewashing',
            'description': 'Dishwashers and warewashing equipment',
            'image_url': 'https://pixabay.com/get/g2aa9607d8edf43e183a793ff4698cc6d3789e788b26f13ff884af19930033534eed27b4125f2e8fb3b7086e3627e278001d92fa8a788423365b04e6982556f95_1280.jpg',
            'is_featured': False,
            'sort_order': 8
        }
    ]
    
    created_categories = {}
    
    # Create main categories first
    for cat_data in categories_data:
        category = Category(
            name=cat_data['name'],
            slug=cat_data['slug'],
            description=cat_data['description'],
            image_url=cat_data['image_url'],
            is_featured=cat_data['is_featured'],
            sort_order=cat_data['sort_order']
        )
        db.session.add(category)
        db.session.flush()  # Get the ID
        created_categories[cat_data['slug']] = category
        
        # Create subcategories if they exist
        if 'children' in cat_data:
            for child_data in cat_data['children']:
                child_category = Category(
                    name=child_data['name'],
                    slug=child_data['slug'],
                    description=child_data['description'],
                    image_url=child_data['image_url'],
                    parent_id=category.id,
                    sort_order=child_data['sort_order']
                )
                db.session.add(child_category)
                db.session.flush()
                created_categories[child_data['slug']] = child_category
    
    return created_categories

def create_products(categories):
    """Create sample products"""
    
    # Stock photo URLs from the provided list
    stock_photos = [
        'https://pixabay.com/get/gc9ff3afa396f9345e1af7a4b675b547642163ffdb3b99b3699d63d9c0b2135055ea7fe917986cfb0f182e3c89658d507c6eb8d31115ad0e524e76893289561f7_1280.jpg',
        'https://pixabay.com/get/gc00468883f7687522738492f7b9167fca5dcb35eba1623167aeba8e2ddf4edaa1d7ed2581acafa6df076bf847511e19c37214339c285106bc1e2b797f76f78d7_1280.jpg',
        'https://pixabay.com/get/ga08707e2d705b69f9abc3564f002408a64598d01603bc2c4651129f59063ad782edde966c7213a29996d5d21f6d709576c374a11af42b2e10d38412493c9c822_1280.jpg',
        'https://pixabay.com/get/g2aa9607d8edf43e183a793ff4698cc6d3789e788b26f13ff884af19930033534eed27b4125f2e8fb3b7086e3627e278001d92fa8a788423365b04e6982556f95_1280.jpg',
        'https://pixabay.com/get/g54320d69517ebd52081b7aedda02cf6892cd3e60992b880d7251ffc557697dfdc9bf7868f45598d76de264b4268ea7268189ac0054966aeae7e07b44c840b5f1_1280.jpg',
        'https://pixabay.com/get/gc5197ae6715945ac845dc69c40d191d624a99b683eb0e5ce53dfeed2bd6c13d37d6657c1fbf4f4304087b5c05bb514295e3180bb80d9329b119ce708ec161e32_1280.jpg',
        'https://pixabay.com/get/g17ee3b4bb74fe4a47b80244c5230f7999a3547a4213b8700d4ac98c3bd21378f984c4fb4d9d6a33c617558bd7a027630fbac75aceee3f57ffb24f507455a6672_1280.jpg',
        'https://pixabay.com/get/g24d123ae4ad6f3f1e7def57f2058664eda498f12f9a6432e3b39ebda62d806fa19cf6c5df4066be1223fd6237540133662d6e489cef79f01f01d6c5dd23db15e_1280.jpg',
        'https://pixabay.com/get/ga54f5834253bc0697e0b25702993bcee631895bfe5dd943445ab220e28d98c3eaedcf74ddf9a4122c0a872ef93aea20fc06091f245423a81194bc666282dc414_1280.jpg',
        'https://pixabay.com/get/ge16afaee6f473ad149f1fd9e24e366d38ae1037fe123f3c3952e0fc90a35c17dd3093638d90740db766240b6b187cd4d94d1e7c57f168e094faf69416e029bfc_1280.jpg',
        'https://pixabay.com/get/g80f9817735b20dcf583f39537cc16e845bea80ff449d98c5a80aed57cd1713684cf14e3dc4e52883b823c8894ac9f5bd87d1a628aa07f7312ffffbf00eb58df8_1280.jpg',
        'https://pixabay.com/get/geb49094e8c6a65e7eaf77fab0a34f5d0845a1d31874b79db767dc8877db110c5839e5d8008af7150c3d0f99a3809bd6be4beb13712fea2a0f77a3c4558cb14bd_1280.jpg',
        'https://pixabay.com/get/g962218f7395369778de71175e196a7c0ef157f897c72d0a8f0ed0a40b4f773a6c5520b0e154a77870036d09d5677c01e9d5d989389a83cb24d96dbb07eb5e1db_1280.jpg',
        'https://pixabay.com/get/gf2a88f8afd58accab1167ef381d69aba9b83efcd2012c554723868e28552629529fe5cac0c223adf7753e73861339ae7a138550e2550d321f9cc9e8e36ec9a20_1280.jpg',
        'https://pixabay.com/get/g499e5c9350e9bb8a8f95df60ca09214fee7bf731a37d3f47a375e15e5e0e8557f3f782fc8c70f2e764a4b43a456b46f66118f6e7ffe4abb6d8a922e7e89e9ef6_1280.jpg',
        'https://pixabay.com/get/gce0b6e86f3c5767917b1939a38ee34d756891736b90d2fb49d40a9761e148d2f926b84ecdf534dfacab38ea1643d02801857c1398ac6088a23ad2427ee696584_1280.jpg',
        'https://pixabay.com/get/g422c8ed9cf799e1ef03e8e59ca53c98cefb8eab9c43030359274fd83b324b38a39987022d6bc8808db39dee49a4feb1010af659ee9ee0b2598399f8a529189f7_1280.jpg',
        'https://pixabay.com/get/gca97dfdbbf65dd0176181d79ef6817fda54d004890c4b01cdf4e7f38f4cebfdd2751a24d914b4e2c0e8c1ac3dadb0afc860769ea13ebd4ad18772103ca2636fa_1280.jpg',
        'https://pixabay.com/get/g2e78645540c9f0055b030eff0db90268d92d14d9a65d268ee4a9f1fcb5075fa50fded69b955b0e2fd3bfcd095da42235193e3d936eb00521b8ae407b0dde9dc2_1280.jpg',
        'https://pixabay.com/get/g6f138a1e59b35b23730b0e91d7835d65fd8d4c3a703090e63a1576bbeba6d0459e43ff5ddbe4ed87b37aa03326c1c8522d18ebfe1a86d513735da029fa1c2235_1280.jpg',
        'https://pixabay.com/get/gad05af8e2967992efb30dfe8d66c2bd60d504496aae6ef5108b10fac1a4c582c554b7b25cf9b4121a37c17e72c318b641d41aa409a91efd60402292cb46b23a1_1280.jpg',
        'https://pixabay.com/get/gd1454a8140943ebc496331b11e9e3599e19c9498042536926cc0150c2f7da748e45edf8410f00ffd251404f522b219b9de348d5ca68291a5e2dd226b09cc2ff1_1280.jpg',
        'https://pixabay.com/get/gef9b78219a080271116447a27bccfb713c5b191a286935c1d853905e7706c0a290535b73f100008656ff0fefaa585ca6abb1cde13e184bd21a8407e139a5d820_1280.jpg',
        'https://pixabay.com/get/gff5e6fa4dd8634b84a6977f1f433aa8f1f24fd433a92c059a88228d6b796662dc980a210b566bac66f8fd8dc1569c6ded78ada3ad3c76b661d932cb8d21476a9_1280.jpg'
    ]
    
    products_data = [
        # Commercial Ovens
        {
            'name': 'TurboChef NGC Rapid Cook Oven',
            'slug': 'turbochef-ngc-rapid-cook-oven',
            'sku': 'TC-NGC-001',
            'category': 'commercial-ovens',
            'brand': 'TurboChef',
            'model_number': 'NGC',
            'short_description': 'High-speed combination cooking oven with convection, impingement, and microwave technology',
            'description': 'The TurboChef NGC is a revolutionary rapid cook oven that combines three cooking technologies - convection, impingement, and microwave - to cook food up to 12 times faster than conventional ovens while maintaining superior quality. Perfect for high-volume operations.',
            'price': 18500.00,
            'cost': 12500.00,
            'weight': 185.0,
            'dimensions': '25.4" W x 26.4" D x 20.9" H',
            'in_stock': True,
            'is_featured': True,
            'requires_quote': True
        },
        {
            'name': 'Blodgett DFG-100 Gas Convection Oven',
            'slug': 'blodgett-dfg-100-gas-convection-oven',
            'sku': 'BLO-DFG100',
            'category': 'commercial-ovens',
            'brand': 'Blodgett',
            'model_number': 'DFG-100',
            'short_description': 'Single deck gas convection oven with manual controls and two-speed fan',
            'description': 'The Blodgett DFG-100 is a reliable single deck gas convection oven featuring manual controls, two-speed fan motor, and solid state temperature control. Built for durability and consistent performance in commercial kitchens.',
            'price': 4250.00,
            'cost': 2850.00,
            'weight': 450.0,
            'dimensions': '38" W x 32" D x 28" H',
            'in_stock': True,
            'is_featured': False,
            'requires_quote': False
        },
        # Commercial Fryers
        {
            'name': 'Frymaster RE17 Electric Fryer',
            'slug': 'frymaster-re17-electric-fryer',
            'sku': 'FRY-RE17-E',
            'category': 'commercial-fryers',
            'brand': 'Frymaster',
            'model_number': 'RE17',
            'short_description': '17 lb. capacity electric countertop fryer with digital controls',
            'description': 'The Frymaster RE17 electric fryer offers 17 lb. oil capacity in a compact countertop design. Features solid state analog controls, melt cycle, and boil-out mode for easy cleaning.',
            'price': 1850.00,
            'cost': 1250.00,
            'weight': 85.0,
            'dimensions': '15.5" W x 24" D x 16" H',
            'in_stock': True,
            'is_featured': True,
            'requires_quote': False
        },
        {
            'name': 'Pitco SG14S Gas Floor Fryer',
            'slug': 'pitco-sg14s-gas-floor-fryer',
            'sku': 'PIT-SG14S',
            'category': 'commercial-fryers',
            'brand': 'Pitco',
            'model_number': 'SG14S',
            'short_description': '35-40 lb. gas floor fryer with millivolt controls',
            'description': 'Heavy-duty Pitco SG14S gas floor fryer with 35-40 lb. capacity. Features standing pilot ignition, millivolt controls, and stainless steel construction for durability.',
            'price': 2750.00,
            'cost': 1850.00,
            'weight': 195.0,
            'dimensions': '15.5" W x 32.5" D x 50" H',
            'in_stock': True,
            'is_featured': False,
            'requires_quote': False
        },
        # Commercial Refrigeration
        {
            'name': 'True T-72F Three Door Freezer',
            'slug': 'true-t72f-three-door-freezer',
            'sku': 'TRUE-T72F',
            'category': 'reach-in-refrigerators',
            'brand': 'True',
            'model_number': 'T-72F',
            'short_description': '78" three section reach-in freezer with 72 cu. ft. capacity',
            'description': 'The True T-72F is a three section reach-in freezer offering 72 cu. ft. of storage capacity. Features LED lighting, digital temperature display, and energy efficient design.',
            'price': 4850.00,
            'cost': 3250.00,
            'weight': 385.0,
            'dimensions': '78" W x 32" D x 80" H',
            'in_stock': True,
            'is_featured': True,
            'requires_quote': False
        },
        {
            'name': 'Nor-Lake KLB612-C Walk-In Cooler',
            'slug': 'nor-lake-klb612-c-walk-in-cooler',
            'sku': 'NL-KLB612C',
            'category': 'walk-in-coolers',
            'brand': 'Nor-Lake',
            'model_number': 'KLB612-C',
            'short_description': '6\' x 12\' x 7\'7" indoor walk-in cooler with floor',
            'description': 'Nor-Lake KLB612-C walk-in cooler box only. 6\' x 12\' x 7\'7" indoor unit with 26 gauge embossed galvalume interior and exterior. Includes floor.',
            'price': 5250.00,
            'cost': 3500.00,
            'weight': 850.0,
            'dimensions': '6\' W x 12\' L x 7\'7" H',
            'in_stock': False,
            'is_featured': False,
            'requires_quote': True
        },
        # Restaurant Tables
        {
            'name': 'Lancaster Table & Seating 30" x 48" Laminated Rectangular Table',
            'slug': 'lancaster-30x48-laminated-table',
            'sku': 'LTS-3048-LAM',
            'category': 'restaurant-tables',
            'brand': 'Lancaster Table & Seating',
            'model_number': '3048-LAM',
            'short_description': '30" x 48" rectangular table with reversible laminate top',
            'description': 'Durable 30" x 48" rectangular table with reversible laminate top featuring black on one side and mahogany on the other. 1.25" thick top with metal edge banding.',
            'price': 185.00,
            'cost': 125.00,
            'weight': 45.0,
            'dimensions': '30" W x 48" L x 1.25" thick',
            'in_stock': True,
            'is_featured': False,
            'requires_quote': False
        },
        {
            'name': 'Flash Furniture 36" Round Table with Walnut Finish',
            'slug': 'flash-furniture-36-round-walnut-table',
            'sku': 'FF-36RND-WAL',
            'category': 'restaurant-tables',
            'brand': 'Flash Furniture',
            'model_number': '36RND-WAL',
            'short_description': '36" round restaurant table with walnut laminate top',
            'description': '36" round restaurant table top with beautiful walnut laminate finish. 1.125" thick MDF core with 2mm PVC edge banding. Perfect for cafes and restaurants.',
            'price': 165.00,
            'cost': 110.00,
            'weight': 32.0,
            'dimensions': '36" diameter x 1.125" thick',
            'in_stock': True,
            'is_featured': False,
            'requires_quote': False
        },
        # Restaurant Chairs
        {
            'name': 'BFM Seating Lima Metal Chair',
            'slug': 'bfm-lima-metal-chair',
            'sku': 'BFM-LIMA-MT',
            'category': 'restaurant-chairs',
            'brand': 'BFM Seating',
            'model_number': 'LIMA-MT',
            'short_description': 'Industrial style metal chair with distressed finish',
            'description': 'The Lima metal chair features an industrial design with distressed metal finish. Stackable design with comfortable seat and backrest. Perfect for modern restaurants and cafes.',
            'price': 125.00,
            'cost': 85.00,
            'weight': 12.0,
            'dimensions': '18" W x 20" D x 32" H',
            'in_stock': True,
            'is_featured': True,
            'requires_quote': False
        },
        {
            'name': 'Alera Continental Series Perforated Back Stacking Chair',
            'slug': 'alera-continental-perforated-chair',
            'sku': 'ALE-CONT-PERF',
            'category': 'restaurant-chairs',
            'brand': 'Alera',
            'model_number': 'CONT-PERF',
            'short_description': 'Lightweight stacking chair with perforated back design',
            'description': 'Modern stacking chair with perforated back for breathability and style. Powder-coated steel frame with comfortable contoured seat. Stacks up to 8 high.',
            'price': 95.00,
            'cost': 65.00,
            'weight': 9.5,
            'dimensions': '19" W x 21" D x 31" H',
            'in_stock': True,
            'is_featured': False,
            'requires_quote': False
        },
        # Cookware
        {
            'name': 'Vollrath Tribute 3-Ply Stainless Steel Sauce Pan',
            'slug': 'vollrath-tribute-sauce-pan',
            'sku': 'VOL-TRIB-SP8',
            'category': 'cookware',
            'brand': 'Vollrath',
            'model_number': 'TRIB-SP8',
            'short_description': '8 qt. stainless steel sauce pan with aluminum core',
            'description': 'Professional-grade 8 qt. sauce pan with 3-ply construction featuring aluminum core for even heat distribution. Stainless steel interior and exterior with riveted handles.',
            'price': 85.00,
            'cost': 57.00,
            'weight': 4.2,
            'dimensions': '11" diameter x 6" deep',
            'in_stock': True,
            'is_featured': False,
            'requires_quote': False
        },
        {
            'name': 'Calphalon Classic Hard-Anodized Nonstick Fry Pan',
            'slug': 'calphalon-classic-fry-pan',
            'sku': 'CAL-CLA-FP12',
            'category': 'cookware',
            'brand': 'Calphalon',
            'model_number': 'CLA-FP12',
            'short_description': '12" hard-anodized nonstick fry pan for professional kitchens',
            'description': 'Heavy-gauge aluminum construction with hard-anodized exterior and dual-layer nonstick interior. Stay-cool stainless steel handle. Oven safe to 450°F.',
            'price': 65.00,
            'cost': 43.00,
            'weight': 2.8,
            'dimensions': '12" diameter x 2" deep',
            'in_stock': True,
            'is_featured': False,
            'requires_quote': False
        },
        # Professional Cutlery
        {
            'name': 'Victorinox Swiss Army 8" Chef\'s Knife',
            'slug': 'victorinox-8-inch-chefs-knife',
            'sku': 'VIC-8CHF-BLK',
            'category': 'cutlery',
            'brand': 'Victorinox',
            'model_number': '8CHF-BLK',
            'short_description': '8" professional chef\'s knife with fibrox handle',
            'description': 'High carbon stainless steel blade with razor-sharp edge and excellent edge retention. Ergonomic fibrox handle provides secure grip even when wet. NSF certified.',
            'price': 45.00,
            'cost': 30.00,
            'weight': 0.5,
            'dimensions': '8" blade length',
            'in_stock': True,
            'is_featured': True,
            'requires_quote': False
        },
        {
            'name': 'Mercer Genesis 6-Piece Knife Set',
            'slug': 'mercer-genesis-6-piece-knife-set',
            'sku': 'MER-GEN-6PC',
            'category': 'cutlery',
            'brand': 'Mercer',
            'model_number': 'GEN-6PC',
            'short_description': 'Professional 6-piece knife set with storage roll',
            'description': 'Complete 6-piece knife set including 8" chef, 8" bread, 6" boning, 4" paring, 3" trimming knives, and knife roll. High-carbon German steel blades.',
            'price': 125.00,
            'cost': 83.00,
            'weight': 3.2,
            'dimensions': 'Various blade lengths',
            'in_stock': True,
            'is_featured': False,
            'requires_quote': False
        }
    ]
    
    # Create products
    for i, product_data in enumerate(products_data):
        # Get random image from stock photos
        image_url = random.choice(stock_photos)
        
        # Find the category
        category_slug = product_data['category']
        category = categories.get(category_slug)
        
        if not category:
            print(f"Category '{category_slug}' not found for product '{product_data['name']}'")
            continue
        
        product = Product(
            name=product_data['name'],
            slug=product_data['slug'],
            sku=product_data['sku'],
            primary_category_id=category.id,
            brand=product_data.get('brand'),
            model_number=product_data.get('model_number'),
            short_description=product_data['short_description'],
            description=product_data['description'],
            price=product_data['price'],
            cost=product_data.get('cost'),
            image_url=image_url,
            weight=product_data.get('weight'),
            dimensions=product_data.get('dimensions'),
            in_stock=product_data['in_stock'],
            is_featured=product_data['is_featured'],
            requires_quote=product_data['requires_quote']
        )
        
        db.session.add(product)
    
    print(f"Created {len(products_data)} products")

def seed_database():
    """Main function to seed the database"""
    with app.app_context():
        print("Starting database seeding...")
        
        # Create all tables
        db.create_all()
        
        # Clear existing data (optional)
        print("Clearing existing data...")
        db.session.query(Product).delete()
        db.session.query(Category).delete()
        db.session.commit()
        
        # Create categories
        print("Creating categories...")
        categories = create_categories()
        db.session.commit()
        print(f"Created {len(categories)} categories")
        
        # Create products
        print("Creating products...")
        create_products(categories)
        db.session.commit()
        
        print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
