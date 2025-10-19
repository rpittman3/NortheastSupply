// Search functionality for Professional Restaurant Supply

class Search {
    constructor() {
        this.init();
    }

    init() {
        this.bindSearchForm();
        this.bindSearchInput();
        this.bindFilterButtons();
        this.setupSearchHistory();
    }

    bindSearchForm() {
        const searchForms = document.querySelectorAll('form[action*="search"]');
        searchForms.forEach(form => {
            form.addEventListener('submit', (e) => {
                this.handleSearch(e);
            });
        });
    }

    bindSearchInput() {
        const searchInputs = document.querySelectorAll('input[name="q"]');
        searchInputs.forEach(input => {
            input.addEventListener('input', (e) => {
                this.handleSearchInput(e);
            });

            input.addEventListener('keydown', (e) => {
                this.handleKeyDown(e);
            });

            input.addEventListener('focus', (e) => {
                this.showSuggestions(e.target);
            });

            input.addEventListener('blur', (e) => {
                setTimeout(() => this.hideSuggestions(e.target), 200);
            });
        });
    }

    bindFilterButtons() {
        const filterButtons = document.querySelectorAll('.filter-btn');
        filterButtons.forEach(button => {
            button.addEventListener('click', (e) => {
                this.handleFilter(e);
            });
        });
    }

    handleSearch(event) {
        const form = event.target;
        const searchInput = form.querySelector('input[name="q"]');
        const query = searchInput.value.trim();

        if (!query) {
            event.preventDefault();
            this.showToast('Please enter a search term', 'warning');
            searchInput.focus();
            return;
        }

        // Add to search history
        this.addToHistory(query);

        // Show loading state
        const submitButton = form.querySelector('button[type="submit"]');
        if (submitButton) {
            const originalHtml = submitButton.innerHTML;
            submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
            submitButton.disabled = true;

            // Re-enable button after a delay (form will navigate away anyway)
            setTimeout(() => {
                submitButton.innerHTML = originalHtml;
                submitButton.disabled = false;
            }, 2000);
        }
    }

    handleSearchInput(event) {
        const input = event.target;
        const query = input.value.trim();

        if (query.length >= 2) {
            this.debounce(() => {
                this.fetchSuggestions(query, input);
            }, 300)();
        } else {
            this.hideSuggestions(input);
        }
    }

