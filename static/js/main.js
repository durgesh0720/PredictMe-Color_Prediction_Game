// Color Prediction Game - Enhanced Main JavaScript Framework

// Modern UI Components and Animations
class UIEnhancements {
    constructor() {
        this.init();
    }

    init() {
        this.addRippleEffects();
        this.enhanceCards();
        this.addLoadingStates();
        this.initScrollAnimations();
        this.enhanceButtons();
    }

    // Add ripple effect to elements
    addRippleEffect(element) {
        if (!element || element.hasAttribute('data-ripple')) return;

        element.setAttribute('data-ripple', 'true');
        element.style.position = 'relative';
        element.style.overflow = 'hidden';

        element.addEventListener('click', (e) => {
            const ripple = document.createElement('span');
            const rect = element.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.cssText = `
                position: absolute;
                width: ${size}px;
                height: ${size}px;
                left: ${x}px;
                top: ${y}px;
                background: rgba(255, 255, 255, 0.3);
                border-radius: 50%;
                transform: scale(0);
                animation: ripple 0.6s linear;
                pointer-events: none;
                z-index: 1;
            `;

            element.appendChild(ripple);

            setTimeout(() => {
                if (ripple.parentNode) {
                    ripple.parentNode.removeChild(ripple);
                }
            }, 600);
        });
    }

    // Add ripple effects to common elements
    addRippleEffects() {
        const selectors = [
            '.btn:not(.btn-outline)',
            '.color-box',
            '.card:not(.no-ripple)',
            '.nav-link',
            '.amount-btn'
        ];

        selectors.forEach(selector => {
            document.querySelectorAll(selector).forEach(element => {
                this.addRippleEffect(element);
            });
        });
    }

    // Enhance card interactions
    enhanceCards() {
        document.querySelectorAll('.card, .info-card, .stats-card').forEach(card => {
            if (card.hasAttribute('data-enhanced')) return;
            card.setAttribute('data-enhanced', 'true');

            // Add hover effects
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-4px) scale(1.02)';
                card.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
            });

            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0) scale(1)';
            });
        });
    }

    // Add loading states to buttons
    addLoadingStates() {
        document.querySelectorAll('form').forEach(form => {
            form.addEventListener('submit', (e) => {
                const submitBtn = form.querySelector('button[type="submit"]');
                if (submitBtn && !submitBtn.hasAttribute('data-no-loading')) {
                    this.setButtonLoading(submitBtn, true);
                }
            });
        });
    }

    // Set button loading state
    setButtonLoading(button, loading) {
        if (loading) {
            button.setAttribute('data-original-text', button.innerHTML);
            button.innerHTML = '<span class="loading-spinner"></span> Loading...';
            button.disabled = true;
            button.classList.add('loading');
        } else {
            const originalText = button.getAttribute('data-original-text');
            if (originalText) {
                button.innerHTML = originalText;
                button.removeAttribute('data-original-text');
            }
            button.disabled = false;
            button.classList.remove('loading');
        }
    }

    // Initialize scroll animations
    initScrollAnimations() {
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-in');
                }
            });
        }, observerOptions);

        // Observe elements that should animate on scroll
        document.querySelectorAll('.card, .stats-card, .info-card, .feature-card').forEach(el => {
            el.classList.add('animate-on-scroll');
            observer.observe(el);
        });
    }

    // Enhance button interactions
    enhanceButtons() {
        document.querySelectorAll('.btn').forEach(button => {
            if (button.hasAttribute('data-enhanced')) return;
            button.setAttribute('data-enhanced', 'true');

            // Add click animation
            button.addEventListener('click', () => {
                button.style.transform = 'scale(0.95)';
                setTimeout(() => {
                    button.style.transform = '';
                }, 150);
            });
        });
    }
}

// Enhanced Notification System
class NotificationManager {
    constructor() {
        this.container = this.createContainer();
        this.notifications = [];
    }

