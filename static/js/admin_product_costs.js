/**
 * Admin Product Costs Management
 * Handles autosave functionality for product cost inputs with search and filtering
 */

class ProductCostManager {
    constructor() {
        this.debounceTimers = new Map();
        this.abortControllers = new Map();
        this.allRows = [];
        this.init();
    }

    init() {
        // Store reference to all product rows for filtering
        this.allRows = Array.from(document.querySelectorAll('.product-row'));
        
        // Find all cost input fields
        const inputs = document.querySelectorAll('.cost-input');
        
        inputs.forEach(input => {
            const productId = input.getAttribute('data-product-id');
            
            // Add event listeners
            input.addEventListener('input', (e) => {
                this.handleInputChange(productId, e.target.value);
            });
            
            input.addEventListener('blur', (e) => {
                this.handleBlur(productId, e.target.value);
            });
            
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.target.blur(); // Trigger blur event for immediate save
                }
            });
        });

        // Setup search functionality
        this.setupSearch();
        
        // Setup category filter
        this.setupCategoryFilter();
        
        // Setup no cost filter
        this.setupNoCostFilter();
    }

    setupSearch() {
        const searchInput = document.getElementById('productSearch');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterProducts();
            });
        }
    }

    setupCategoryFilter() {
        const categoryFilter = document.getElementById('categoryFilter');
        if (categoryFilter) {
            categoryFilter.addEventListener('change', (e) => {
                this.filterProducts();
            });
        }
    }

    setupNoCostFilter() {
        const noCostFilter = document.getElementById('noCostFilter');
        if (noCostFilter) {
            noCostFilter.addEventListener('change', (e) => {
                this.filterProducts();
            });
        }
    }

    filterProducts() {
        const searchTerm = document.getElementById('productSearch')?.value.toLowerCase() || '';
        const selectedCategory = document.getElementById('categoryFilter')?.value || '';
        const noCostOnly = document.getElementById('noCostFilter')?.checked || false;
        
        let visibleCount = 0;

        this.allRows.forEach(row => {
            const productName = row.querySelector('strong').textContent.toLowerCase();
            const categoryId = row.getAttribute('data-category-id');
            const categoryName = row.querySelector('.category-name').textContent.toLowerCase();
            
            // Check search match
            const matchesSearch = productName.includes(searchTerm) || categoryName.includes(searchTerm);
            
            // Check category filter
            const matchesCategory = !selectedCategory || categoryId === selectedCategory;
            
            // Check no cost filter
            const currentCostElement = row.querySelector('.current-cost');
            const hasCost = currentCostElement && !currentCostElement.textContent.includes('Not set');
            const matchesNoCostFilter = !noCostOnly || !hasCost;
            
            if (matchesSearch && matchesCategory && matchesNoCostFilter) {
                row.style.display = '';
                visibleCount++;
            } else {
                row.style.display = 'none';
            }
        });

        // Update visible count
        const countElement = document.getElementById('visibleCount');
        if (countElement) {
            countElement.textContent = visibleCount;
        }
    }

    handleInputChange(productId, value) {
        // Clear existing timer for this product
        if (this.debounceTimers.has(productId)) {
            clearTimeout(this.debounceTimers.get(productId));
        }
        
        // Set new debounced timer (700ms)
        const timer = setTimeout(() => {
            this.saveCost(productId, value);
        }, 700);
        
        this.debounceTimers.set(productId, timer);
    }

    handleBlur(productId, value) {
        // Clear any pending debounced save
        if (this.debounceTimers.has(productId)) {
            clearTimeout(this.debounceTimers.get(productId));
            this.debounceTimers.delete(productId);
        }
        
        // Save immediately on blur
        this.saveCost(productId, value);
    }

    async saveCost(productId, value) {
        // Cancel any existing request for this product
        if (this.abortControllers.has(productId)) {
            this.abortControllers.get(productId).abort();
        }
        
        const abortController = new AbortController();
        this.abortControllers.set(productId, abortController);
        
        // Update UI to show saving state
        this.updateStatus(productId, 'saving');
        
        try {
            // Prepare data
            const cost = value.trim() === '' ? null : parseFloat(value);
            
            // Validate client-side
            if (cost !== null && (isNaN(cost) || cost < 0)) {
                throw new Error('Cost must be a positive number');
            }
            
            // Get CSRF token
            const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
            
            // Prepare form data (send empty string to clear cost)
            const formData = new FormData();
            formData.append('cost', cost !== null ? cost.toString() : '');
            
            const response = await fetch(`/admin/products/${productId}/cost`, {
                method: 'PATCH',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: formData,
                signal: abortController.signal
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Failed to save cost');
            }

            // Check if response value matches current input value (avoid race conditions)
            const currentInput = document.querySelector(`input[data-product-id="${productId}"]`);
            const currentValue = currentInput.value.trim() === '' ? null : parseFloat(currentInput.value);
            
            if (result.cost !== currentValue) {
                // Response is outdated, reset status and ignore it
                this.updateStatus(productId, 'idle');
                return;
            }

            // Update UI with success
            this.updateStatus(productId, 'success');
            this.updateCurrentCost(productId, result.cost);
            this.updateCurrentPrice(productId, result.price);
            
            this.showToast('Product cost updated successfully', 'success');
            
            // Clear success status after 2 seconds
            setTimeout(() => {
                this.updateStatus(productId, 'idle');
            }, 2000);

        } catch (error) {
            if (error.name === 'AbortError') {
                // Request was cancelled, ignore
                return;
            }
            
            console.error('Error saving cost:', error);
            this.updateStatus(productId, 'error');
            this.showToast(error.message, 'error');
            
            // Clear error status after 3 seconds
            setTimeout(() => {
                this.updateStatus(productId, 'idle');
            }, 3000);
        } finally {
            // Clean up abort controller
            this.abortControllers.delete(productId);
        }
    }

    updateStatus(productId, status) {
        const statusElement = document.querySelector(`.status-indicator[data-product-id="${productId}"] i`);
        if (!statusElement) return;

        // Remove all status classes
        statusElement.className = 'fas fa-circle';
        
        switch (status) {
            case 'saving':
                statusElement.className = 'fas fa-spinner fa-spin text-primary';
                statusElement.title = 'Saving...';
                break;
            case 'success':
                statusElement.className = 'fas fa-check text-success';
                statusElement.title = 'Saved';
                break;
            case 'error':
                statusElement.className = 'fas fa-exclamation-triangle text-danger';
                statusElement.title = 'Error saving';
                break;
            default: // idle
                statusElement.className = 'fas fa-circle text-muted';
                statusElement.title = 'Ready';
                break;
        }
    }

    updateCurrentCost(productId, cost) {
        const row = document.querySelector(`tr[data-product-id="${productId}"]`);
        if (!row) return;
        
        const costElement = row.querySelector('.current-cost');
        if (costElement) {
            if (cost !== null && cost !== undefined) {
                costElement.innerHTML = `$${cost.toFixed(2)}`;
            } else {
                costElement.innerHTML = '<span class="text-muted">Not set</span>';
            }
        }
        
        // Re-apply filters after cost update (in case "no cost" filter is active)
        this.filterProducts();
    }

    updateCurrentPrice(productId, price) {
        const row = document.querySelector(`tr[data-product-id="${productId}"]`);
        if (!row) return;
        
        const priceElement = row.querySelector('.current-price');
        if (priceElement) {
            if (price !== null && price !== undefined) {
                priceElement.innerHTML = `$${price.toFixed(2)}`;
            } else {
                priceElement.innerHTML = '<span class="text-muted">Not set</span>';
            }
        }
    }

    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `alert alert-${type === 'error' ? 'danger' : 'success'} alert-dismissible fade show position-fixed`;
        toast.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
        toast.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(toast);
        
        // Auto remove after 3 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 3000);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new ProductCostManager();
});