    handleKeyDown(event) {
        const input = event.target;
        const suggestions = this.getSuggestionsContainer(input);

        if (!suggestions || !suggestions.style.display || suggestions.style.display === 'none') {
            return;
        }

        const suggestionItems = suggestions.querySelectorAll('.suggestion-item');
        const currentActive = suggestions.querySelector('.suggestion-item.active');
        let activeIndex = Array.from(suggestionItems).indexOf(currentActive);

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                activeIndex = activeIndex < suggestionItems.length - 1 ? activeIndex + 1 : 0;
                this.setActiveSuggestion(suggestionItems, activeIndex);
                break;

            case 'ArrowUp':
                event.preventDefault();
                activeIndex = activeIndex > 0 ? activeIndex - 1 : suggestionItems.length - 1;
                this.setActiveSuggestion(suggestionItems, activeIndex);
                break;

            case 'Enter':
                if (currentActive) {
                    event.preventDefault();
                    currentActive.click();
                }
                break;

            case 'Escape':
                this.hideSuggestions(input);
                input.blur();
                break;
        }
    }

    async fetchSuggestions(query, input) {
        try {
            // For now, show history-based suggestions
            // In a full implementation, this would call a backend endpoint
            this.showHistorySuggestions(query, input);
        } catch (error) {
            console.error('Error fetching suggestions:', error);
        }
    }

    showHistorySuggestions(query, input) {
        const history = this.getSearchHistory();
        const filteredHistory = history.filter(term => 
            term.toLowerCase().includes(query.toLowerCase()) && 
            term.toLowerCase() !== query.toLowerCase()
        ).slice(0, 5);

        // Add some common search suggestions
        const commonSuggestions = [
            'commercial refrigerator',
            'pizza oven',
            'stainless steel prep table',
            'commercial dishwasher',
            'deep fryer',
            'ice machine',
            'food processor',
            'mixer',
            'grill',
            'convection oven'
        ].filter(term => 
            term.toLowerCase().includes(query.toLowerCase()) && 
            term.toLowerCase() !== query.toLowerCase()
        ).slice(0, 3);

        const suggestions = [...new Set([...filteredHistory, ...commonSuggestions])].slice(0, 5);

        this.displaySuggestions(suggestions, input, query);
    }

    displaySuggestions(suggestions, input, query) {
        const container = this.getSuggestionsContainer(input);
        
        if (suggestions.length === 0) {
            this.hideSuggestions(input);
            return;
        }

        container.innerHTML = '';
        
        suggestions.forEach((suggestion, index) => {
            const item = document.createElement('div');
            item.className = 'suggestion-item px-3 py-2';
            item.style.cursor = 'pointer';
            item.style.borderBottom = '1px solid #eee';
            
            // Highlight matching text
            const highlighted = suggestion.replace(
                new RegExp(`(${query})`, 'gi'),
                '<strong>$1</strong>'
            );
            
            item.innerHTML = `
                <i class="fas fa-search text-muted me-2"></i>
                ${highlighted}
            `;

            item.addEventListener('click', () => {
                input.value = suggestion;
                input.closest('form').submit();
            });

            item.addEventListener('mouseenter', () => {
                this.setActiveSuggestion(container.querySelectorAll('.suggestion-item'), index);
            });

            container.appendChild(item);
        });

        this.showSuggestions(input);
    }

    getSuggestionsContainer(input) {
        let container = input.parentNode.querySelector('.search-suggestions');
        if (!container) {
            container = document.createElement('div');
            container.className = 'search-suggestions position-absolute bg-white border rounded shadow-sm';
            container.style.top = '100%';
            container.style.left = '0';
            container.style.right = '0';
            container.style.zIndex = '1000';
            container.style.display = 'none';
            container.style.maxHeight = '300px';
            container.style.overflowY = 'auto';

            input.parentNode.style.position = 'relative';
            input.parentNode.appendChild(container);
        }
        return container;
    }

    showSuggestions(input) {
        const container = this.getSuggestionsContainer(input);
        container.style.display = 'block';
    }

    hideSuggestions(input) {
        const container = this.getSuggestionsContainer(input);
        container.style.display = 'none';
    }

    setActiveSuggestion(items, activeIndex) {
        items.forEach((item, index) => {
            if (index === activeIndex) {
                item.classList.add('active');
                item.style.backgroundColor = '#f8f9fa';
            } else {
                item.classList.remove('active');
                item.style.backgroundColor = '';
            }
        });
    }

    handleFilter(event) {
        event.preventDefault();
        const button = event.target;
        const filterValue = button.dataset.filter;
        const filterType = button.dataset.filterType;

        // Toggle active state
        const filterGroup = button.parentNode;
        const activeButton = filterGroup.querySelector('.filter-btn.active');
        
        if (activeButton) {
            activeButton.classList.remove('active');
        }
        
        if (activeButton !== button) {
            button.classList.add('active');
            this.applyFilter(filterType, filterValue);
        } else {
            this.clearFilter(filterType);
        }
    }

    applyFilter(filterType, filterValue) {
        const url = new URL(window.location);
        url.searchParams.set(filterType, filterValue);
        url.searchParams.set('page', '1'); // Reset to first page
        window.location.href = url.toString();
    }

    clearFilter(filterType) {
        const url = new URL(window.location);
        url.searchParams.delete(filterType);
        url.searchParams.set('page', '1'); // Reset to first page
        window.location.href = url.toString();
    }

    setupSearchHistory() {
        // Initialize search history if it doesn't exist
        if (!localStorage.getItem('searchHistory')) {
            localStorage.setItem('searchHistory', JSON.stringify([]));
        }
    }

    getSearchHistory() {
        try {
            return JSON.parse(localStorage.getItem('searchHistory') || '[]');
        } catch (error) {
            console.error('Error reading search history:', error);
            return [];
        }
    }

    addToHistory(query) {
        try {
            let history = this.getSearchHistory();
            
            // Remove query if it already exists
            history = history.filter(term => term.toLowerCase() !== query.toLowerCase());
            
            // Add to beginning
            history.unshift(query);
            
            // Keep only last 10 searches
            history = history.slice(0, 10);
            
            localStorage.setItem('searchHistory', JSON.stringify(history));
        } catch (error) {
            console.error('Error saving search history:', error);
        }
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
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
        toast.className = `toast align-items-center text-bg-${type === 'error' ? 'danger' : type === 'success' ? 'success' : type === 'warning' ? 'warning' : 'info'} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-${type === 'error' ? 'exclamation-circle' : type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
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

// Initialize search functionality when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.search = new Search();
});

// Quick search function for global use
window.quickSearch = function(query) {
    const searchForm = document.querySelector('form[action*="search"]');
    if (searchForm) {
        const searchInput = searchForm.querySelector('input[name="q"]');
        if (searchInput) {
            searchInput.value = query;
            searchForm.submit();
        }
    }
};