    createContainer() {
        let container = document.querySelector('.notification-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'notification-container';
            document.body.appendChild(container);
        }
        return container;
    }

    show(message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        
        this.container.appendChild(notification);
        this.notifications.push(notification);

        // Trigger animation
        setTimeout(() => {
            notification.classList.add('show');
        }, 100);

        // Auto remove
        setTimeout(() => {
            this.remove(notification);
        }, duration);

        // Click to dismiss
        notification.addEventListener('click', () => {
            this.remove(notification);
        });

        return notification;
    }

    remove(notification) {
        if (notification && notification.parentNode) {
            notification.classList.remove('show');
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
                const index = this.notifications.indexOf(notification);
                if (index > -1) {
                    this.notifications.splice(index, 1);
                }
            }, 300);
        }
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

// Global notification instance
const notify = new NotificationManager();

// Utility Functions
const utils = {
    // Format currency
    formatCurrency(amount) {
        return new Intl.NumberFormat('en-IN', {
            style: 'currency',
            currency: 'INR',
            minimumFractionDigits: 0
        }).format(amount);
    },

    // Format time
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    },

    // Debounce function
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
    },

    // Throttle function
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Get CSRF token
    getCSRFToken() {
        const token = document.querySelector('[name=csrfmiddlewaretoken]');
        return token ? token.value : null;
    },

    // Copy to clipboard
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            notify.success('Copied to clipboard!');
            return true;
        } catch (err) {
            console.error('Failed to copy: ', err);
            notify.error('Failed to copy to clipboard');
            return false;
        }
    },

    // Modern animation utilities
    animations: {
        // Fade in animation
        fadeIn(element, duration = 300) {
            element.style.opacity = '0';
            element.style.display = 'block';

            const start = performance.now();

            function animate(currentTime) {
                const elapsed = currentTime - start;
                const progress = Math.min(elapsed / duration, 1);

                element.style.opacity = progress;

                if (progress < 1) {
                    requestAnimationFrame(animate);
                }
            }

            requestAnimationFrame(animate);
        },

        // Fade out animation
        fadeOut(element, duration = 300) {
            const start = performance.now();
            const startOpacity = parseFloat(getComputedStyle(element).opacity);

            function animate(currentTime) {
                const elapsed = currentTime - start;
                const progress = Math.min(elapsed / duration, 1);

                element.style.opacity = startOpacity * (1 - progress);

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    element.style.display = 'none';
                }
            }

            requestAnimationFrame(animate);
        },

        // Slide down animation
        slideDown(element, duration = 300) {
            element.style.height = '0';
            element.style.overflow = 'hidden';
            element.style.display = 'block';

            const targetHeight = element.scrollHeight;
            const start = performance.now();

            function animate(currentTime) {
                const elapsed = currentTime - start;
                const progress = Math.min(elapsed / duration, 1);

                element.style.height = (targetHeight * progress) + 'px';

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    element.style.height = '';
                    element.style.overflow = '';
                }
            }

            requestAnimationFrame(animate);
        },

        // Slide up animation
        slideUp(element, duration = 300) {
            const startHeight = element.offsetHeight;
            const start = performance.now();

            element.style.overflow = 'hidden';

            function animate(currentTime) {
                const elapsed = currentTime - start;
                const progress = Math.min(elapsed / duration, 1);

                element.style.height = (startHeight * (1 - progress)) + 'px';

                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    element.style.display = 'none';
                    element.style.height = '';
                    element.style.overflow = '';
                }
            }

            requestAnimationFrame(animate);
        },

        // Bounce animation
        bounce(element) {
            element.style.animation = 'bounce 0.6s ease-in-out';
            setTimeout(() => {
                element.style.animation = '';
            }, 600);
        },

        // Shake animation for errors
        shake(element) {
            element.style.animation = 'shake 0.5s ease-in-out';
            setTimeout(() => {
                element.style.animation = '';
            }, 500);
        },

        // Pulse animation
        pulse(element, duration = 1000) {
            element.style.animation = `pulse ${duration}ms ease-in-out`;
            setTimeout(() => {
                element.style.animation = '';
            }, duration);
        }
    },

    // Button utilities
    setButtonLoading(button, loading = true) {
        if (loading) {
            button.dataset.originalText = button.textContent;
            button.classList.add('btn-loading');
            button.disabled = true;
        } else {
            button.classList.remove('btn-loading');
            button.disabled = false;
            if (button.dataset.originalText) {
                button.textContent = button.dataset.originalText;
                delete button.dataset.originalText;
            }
        }
    },

    // Enhanced button click handler with loading state
    handleButtonClick(button, asyncFunction) {
        return async function(event) {
            event.preventDefault();

            if (button.disabled || button.classList.contains('btn-loading')) {
                return;
            }

            utils.setButtonLoading(button, true);

            try {
                const result = await asyncFunction(event);

                // Add success animation
                button.classList.add('btn-success-animation');
                setTimeout(() => {
                    button.classList.remove('btn-success-animation');
                }, 600);

                return result;
            } catch (error) {
                console.error('Button action failed:', error);

                // Add shake animation for error
                button.classList.add('btn-shake');
                setTimeout(() => {
                    button.classList.remove('btn-shake');
                }, 500);

                notify.error('Action failed. Please try again.');
                throw error;
            } finally {
                utils.setButtonLoading(button, false);
            }
        };
    },

    // Add ripple effect to buttons
    addRippleEffect(button) {
        button.classList.add('btn-ripple');

        button.addEventListener('click', function(e) {
            const ripple = document.createElement('span');
            const rect = this.getBoundingClientRect();
            const size = Math.max(rect.width, rect.height);
            const x = e.clientX - rect.left - size / 2;
            const y = e.clientY - rect.top - size / 2;

            ripple.style.width = ripple.style.height = size + 'px';
            ripple.style.left = x + 'px';
            ripple.style.top = y + 'px';
            ripple.classList.add('ripple');

            this.appendChild(ripple);

            setTimeout(() => {
                ripple.remove();
            }, 600);
        });
    },

    // Enhanced toast notifications
    showToast(message, type = 'info', duration = 5000) {
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.innerHTML = `
            <div style="display: flex; align-items: center; gap: 12px;">
                <i class="fas fa-${this.getToastIcon(type)}"></i>
                <span>${message}</span>
                <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; font-size: 18px; cursor: pointer; margin-left: auto;">&times;</button>
            </div>
        `;

        document.body.appendChild(toast);

        // Trigger animation
        setTimeout(() => {
            toast.classList.add('show');
        }, 100);

        // Auto remove
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => {
                if (toast.parentElement) {
                    toast.remove();
                }
            }, 300);
        }, duration);

        return toast;
    },

    getToastIcon(type) {
        const icons = {
            success: 'check-circle',
            error: 'exclamation-circle',
            warning: 'exclamation-triangle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    },

    // Validate email
    isValidEmail(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    // Validate phone number
    isValidPhone(phone) {
        const phoneRegex = /^\+?[\d\s\-\(\)]{10,}$/;
        return phoneRegex.test(phone);
    },

    // Generate random ID
    generateId() {
        return Math.random().toString(36).substr(2, 9);
    },

    // Local storage helpers
    storage: {
        set(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (e) {
                console.error('Storage set error:', e);
                return false;
            }
        },

        get(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.error('Storage get error:', e);
                return defaultValue;
            }
        },

        remove(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (e) {
                console.error('Storage remove error:', e);
                return false;
            }
        }
    }
};

// Form Validation
class FormValidator {
    constructor(form) {
        this.form = form;
        this.errors = {};
        this.rules = {};
    }

    addRule(fieldName, rule, message) {
        if (!this.rules[fieldName]) {
            this.rules[fieldName] = [];
        }
        this.rules[fieldName].push({ rule, message });
        return this;
    }

    validate() {
        this.errors = {};
        const formData = new FormData(this.form);

        for (const [fieldName, rules] of Object.entries(this.rules)) {
            const value = formData.get(fieldName);
            
            for (const { rule, message } of rules) {
                if (!rule(value)) {
                    if (!this.errors[fieldName]) {
                        this.errors[fieldName] = [];
                    }
                    this.errors[fieldName].push(message);
                    break; // Stop at first error for this field
                }
            }
        }

        this.displayErrors();
        return Object.keys(this.errors).length === 0;
    }

    displayErrors() {
        // Clear previous errors
        this.form.querySelectorAll('.error-message').forEach(el => el.remove());
        this.form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));

        // Display new errors
        for (const [fieldName, messages] of Object.entries(this.errors)) {
            const field = this.form.querySelector(`[name="${fieldName}"]`);
            if (field) {
                field.classList.add('error');
                
                const errorDiv = document.createElement('div');
                errorDiv.className = 'error-message text-error';
                errorDiv.style.fontSize = '0.875rem';
                errorDiv.style.marginTop = '0.25rem';
                errorDiv.textContent = messages[0];
                
                field.parentNode.appendChild(errorDiv);
            }
        }
    }

    // Common validation rules
    static rules = {
        required: (value) => value && value.trim() !== '',
        email: (value) => !value || utils.isValidEmail(value),
        phone: (value) => !value || utils.isValidPhone(value),
        minLength: (min) => (value) => !value || value.length >= min,
        maxLength: (max) => (value) => !value || value.length <= max,
        numeric: (value) => !value || !isNaN(value),
        positive: (value) => !value || parseFloat(value) > 0,
        match: (otherFieldName) => (value, form) => {
            const otherField = form.querySelector(`[name="${otherFieldName}"]`);
            return !value || !otherField || value === otherField.value;
        }
    };
}

