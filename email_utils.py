import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

def is_dev_mode():
    """Check if we're in development mode"""
    return os.environ.get('REPL_ID') is not None

def get_recipient_email():
    """Get the appropriate recipient email based on environment"""
    if is_dev_mode():
        dev_email = os.environ.get('DEV_EMAIL')
        logging.info(f"Development mode: Sending email to DEV_EMAIL")
        return dev_email
    else:
        return os.environ.get('RECIPIENT_EMAIL')

def send_order_notification(order, user):
    """Send order notification email to admin"""
    try:
        smtp_host = os.environ.get('SMTP_HOST')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_pass = os.environ.get('SMTP_PASS')
        from_email = os.environ.get('FROM_EMAIL')
        to_email = get_recipient_email()
        
        if not all([smtp_host, smtp_port, smtp_user, smtp_pass, from_email, to_email]):
            logging.error("Missing required email configuration")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'New Order Received - {order.order_number}'
        msg['From'] = from_email
        msg['To'] = to_email
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #0d6efd; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f8f9fa; padding: 20px; }}
                .order-info {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                .order-info h3 {{ margin-top: 0; color: #0d6efd; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #dee2e6; }}
                th {{ background-color: #e9ecef; font-weight: bold; }}
                .total-row {{ font-weight: bold; background-color: #f8f9fa; }}
                .footer {{ text-align: center; padding: 15px; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Order Received</h1>
                    <p>Order #{order.order_number}</p>
                </div>
                
                <div class="content">
                    <div class="order-info">
                        <h3>Order Details</h3>
                        <p><strong>Order Number:</strong> {order.order_number}</p>
                        <p><strong>Order Date:</strong> {order.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                        <p><strong>Status:</strong> {order.status.capitalize()}</p>
                        <p><strong>Customer ID:</strong> {user.id if user else order.user_id}</p>
                        {f"<p><strong>Customer Name:</strong> {user.first_name} {user.last_name}</p>" if user and user.first_name else ""}
                        {f"<p><strong>Company:</strong> {user.company_name}</p>" if user and user.company_name else ""}
                    </div>
                    
                    <div class="order-info">
                        <h3>Shipping Information</h3>
                        <p><strong>{order.shipping_name}</strong></p>
                        {f"<p>{order.shipping_company}</p>" if order.shipping_company else ""}
                        <p>{order.shipping_address}</p>
                        <p>{order.shipping_city}, {order.shipping_state} {order.shipping_zip}</p>
                        <p><strong>Phone:</strong> {order.shipping_phone}</p>
                        {f"<p><strong>Delivery Type:</strong> {order.shipping_option}</p>" if order.shipping_option else ""}
                    </div>
                    
                    <div class="order-info">
                        <h3>Order Items</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Product</th>
                                    <th style="text-align: center;">Qty</th>
                                    <th style="text-align: right;">Price</th>
                                    <th style="text-align: right;">Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join([f'''
                                <tr>
                                    <td>{item.product.name if item.product else "Product Not Found"}<br>
                                        <small style="color: #6c757d;">SKU: {item.product.sku if item.product else "N/A"}</small>
                                    </td>
                                    <td style="text-align: center;">{item.quantity}</td>
                                    <td style="text-align: right;">${item.unit_price:.2f}</td>
                                    <td style="text-align: right;">${item.total_price:.2f}</td>
                                </tr>
                                ''' for item in order.items])}
                            </tbody>
                            <tfoot>
                                <tr>
                                    <td colspan="3" style="text-align: right;"><strong>Subtotal:</strong></td>
                                    <td style="text-align: right;">${order.subtotal:.2f}</td>
                                </tr>
                                <tr>
                                    <td colspan="3" style="text-align: right;"><strong>Tax:</strong></td>
                                    <td style="text-align: right;">{"$%.2f" % order.tax_amount if order.tax_amount > 0 else "TBD"}</td>
                                </tr>
                                <tr>
                                    <td colspan="3" style="text-align: right;"><strong>Shipping:</strong></td>
                                    <td style="text-align: right;">{"$%.2f" % order.shipping_amount if order.shipping_amount > 0 else "TBD"}</td>
                                </tr>
                                <tr class="total-row">
                                    <td colspan="3" style="text-align: right;"><strong>Total:</strong></td>
                                    <td style="text-align: right;"><strong>${order.total_amount:.2f}</strong></td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated notification from Professional Restaurant Supply</p>
                    {"<p style='color: #dc3545;'><strong>DEVELOPMENT MODE - Email sent to DEV_EMAIL</strong></p>" if is_dev_mode() else ""}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Build text body
        customer_name = f"Name: {user.first_name} {user.last_name}" if user and user.first_name else ""
        customer_company = f"Company: {user.company_name}" if user and user.company_name else ""
        shipping_company_line = order.shipping_company if order.shipping_company else ""
        delivery_type = f"Delivery Type: {order.shipping_option}" if order.shipping_option else ""
        
        order_items_text = "\n".join([
            f"{item.product.name if item.product else 'Product Not Found'} (SKU: {item.product.sku if item.product else 'N/A'}) - Qty: {item.quantity} x ${item.unit_price:.2f} = ${item.total_price:.2f}"
            for item in order.items
        ])
        
        tax_display = f"${order.tax_amount:.2f}" if order.tax_amount > 0 else "TBD"
        shipping_display = f"${order.shipping_amount:.2f}" if order.shipping_amount > 0 else "TBD"
        dev_mode_notice = "DEVELOPMENT MODE - Email sent to DEV_EMAIL" if is_dev_mode() else ""
        
        text_body = f"""NEW ORDER RECEIVED

Order Number: {order.order_number}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Status: {order.status.capitalize()}

CUSTOMER INFORMATION
Customer ID: {user.id if user else order.user_id}
{customer_name}
{customer_company}

SHIPPING INFORMATION
{order.shipping_name}
{shipping_company_line}
{order.shipping_address}
{order.shipping_city}, {order.shipping_state} {order.shipping_zip}
Phone: {order.shipping_phone}
{delivery_type}

ORDER ITEMS
{order_items_text}

Subtotal: ${order.subtotal:.2f}
Tax: {tax_display}
Shipping: {shipping_display}
TOTAL: ${order.total_amount:.2f}

---
This is an automated notification from Professional Restaurant Supply
{dev_mode_notice}
"""
        
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Port 465 requires SSL, port 587 requires STARTTLS
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Order notification email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send order notification email: {str(e)}")
        return False

def send_customer_order_email(order, user, order_url, base_url):
    """Send order update email to customer with order details and payment link"""
    try:
        smtp_host = os.environ.get('SMTP_HOST')
        smtp_port = int(os.environ.get('SMTP_PORT', 587))
        smtp_user = os.environ.get('SMTP_USER')
        smtp_pass = os.environ.get('SMTP_PASS')
        from_email = os.environ.get('FROM_EMAIL')
        
        # In dev mode, send to DEV_EMAIL, otherwise send to customer's email
        if is_dev_mode():
            to_email = os.environ.get('DEV_EMAIL')
            logging.info(f"Development mode: Sending customer email to DEV_EMAIL instead of customer")
        else:
            to_email = user.email if user and user.email else None
            
        if not to_email:
            logging.error("No customer email address available")
            return False
        
        if not all([smtp_host, smtp_port, smtp_user, smtp_pass, from_email]):
            logging.error("Missing required email configuration")
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f'Order Update - {order.order_number}'
        msg['From'] = from_email
        msg['To'] = to_email
        
        # Build payment section
        payment_section_html = ""
        payment_section_text = ""
        if order.payment_link:
            payment_section_html = f"""
            <div class="order-info" style="background-color: #d1e7dd; border-left: 4px solid #0d6efd;">
                <h3 style="color: #0d6efd;">Complete Your Payment</h3>
                <p>Your order total is <strong style="font-size: 18px;">${order.total_amount:.2f}</strong></p>
                <p style="margin: 20px 0;">
                    <a href="{order.payment_link}" style="display: inline-block; background-color: #0d6efd; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Proceed to Secure Payment
                    </a>
                </p>
                <p style="font-size: 12px; color: #6c757d;">Click the button above or copy this link: {order.payment_link}</p>
            </div>
            """
            payment_section_text = f"""
PAYMENT INFORMATION
Your order total is ${order.total_amount:.2f}
Payment Link: {order.payment_link}
"""
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background-color: #0d6efd; color: white; padding: 20px; text-align: center; }}
                .content {{ background-color: #f8f9fa; padding: 20px; }}
                .order-info {{ background-color: white; padding: 15px; margin: 15px 0; border-radius: 5px; }}
                .order-info h3 {{ margin-top: 0; color: #0d6efd; }}
                table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
                th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #dee2e6; }}
                th {{ background-color: #e9ecef; font-weight: bold; }}
                .total-row {{ font-weight: bold; background-color: #f8f9fa; }}
                .footer {{ text-align: center; padding: 15px; color: #6c757d; font-size: 12px; }}
                .status-badge {{ display: inline-block; padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
                .status-pending {{ background-color: #ffc107; color: #000; }}
                .status-processing {{ background-color: #0dcaf0; color: #000; }}
                .status-shipped {{ background-color: #0d6efd; color: white; }}
                .status-delivered {{ background-color: #198754; color: white; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Order Update</h1>
                    <p>Professional Restaurant Supply</p>
                </div>
                
                <div class="content">
                    <div class="order-info">
                        <h3>Order #{order.order_number}</h3>
                        <p><strong>Order Date:</strong> {order.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                        <p><strong>Status:</strong> <span class="status-badge status-{order.status}">{order.status.upper()}</span></p>
                    </div>
                    
                    <div class="order-info">
                        <h3>View Your Order</h3>
                        <p>Click the link below to view your complete order details:</p>
                        <p style="margin: 15px 0;">
                            <a href="{order_url}" style="display: inline-block; background-color: #6c757d; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                                View Order Details
                            </a>
                        </p>
                        <p style="font-size: 12px; color: #6c757d;">Or copy this link: {order_url}</p>
                    </div>
                    
                    {payment_section_html}
                    
                    <div class="order-info">
                        <h3>Order Items</h3>
                        <table>
                            <thead>
                                <tr>
                                    <th>Product</th>
                                    <th style="text-align: center;">Qty</th>
                                    <th style="text-align: right;">Price</th>
                                    <th style="text-align: right;">Total</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"".join([f'''
                                <tr>
                                    <td>{item.product.name if item.product else "Product Not Found"}<br>
                                        <small style="color: #6c757d;">SKU: {item.product.sku if item.product else "N/A"}</small>
                                    </td>
                                    <td style="text-align: center;">{item.quantity}</td>
                                    <td style="text-align: right;">${item.unit_price:.2f}</td>
                                    <td style="text-align: right;">${item.total_price:.2f}</td>
                                </tr>
                                ''' for item in order.items])}
                            </tbody>
                            <tfoot>
                                <tr>
                                    <td colspan="3" style="text-align: right;"><strong>Subtotal:</strong></td>
                                    <td style="text-align: right;">${order.subtotal:.2f}</td>
                                </tr>
                                <tr>
                                    <td colspan="3" style="text-align: right;"><strong>Tax:</strong></td>
                                    <td style="text-align: right;">{"$%.2f" % order.tax_amount if order.tax_amount > 0 else "TBD"}</td>
                                </tr>
                                <tr>
                                    <td colspan="3" style="text-align: right;"><strong>Shipping:</strong></td>
                                    <td style="text-align: right;">{"$%.2f" % order.shipping_amount if order.shipping_amount > 0 else "TBD"}</td>
                                </tr>
                                <tr class="total-row">
                                    <td colspan="3" style="text-align: right;"><strong>Total:</strong></td>
                                    <td style="text-align: right;"><strong>${order.total_amount:.2f}</strong></td>
                                </tr>
                            </tfoot>
                        </table>
                    </div>
                    
                    <div class="order-info">
                        <h3>Shipping Address</h3>
                        <p><strong>{order.shipping_name}</strong></p>
                        {f"<p>{order.shipping_company}</p>" if order.shipping_company else ""}
                        <p>{order.shipping_address}</p>
                        <p>{order.shipping_city}, {order.shipping_state} {order.shipping_zip}</p>
                        <p><strong>Phone:</strong> {order.shipping_phone}</p>
                        {f"<p><strong>Delivery Type:</strong> {order.shipping_option}</p>" if order.shipping_option else ""}
                    </div>
                </div>
                
                <div class="footer">
                    <p>Thank you for your business!</p>
                    <p>Professional Restaurant Supply</p>
                    {"<p style='color: #dc3545;'><strong>DEVELOPMENT MODE - Email sent to DEV_EMAIL instead of customer</strong></p>" if is_dev_mode() else ""}
                </div>
            </div>
        </body>
        </html>
        """
        
        # Build text body
        order_items_text = "\n".join([
            f"{item.product.name if item.product else 'Product Not Found'} (SKU: {item.product.sku if item.product else 'N/A'}) - Qty: {item.quantity} x ${item.unit_price:.2f} = ${item.total_price:.2f}"
            for item in order.items
        ])
        
        tax_display = f"${order.tax_amount:.2f}" if order.tax_amount > 0 else "TBD"
        shipping_display = f"${order.shipping_amount:.2f}" if order.shipping_amount > 0 else "TBD"
        shipping_company_line = order.shipping_company if order.shipping_company else ""
        delivery_type = f"Delivery Type: {order.shipping_option}" if order.shipping_option else ""
        dev_mode_notice = "DEVELOPMENT MODE - Email sent to DEV_EMAIL instead of customer" if is_dev_mode() else ""
        
        text_body = f"""ORDER UPDATE - Professional Restaurant Supply

Order Number: {order.order_number}
Order Date: {order.created_at.strftime('%B %d, %Y at %I:%M %p')}
Status: {order.status.upper()}

VIEW YOUR ORDER
You can view your complete order details at:
{order_url}

{payment_section_text}
ORDER ITEMS
{order_items_text}

Subtotal: ${order.subtotal:.2f}
Tax: {tax_display}
Shipping: {shipping_display}
TOTAL: ${order.total_amount:.2f}

SHIPPING ADDRESS
{order.shipping_name}
{shipping_company_line}
{order.shipping_address}
{order.shipping_city}, {order.shipping_state} {order.shipping_zip}
Phone: {order.shipping_phone}
{delivery_type}

---
Thank you for your business!
Professional Restaurant Supply
{dev_mode_notice}
"""
        
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        # Port 465 requires SSL, port 587 requires STARTTLS
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port)
            server.starttls()
        
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        
        logging.info(f"Customer order email sent successfully to {to_email}")
        return True
        
    except Exception as e:
        logging.error(f"Failed to send customer order email: {str(e)}")
        return False
