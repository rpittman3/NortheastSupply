/**
 * Admin Product Costs Management
 * Handles manual save for product cost and MAP price inputs with search and filtering
 */

class ProductCostManager {
    constructor() {
        this.abortControllers = new Map();
        this.allRows = [];
        this.init();
    }

    init() {
        // Store reference to all product rows for filtering
        this.allRows = Array.from(document.querySelectorAll('.product-row'));
        
        // Find all Apply buttons
        const applyButtons = document.querySelectorAll('.apply-btn');
        applyButtons.forEach(button => {
            const productId = button.getAttribute('data-product-id');
            
            button.addEventListener('click', (e) => {
                this.handleApply(productId);
            });
        });

        // Add Enter key support for inputs
        const allInputs = document.querySelectorAll('.cost-input, .map-input');
        allInputs.forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    const productId = input.getAttribute('data-product-id');
                    this.handleApply(productId);
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
            const priceNaCheckbox = row.querySelector('.price-na-checkbox');
            const isPriceNa = priceNaCheckbox && priceNaCheckbox.checked;
            // Show only if: not filtering OR (no cost AND not price N/A)
            const matchesNoCostFilter = !noCostOnly || (!hasCost && !isPriceNa);
            
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

    async handleApply(productId) {
        // Get the input values
        const costInput = document.querySelector(`.cost-input[data-product-id="${productId}"]`);
        const mapInput = document.querySelector(`.map-input[data-product-id="${productId}"]`);
        const priceNaCheckbox = document.querySelector(`.price-na-checkbox[data-product-id="${productId}"]`);
        
        const costValue = costInput?.value.trim() || '';
        const mapValue = mapInput?.value.trim() || '';
        const priceNaValue = priceNaCheckbox?.checked || false;
        
        // Cancel any existing requests for this product
        const abortKey = `apply-${productId}`;
        if (this.abortControllers.has(abortKey)) {
            this.abortControllers.get(abortKey).abort();
        }
        
        const abortController = new AbortController();
        this.abortControllers.set(abortKey, abortController);
        
        // Update button to show saving state
        this.updateButtonState(productId, 'saving');
        
        try {
            // Save cost, MAP price, and price N/A checkbox
            await this.saveAllValues(productId, costValue, mapValue, priceNaValue, abortController.signal);
            
            // Update button to show success
            this.updateButtonState(productId, 'success');
            
            this.showToast('Product updated successfully', 'success');
            
            // Reset button after 2 seconds
            setTimeout(() => {
                this.updateButtonState(productId, 'idle');
            }, 2000);
            
        } catch (error) {
            if (error.name === 'AbortError') {
                return;
            }
            
            console.error('Error saving:', error);
            this.updateButtonState(productId, 'error');
            this.showToast(error.message, 'error');
            
            // Reset button after 3 seconds
            setTimeout(() => {
                this.updateButtonState(productId, 'idle');
            }, 3000);
        } finally {
            this.abortControllers.delete(abortKey);
        }
    }

    async saveAllValues(productId, costValue, mapValue, priceNaValue, signal) {
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        
        // Prepare cost value
        const cost = costValue === '' ? null : parseFloat(costValue);
        if (cost !== null && (isNaN(cost) || cost < 0)) {
            throw new Error('Cost must be a positive number');
        }
        
        // Prepare MAP value
        const mapPrice = mapValue === '' ? null : parseFloat(mapValue);
        if (mapPrice !== null && (isNaN(mapPrice) || mapPrice < 0)) {
            throw new Error('MAP price must be a positive number');
        }
        
        // Save cost first
        const costFormData = new FormData();
        costFormData.append('cost', cost !== null ? cost.toString() : '');
        
        const costResponse = await fetch(`/admin/products/${productId}/cost`, {
            method: 'PATCH',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: costFormData,
            signal: signal
        });

        const costResult = await costResponse.json();

        if (!costResponse.ok) {
            throw new Error(costResult.error || 'Failed to save cost');
        }

        // Save MAP price
        const mapFormData = new FormData();
        mapFormData.append('map_price', mapPrice !== null ? mapPrice.toString() : '');
        
        const mapResponse = await fetch(`/admin/products/${productId}/map-price`, {
            method: 'PATCH',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: mapFormData,
            signal: signal
        });

        const mapResult = await mapResponse.json();

        if (!mapResponse.ok) {
            throw new Error(mapResult.error || 'Failed to save MAP price');
        }

        // Save Price N/A checkbox
        const priceNaFormData = new FormData();
        priceNaFormData.append('price_not_available', priceNaValue ? 'true' : 'false');
        
        const priceNaResponse = await fetch(`/admin/products/${productId}/price-not-available`, {
            method: 'PATCH',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: priceNaFormData,
            signal: signal
        });

        const priceNaResult = await priceNaResponse.json();

        if (!priceNaResponse.ok) {
            throw new Error(priceNaResult.error || 'Failed to save price not available');
        }

        // Update UI with results
        this.updateCurrentCost(productId, costResult.cost);
        this.updateCurrentPrice(productId, costResult.price);
        this.updateCurrentMapPrice(productId, mapResult.map_price);
    }

    updateButtonState(productId, state) {
        const button = document.querySelector(`.apply-btn[data-product-id="${productId}"]`);
        if (!button) return;

        // Reset button classes
        button.className = 'btn btn-sm apply-btn';
        button.disabled = false;
        
        switch (state) {
            case 'saving':
                button.className = 'btn btn-sm btn-secondary apply-btn';
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Saving...';
                break;
            case 'success':
                button.className = 'btn btn-sm btn-success apply-btn';
                button.disabled = true;
                button.innerHTML = '<i class="fas fa-check"></i> Saved';
                break;
            case 'error':
                button.className = 'btn btn-sm btn-danger apply-btn';
                button.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Error';
                break;
            default: // idle
                button.className = 'btn btn-sm btn-primary apply-btn';
                button.innerHTML = '<i class="fas fa-check"></i> Apply';
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

    updateCurrentMapPrice(productId, mapPrice) {
        const row = document.querySelector(`tr[data-product-id="${productId}"]`);
        if (!row) return;
        
        const mapElement = row.querySelector('.current-map');
        if (mapElement) {
            if (mapPrice !== null && mapPrice !== undefined) {
                mapElement.innerHTML = `$${mapPrice.toFixed(2)}`;
            } else {
                mapElement.innerHTML = '<span class="text-muted">Not set</span>';
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