// Loading State Manager
class LoadingManager {
    constructor() {
        this.loadingElements = new Set();
    }

    show(element, text = 'Loading...') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        element.classList.add('loading');
        element.setAttribute('data-original-text', element.textContent);
        element.textContent = text;
        element.disabled = true;
        
        this.loadingElements.add(element);
    }

    hide(element) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        
        if (!element) return;

        element.classList.remove('loading');
        const originalText = element.getAttribute('data-original-text');
        if (originalText) {
            element.textContent = originalText;
            element.removeAttribute('data-original-text');
        }
        element.disabled = false;
        
        this.loadingElements.delete(element);
    }

    hideAll() {
        this.loadingElements.forEach(element => this.hide(element));
    }
}

// Global loading manager
const loading = new LoadingManager();

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 300);
        }, 5000);
    });

    // Add click handlers for dismissible alerts
    document.querySelectorAll('.alert').forEach(alert => {
        alert.style.cursor = 'pointer';
        alert.addEventListener('click', () => {
            alert.style.opacity = '0';
            setTimeout(() => {
                if (alert.parentNode) {
                    alert.parentNode.removeChild(alert);
                }
            }, 300);
        });
    });

    // Initialize enhanced buttons
    initializeEnhancedUI();
});

// Initialize enhanced UI elements
function initializeEnhancedUI() {
    // Add ripple effect to all buttons
    document.querySelectorAll('.btn').forEach(button => {
        utils.addRippleEffect(button);

        // Add touch feedback for mobile
        if ('ontouchstart' in window) {
            button.addEventListener('touchstart', function() {
                this.classList.add('active');
            });

            button.addEventListener('touchend', function() {
                this.classList.remove('active');
            });
        }
    });

    // Add touch feedback for color boxes
    document.querySelectorAll('.color-box').forEach(box => {
        if ('ontouchstart' in window) {
            box.addEventListener('touchstart', function() {
                if (!this.classList.contains('disabled')) {
                    this.classList.add('active');
                }
            });

            box.addEventListener('touchend', function() {
                this.classList.remove('active');
            });
        }
    });

    // Detect if device is mobile
    const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);

    // Add mobile-specific classes if needed
    if (isMobile) {
        document.body.classList.add('mobile-device');

        // Adjust viewport for better mobile experience
        const viewportMeta = document.querySelector('meta[name="viewport"]');
        if (viewportMeta) {
            viewportMeta.content = 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0';
        }

        // Add fastclick to eliminate 300ms delay
        if (typeof FastClick !== 'undefined') {
            FastClick.attach(document.body);
        }
    }

    // Add swipe gesture support for mobile
    if (isMobile) {
        enableSwipeGestures();
    }
}

