// Cart functionality for Professional Restaurant Supply

class Cart {
    constructor() {
        this.init();
        this.updateCartCount();
    }

    init() {
        // Bind event listeners
        this.bindAddToCartButtons();
        this.bindQuantityUpdates();
        this.bindRemoveButtons();
        this.bindCheckoutValidation();
    }

    bindAddToCartButtons() {
        document.addEventListener('click', (e) => {
            if (e.target.matches('.add-to-cart-btn') || e.target.closest('.add-to-cart-btn')) {
                e.preventDefault();
                const button = e.target.matches('.add-to-cart-btn') ? e.target : e.target.closest('.add-to-cart-btn');
                this.addToCart(button);
            }
        });
    }

    bindQuantityUpdates() {
        document.addEventListener('change', (e) => {
            if (e.target.matches('input[name="quantity"]') && e.target.closest('.cart-item')) {
                this.updateQuantity(e.target);
            }
        });
    }

    bindRemoveButtons() {
        document.addEventListener('click', (e) => {
            if (e.target.matches('.remove-item-btn') || e.target.closest('.remove-item-btn')) {
                e.preventDefault();
                const button = e.target.matches('.remove-item-btn') ? e.target : e.target.closest('.remove-item-btn');
                this.removeItem(button);
            }
        });
    }

    bindCheckoutValidation() {
        const checkoutForm = document.querySelector('#checkout-form');
        if (checkoutForm) {
            checkoutForm.addEventListener('submit', (e) => {
                this.validateCheckout(e);
            });
        }
    }

