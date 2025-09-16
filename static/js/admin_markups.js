/**
 * Admin Markups Management
 * Handles autosave functionality for category markup inputs
 */

class MarkupManager {
    constructor() {
        this.debounceTimers = new Map();
        this.abortControllers = new Map();
        this.init();
    }

    init() {
        // Find all markup input fields
        const inputs = document.querySelectorAll('.markup-input');
        
        inputs.forEach(input => {
            const categoryId = input.getAttribute('data-category-id');
            
            // Add event listeners
            input.addEventListener('input', (e) => {
                this.handleInputChange(categoryId, e.target.value);
            });
            
            input.addEventListener('blur', (e) => {
                this.handleBlur(categoryId, e.target.value);
            });
            
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    e.target.blur(); // Trigger blur event for immediate save
                }
            });
        });
    }

    handleInputChange(categoryId, value) {
        // Clear existing timer for this category
        if (this.debounceTimers.has(categoryId)) {
            clearTimeout(this.debounceTimers.get(categoryId));
        }
        
        // Set new debounced timer (700ms)
        const timer = setTimeout(() => {
            this.saveMarkup(categoryId, value);
        }, 700);
        
        this.debounceTimers.set(categoryId, timer);
    }

    handleBlur(categoryId, value) {
        // Clear any pending debounced save
        if (this.debounceTimers.has(categoryId)) {
            clearTimeout(this.debounceTimers.get(categoryId));
            this.debounceTimers.delete(categoryId);
        }
        
        // Save immediately on blur
        this.saveMarkup(categoryId, value);
    }

    async saveMarkup(categoryId, value) {
        // Cancel any existing request for this category
        if (this.abortControllers.has(categoryId)) {
            this.abortControllers.get(categoryId).abort();
        }
        
        const abortController = new AbortController();
        this.abortControllers.set(categoryId, abortController);
        
        // Update UI to show saving state
        this.updateStatus(categoryId, 'saving');
        
        try {
            // Prepare data
            const markup = value.trim() === '' ? null : parseFloat(value);
            
            // Validate client-side
            if (markup !== null && (isNaN(markup) || markup < 0 || markup > 300)) {
                throw new Error('Markup must be between 0% and 300%');
            }
            
            const response = await fetch(`/admin/categories/${categoryId}/markup`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ markup: markup }),
                signal: abortController.signal
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.error || 'Failed to save markup');
            }

            // Check if response value matches current input value (avoid race conditions)
            const currentInput = document.querySelector(`input[data-category-id="${categoryId}"]`);
            const currentValue = currentInput.value.trim() === '' ? null : parseFloat(currentInput.value);
            
            if (result.markup !== currentValue) {
                // Response is outdated, ignore it
                return;
            }

            // Update UI with success
            this.updateStatus(categoryId, 'success');
            this.updateCurrentMarkup(categoryId, result.markup);
            
            // Show updated count if any products were affected
            if (result.updated_count > 0) {
                this.showToast(`Updated ${result.updated_count} product prices`, 'success');
            }
            
            // Clear success status after 2 seconds
            setTimeout(() => {
                this.updateStatus(categoryId, 'idle');
            }, 2000);

        } catch (error) {
            // Only show error if request wasn't aborted
            if (!abortController.signal.aborted) {
                this.updateStatus(categoryId, 'error', error.message);
                this.showToast(error.message, 'error');
                
                // Clear error status after 5 seconds
                setTimeout(() => {
                    this.updateStatus(categoryId, 'idle');
                }, 5000);
            }
        } finally {
            // Clean up
            this.abortControllers.delete(categoryId);
        }
    }

    updateStatus(categoryId, status, message = '') {
        const indicator = document.querySelector(`.status-indicator[data-category-id="${categoryId}"] i`);
        if (!indicator) return;

        // Remove existing classes
        indicator.className = 'fas';
        
        switch (status) {
            case 'saving':
                indicator.className += ' fa-spinner fa-spin text-primary';
                indicator.title = 'Saving...';
                break;
            case 'success':
                indicator.className += ' fa-check-circle text-success';
                indicator.title = 'Saved successfully';
                break;
            case 'error':
                indicator.className += ' fa-exclamation-circle text-danger';
                indicator.title = message || 'Error saving';
                break;
            case 'idle':
            default:
                indicator.className += ' fa-circle text-muted';
                indicator.title = 'Ready';
                break;
        }
    }

    updateCurrentMarkup(categoryId, markup) {
        const row = document.querySelector(`tr[data-category-id="${categoryId}"]`);
        if (!row) return;
        
        const currentMarkupSpan = row.querySelector('.current-markup');
        if (!currentMarkupSpan) return;
        
        if (markup !== null) {
            currentMarkupSpan.innerHTML = `${markup.toFixed(2)}%`;
        } else {
            currentMarkupSpan.innerHTML = '<span class="text-muted">Not set</span>';
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
        
        // Add to page
        document.body.appendChild(toast);
        
        // Auto remove after 4 seconds
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 4000);
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    new MarkupManager();
});