// Enable swipe gestures for mobile
function enableSwipeGestures() {
    let touchStartX = 0;
    let touchEndX = 0;

    document.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
    }, false);

    document.addEventListener('touchend', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        handleSwipe();
    }, false);

    function handleSwipe() {
        const swipeThreshold = 100;

        if (touchEndX < touchStartX - swipeThreshold) {
            // Swipe left
            const event = new CustomEvent('swipe-left');
            document.dispatchEvent(event);
        }

        if (touchEndX > touchStartX + swipeThreshold) {
            // Swipe right
            const event = new CustomEvent('swipe-right');
            document.dispatchEvent(event);
        }
    }
}

// Form validation setup - Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('form[data-validate]').forEach(form => {
        const validator = new FormValidator(form);

        // Add common validation rules based on input types
        form.querySelectorAll('input[required]').forEach(input => {
            validator.addRule(input.name, FormValidator.rules.required, 'This field is required');
        });

        form.querySelectorAll('input[type="email"]').forEach(input => {
            validator.addRule(input.name, FormValidator.rules.email, 'Please enter a valid email address');
        });

        form.addEventListener('submit', (e) => {
            if (!validator.validate()) {
                e.preventDefault();
                notify.error('Please fix the errors in the form');
            }
        });
    });
});

// Initialize UI Enhancements
const uiEnhancements = new UIEnhancements();