    addToCart(button) {
        const form = button.closest('form');
        const productId = form.querySelector('input[name="product_id"]').value;
        const quantity = form.querySelector('input[name="quantity"]')?.value || 1;
        
        // Show loading state
        const originalText = button.innerHTML;
        button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Adding...';
        button.disabled = true;

        // Submit form via fetch for better UX
        const formData = new FormData(form);
        
        fetch(form.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                // Update cart count
                this.updateCartCount();
                
                // Show success feedback
                button.innerHTML = '<i class="fas fa-check"></i> Added!';
                button.classList.remove('btn-primary');
                button.classList.add('btn-success');
                
                // Show toast notification
                this.showToast('Product added to cart!', 'success');
                
                // Reset button after 2 seconds
                setTimeout(() => {
                    button.innerHTML = originalText;
                    button.classList.remove('btn-success');
                    button.classList.add('btn-primary');
                    button.disabled = false;
                }, 2000);
            } else {
                throw new Error('Failed to add to cart');
            }
        })
        .catch(error => {
            console.error('Error adding to cart:', error);
            button.innerHTML = originalText;
            button.disabled = false;
            this.showToast('Error adding to cart. Please try again.', 'error');
        });
    }

    updateQuantity(input) {
        const quantity = parseInt(input.value);
        if (quantity < 1) {
            input.value = 1;
            return;
        }

        const form = input.closest('form');
        const itemRow = input.closest('.cart-item');
        
        // Show loading state
        itemRow.classList.add('loading');

        // Auto-submit the form
        const formData = new FormData(form);
        
        fetch(form.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                // Update the total for this item
                this.updateItemTotal(itemRow, quantity);
                this.updateCartTotals();
                this.updateCartCount();
                this.showToast('Cart updated!', 'success');
            } else {
                throw new Error('Failed to update cart');
            }
        })
        .catch(error => {
            console.error('Error updating cart:', error);
            this.showToast('Error updating cart. Please refresh and try again.', 'error');
        })
        .finally(() => {
            itemRow.classList.remove('loading');
        });
    }

    removeItem(button) {
        if (!confirm('Remove this item from your cart?')) {
            return;
        }

        const form = button.closest('form');
        const itemRow = button.closest('.cart-item');
        
        // Show loading state
        itemRow.classList.add('loading');

        const formData = new FormData(form);
        
        fetch(form.action, {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (response.ok) {
                // Animate item removal
                itemRow.style.transition = 'all 0.3s ease';
                itemRow.style.opacity = '0';
                itemRow.style.transform = 'translateX(-100%)';
                
                setTimeout(() => {
                    itemRow.remove();
                    this.updateCartTotals();
                    this.updateCartCount();
                    this.checkEmptyCart();
                }, 300);
                
                this.showToast('Item removed from cart', 'info');
            } else {
                throw new Error('Failed to remove item');
            }
        })
        .catch(error => {
            console.error('Error removing item:', error);
            itemRow.classList.remove('loading');
            this.showToast('Error removing item. Please try again.', 'error');
        });
    }

    updateItemTotal(itemRow, quantity) {
        const priceElement = itemRow.querySelector('.item-price');
        const totalElement = itemRow.querySelector('.item-total');
        
        if (priceElement && totalElement) {
            const price = parseFloat(priceElement.textContent.replace('$', ''));
            const total = price * quantity;
            totalElement.textContent = `$${total.toFixed(2)}`;
        }
    }

    updateCartTotals() {
        const cartItems = document.querySelectorAll('.cart-item');
        let subtotal = 0;
        
        cartItems.forEach(item => {
            const totalElement = item.querySelector('.item-total');
            if (totalElement) {
                const total = parseFloat(totalElement.textContent.replace('$', ''));
                subtotal += total;
            }
        });
        
        // Update subtotal
        const subtotalElement = document.querySelector('.cart-subtotal');
        if (subtotalElement) {
            subtotalElement.textContent = `$${subtotal.toFixed(2)}`;
        }
        
        // Update tax
        const tax = subtotal * 0.08;
        const taxElement = document.querySelector('.cart-tax');
        if (taxElement) {
            taxElement.textContent = `$${tax.toFixed(2)}`;
        }
        
        // Update shipping
        const shipping = subtotal >= 500 ? 0 : 25.00;
        const shippingElement = document.querySelector('.cart-shipping');
        if (shippingElement) {
            if (shipping === 0) {
                shippingElement.innerHTML = '<span class="text-success">FREE</span>';
            } else {
                shippingElement.textContent = `$${shipping.toFixed(2)}`;
            }
        }
        
        // Update total
        const total = subtotal + tax + shipping;
        const totalElement = document.querySelector('.cart-total');
        if (totalElement) {
            totalElement.textContent = `$${total.toFixed(2)}`;
        }
        
        // Update free shipping message
        const freeShippingMessage = document.querySelector('.free-shipping-message');
        if (freeShippingMessage && subtotal < 500) {
            const remaining = 500 - subtotal;
            freeShippingMessage.textContent = `Add $${remaining.toFixed(2)} more for free shipping!`;
        } else if (freeShippingMessage) {
            freeShippingMessage.style.display = 'none';
        }
    }

    async updateCartCount() {
        try {
            const response = await fetch('/get_cart_count');
            const data = await response.json();
            const cartBadges = document.querySelectorAll('.cart-count, .badge');
            
            cartBadges.forEach(badge => {
                if (badge.classList.contains('cart-count') || badge.closest('.nav-link')?.href?.includes('/cart')) {
                    badge.textContent = data.count;
                    
                    // Add animation for count changes
                    badge.classList.add('animate__animated', 'animate__pulse');
                    setTimeout(() => {
                        badge.classList.remove('animate__animated', 'animate__pulse');
                    }, 600);
                }
            });
        } catch (error) {
            console.error('Error updating cart count:', error);
        }
    }

    checkEmptyCart() {
        const cartItems = document.querySelectorAll('.cart-item');
        if (cartItems.length === 0) {
            const cartContainer = document.querySelector('.cart-items-container');
            if (cartContainer) {
                cartContainer.innerHTML = `
                    <div class="text-center py-5">
                        <i class="fas fa-shopping-cart fa-3x text-muted mb-3"></i>
                        <h3>Your cart is empty</h3>
                        <p class="text-muted mb-4">Add some items to get started!</p>
                        <a href="/" class="btn btn-primary btn-lg">
                            <i class="fas fa-store"></i> Start Shopping
                        </a>
                    </div>
                `;
            }
        }
    }

    validateCheckout(event) {
        const form = event.target;
        const requiredFields = form.querySelectorAll('input[required], select[required]');
        let isValid = true;
        
        requiredFields.forEach(field => {
            if (!field.value.trim()) {
                field.classList.add('is-invalid');
                isValid = false;
            } else {
                field.classList.remove('is-invalid');
            }
        });
        
        // Validate email format
        const emailField = form.querySelector('input[type="email"]');
        if (emailField && emailField.value) {
            const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailRegex.test(emailField.value)) {
                emailField.classList.add('is-invalid');
                isValid = false;
            }
        }
        
        // Validate phone format
        const phoneField = form.querySelector('input[name*="phone"]');
        if (phoneField && phoneField.value) {
            const phoneRegex = /^\(?([0-9]{3})\)?[-. ]?([0-9]{3})[-. ]?([0-9]{4})$/;
            if (!phoneRegex.test(phoneField.value)) {
                phoneField.classList.add('is-invalid');
                isValid = false;
            }
        }
        
        if (!isValid) {
            event.preventDefault();
            this.showToast('Please fill in all required fields correctly.', 'error');
            
            // Scroll to first invalid field
            const firstInvalid = form.querySelector('.is-invalid');
            if (firstInvalid) {
                firstInvalid.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstInvalid.focus();
            }
        }
    }

    showToast(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1060';
            document.body.appendChild(toastContainer);
        }
        
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : 'info-circle'} me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        toastContainer.appendChild(toast);
        
        // Initialize and show toast
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }
}

// Initialize cart functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.cart = new Cart();
});

// Expose cart methods globally for inline event handlers
window.addToCart = function(productId, quantity = 1) {
    if (window.cart) {
        const form = document.createElement('form');
        form.innerHTML = `
            <input type="hidden" name="product_id" value="${productId}">
            <input type="hidden" name="quantity" value="${quantity}">
        `;
        form.action = '/add_to_cart';
        
        const button = document.createElement('button');
        button.className = 'add-to-cart-btn';
        form.appendChild(button);
        
        window.cart.addToCart(button);
    }
};
