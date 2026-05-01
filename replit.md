# Overview

Professional Restaurant Supply is a Flask-based e-commerce web application designed for selling professional restaurant equipment and supplies. The platform serves restaurants across the Northeast region, offering a comprehensive catalog of commercial kitchen equipment with features like shopping cart functionality, quote requests for bulk orders, user account management, and order processing. The application targets B2B customers in the foodservice industry who need reliable, professional-grade equipment and supplies.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
The application uses server-side rendered templates with Jinja2, leveraging Bootstrap 5 for responsive UI components and styling. The frontend implements a traditional multi-page application (MPA) architecture with progressive enhancement through vanilla JavaScript modules for cart management and search functionality. Static assets are organized into CSS and JavaScript files, with Font Awesome providing iconography and external CDNs serving Bootstrap and other dependencies.

## Backend Architecture
Built on Flask with SQLAlchemy ORM for database operations, the application follows a modular structure separating concerns across different files. The main application factory pattern is used with blueprints for authentication routes. The routing layer handles all HTTP requests, form processing, and template rendering. Flask-WTF provides CSRF protection and form validation with custom form classes for different user interactions.

## Database Design
The application uses SQLAlchemy with a declarative base model approach, supporting multiple database backends through environment configuration. The schema includes core entities for users, products, categories, shopping cart items, orders, and quote requests. A hierarchical category system supports nested product organization. The OAuth table structure is specifically designed for Replit Auth integration with unique constraints for browser session management.

## Authentication System
Authentication is implemented through Flask-Dance OAuth integration with Replit's authentication service. The system uses a custom UserSessionStorage class that manages OAuth tokens tied to both user IDs and browser session keys. Flask-Login handles session management and user state persistence. The authentication blueprint is mounted at `/auth` with decorators providing route-level access control.

## Data Models
The application implements a comprehensive e-commerce data model including:
- User profiles with company information and contact details
- Hierarchical product categories with parent-child relationships
- Product catalog with pricing, inventory, and quote requirements
- Shopping cart with user-specific item storage
- Order processing with shipping information, item details, and comprehensive tracking
- Order status history tracking all state changes with timestamps and actors
- Quote request system for B2B custom pricing

## Order Tracking System
The platform includes comprehensive order tracking capabilities:
- **Timestamp Tracking**: Records order creation, email sent time, first customer view, and last customer view
- **Status History**: Complete audit trail of all status changes with timestamps, who made the change (customer/admin), and optional notes
- **Status Flow**: Pending → Sent → Shipped → Delivered (or Cancelled at any stage before Shipped)
- **Customer Actions**: Customers can decline orders in Pending or Sent status through secure order link
- **Admin Visibility**: Full tracking timeline visible in admin order detail page showing customer engagement

# External Dependencies

## Authentication Services
- **Replit Auth**: Primary OAuth provider for user authentication and session management
- **Flask-Dance**: OAuth client library handling the authentication flow

## Frontend Libraries
- **Bootstrap 5**: UI framework for responsive design and component styling
- **Font Awesome**: Icon library for user interface elements
- **jQuery** (implied by cart.js): DOM manipulation and AJAX functionality

## Backend Services
- **Flask Framework**: Core web application framework
- **SQLAlchemy**: Database ORM and query builder
- **Flask-SQLAlchemy**: Flask extension for SQLAlchemy integration
- **Flask-WTF**: Form handling and CSRF protection
- **WTForms**: Form validation and rendering
- **Flask-Login**: User session management

## Infrastructure
- **Database**: Configurable through DATABASE_URL environment variable (supports PostgreSQL, MySQL, SQLite)
- **Image Storage**: DigitalOcean Spaces (S3-compatible) via boto3. Uploaded product/category images are stored in Spaces and served via public URLs. Falls back to local filesystem if DO credentials are missing. Requires secrets: DO_SPACES_KEY, DO_SPACES_SECRET, DO_SPACES_BUCKET, DO_SPACES_REGION.
- **Session Management**: Flask sessions with configurable secret key
- **Logging**: Python standard library logging with DEBUG level configuration
- **WSGI**: ProxyFix middleware for proper URL generation behind reverse proxies

## AI Features
- **AI Description Generator**: Admin product form has a "Generate with AI" button next to the long description field. Clicking it scrapes restaurantsupply.com (search by product name/SKU/manufacturer/category) and attempts to scrape the manufacturer's official website, then passes the gathered content to OpenAI (gpt-5 via Replit AI Integrations) to synthesize a rich HTML product description that populates the CKEditor field automatically. Route: `POST /admin/products/generate-description`.

## SEO Features
- **Meta Tags**: Product and category pages have unique `<meta name="description">`, canonical URL, Open Graph tags (og:title, og:description, og:image, og:url, og:type, og:site_name), and Twitter Card tags. All other pages inherit site-wide defaults defined via Jinja2 blocks in `base.html`.
- **Product SEO**: Each product page auto-populates all SEO tags from `product.name`, `product.short_description` (stripped of HTML), and `product.thumb_image_url`. Admins can override with `product.meta_title` (max 160 chars) and `product.meta_description` (max 320 chars) via a collapsible "SEO (Optional)" panel in the admin product form.
- **Category SEO**: Same treatment for category pages using `category.name`, `category.description`, and `category.image_url`. Overridable via `category.meta_title` and `category.meta_description` in the admin category form.
- **JSON-LD Structured Data**: Product pages include a Schema.org `Product` schema (name, description, sku, image, brand, offers) and a `BreadcrumbList` schema. Category pages include a `BreadcrumbList` schema reflecting the navigation path.
- **Database columns**: `product.meta_title`, `product.meta_description`, `category.meta_title`, `category.meta_description` (all nullable VARCHAR, added via ALTER TABLE).

## Development Tools
- **Werkzeug**: WSGI utilities and development server
- **Jinja2**: Template engine (included with Flask)
- **OpenAI**: Replit AI Integrations (no separate API key required; billed to Replit credits)
- **Trafilatura**: Web content extraction for AI description generator