// Export for use in other scripts
window.ColorPredictionGame = {
    notify,
    utils,
    FormValidator,
    loading,
    uiEnhancements,
    UIEnhancements
};

// Initialize framework when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize UI enhancements for dynamically loaded content
    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList') {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === Node.ELEMENT_NODE) {
                        // Re-initialize enhancements for new elements
                        if (node.matches('.btn') || node.querySelector('.btn')) {
                            uiEnhancements.enhanceButtons();
                        }
                        if (node.matches('.card') || node.querySelector('.card')) {
                            uiEnhancements.enhanceCards();
                        }
                        // Add ripple effects to new elements
                        const rippleElements = node.querySelectorAll('.btn:not(.btn-outline), .color-box, .card:not(.no-ripple)');
                        rippleElements.forEach(el => uiEnhancements.addRippleEffect(el));
                    }
                });
            }
        });
    });

    // Start observing
    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    // Add global keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        // ESC key to close modals/notifications
        if (e.key === 'Escape') {
            // Close any open modals
            const modals = document.querySelectorAll('.modal.show');
            modals.forEach(modal => {
                modal.classList.remove('show');
            });

            // Close notifications
            const notifications = document.querySelectorAll('.notification.show');
            notifications.forEach(notification => {
                notify.remove(notification);
            });
        }
    });

    // Add smooth scrolling to anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // Initialize lazy loading for images
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    img.src = img.dataset.src;
                    img.classList.remove('lazy');
                    imageObserver.unobserve(img);
                }
            });
        });

        document.querySelectorAll('img[data-src]').forEach(img => {
            imageObserver.observe(img);
        });
    }

    console.log('🎮 Color Prediction Game - Enhanced UI Framework Loaded');
});
