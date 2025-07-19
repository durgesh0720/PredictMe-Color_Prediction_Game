/**
 * Admin Game Control Live - JavaScript Module
 * 
 * This module provides real-time game control functionality for the admin panel.
 * It includes WebSocket communication, security validation, and UI management.
 * 
 * @version 1.0.0
 * @author Admin Panel Team
 * @created 2024-01-19
 * 
 * Features:
 * - Real-time WebSocket communication
 * - Enhanced security validation
 * - Input sanitization and validation
 * - Rate limiting and DoS protection
 * - Accessibility support
 * - Error handling and recovery
 */

// Encapsulate all functionality in an IIFE to avoid global namespace pollution
(function() {
    'use strict';
    
    /**
     * Configuration constants for the admin game control system
     * @readonly
     * @enum {number}
     */
    const CONFIG = {
        WEBSOCKET_RECONNECT_ATTEMPTS: 5,
        WEBSOCKET_RECONNECT_DELAY: 1000,
        WEBSOCKET_HEARTBEAT_INTERVAL: 15000,
        WEBSOCKET_PONG_TIMEOUT: 60000,
        TIMER_UPDATE_INTERVAL: 2000,
        FALLBACK_RECONNECT_INTERVAL: 120000,
        MAX_RECONNECT_DELAY: 30000,
        MESSAGE_SIZE_LIMIT: 1024 * 1024, // 1MB
        RATE_LIMIT_MESSAGES_PER_SECOND: 20,
        REQUEST_TIMEOUT: 10000 // 10 seconds
    };
    
    /**
     * Private state variables
     * @private
     */
    let selectedColors = {};
    let wsManager = null;
    let lastServerUpdate = null;
    let serverTimers = [];
    let isPageVisible = true;
    
    /**
     * Cache for performance optimization
     * @private
     */
    const statsCache = { 
        data: null, 
        timestamp: 0, 
        ttl: 1000 
    };
    
    /**
     * Input validation and sanitization functions
     * @namespace ValidationUtils
     */
    const ValidationUtils = {
        /**
         * Validate input based on type
         * @param {*} input - The input to validate
         * @param {string} type - The type of validation to perform
         * @returns {string|null} - Validated input or null if invalid
         */
        validateInput(input, type) {
            switch(type) {
                case 'roundId':
                    return /^[a-zA-Z0-9-_]+$/.test(input) ? input : null;
                case 'color':
                    return ['red', 'green', 'violet', 'blue'].includes(input) ? input : null;
                case 'messageType':
                    const validTypes = [
                        'get_game_status', 'get_live_stats', 'get_timer_info',
                        'select_color', 'sync_state', 'force_refresh', 'ping'
                    ];
                    return validTypes.includes(input) ? input : null;
                default:
                    return null;
            }
        },
        
        /**
         * Escape HTML to prevent XSS attacks
         * @param {string} text - Text to escape
         * @returns {string} - Escaped HTML
         */
        escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        },
        
        /**
         * Validate timestamp to prevent replay attacks
         * @param {number} timestamp - Timestamp to validate
         * @param {number} [windowMs=30000] - Time window in milliseconds
         * @returns {boolean} - True if timestamp is valid
         */
        validateTimestamp(timestamp, windowMs = 30000) {
            if (!timestamp) return true; // Optional timestamp
            const currentTime = Date.now();
            return Math.abs(currentTime - timestamp) <= windowMs;
        }
    };
    
    /**
     * WebSocket communication utilities
     * @namespace WebSocketUtils
     */
    const WebSocketUtils = {
        /**
         * Generate unique client ID for session tracking
         * @returns {string} - Unique client ID
         */
        generateClientId() {
            return 'admin_' + Math.random().toString(36).substr(2, 9) + '_' + Date.now();
        },

        /**
         * Secure message sending with validation
         * @param {Object} message - Message to send
         * @returns {boolean} - True if message was sent successfully
         */
        sendSecureMessage(message) {
            if (!wsManager || !wsManager.isConnected) {
                console.warn('WebSocket not connected. Message not sent:', message);
                return false;
            }

            return wsManager.sendMessage(message);
        },

        /**
         * Initialize WebSocket connection
         */
        initWebSocket() {
            if (wsManager) {
                wsManager.connect();
            } else {
                initializeWebSocket();
            }
        }
    };
    
    /**
     * UI utility functions
     * @namespace UIUtils
     */
    const UIUtils = {
        /**
         * Show success message to user
         * @param {string} message - Success message to display
         */
        showSuccessMessage(message) {
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-success';
            alertDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
                padding: 1rem;
                border-radius: var(--radius);
                background: var(--color-green-light);
                border: 1px solid var(--color-green);
                color: var(--status-active-color);
                box-shadow: var(--shadow-lg);
            `;
            alertDiv.innerHTML = `<i class="fas fa-check-circle" aria-hidden="true"></i> ${ValidationUtils.escapeHtml(message)}`;
            alertDiv.setAttribute('role', 'alert');
            alertDiv.setAttribute('aria-live', 'polite');

            document.body.appendChild(alertDiv);

            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 3000);
        },
        
        /**
         * Show error message to user
         * @param {string} message - Error message to display
         */
        showErrorMessage(message) {
            const alertDiv = document.createElement('div');
            alertDiv.className = 'alert alert-danger';
            alertDiv.style.cssText = `
                position: fixed;
                top: 20px;
                right: 20px;
                z-index: 9999;
                max-width: 400px;
                padding: 1rem;
                border-radius: var(--radius);
                background: #fef2f2;
                border: 1px solid var(--danger);
                color: #dc2626;
                box-shadow: var(--shadow-lg);
            `;
            alertDiv.innerHTML = `<i class="fas fa-exclamation-circle" aria-hidden="true"></i> ${ValidationUtils.escapeHtml(message)}`;
            alertDiv.setAttribute('role', 'alert');
            alertDiv.setAttribute('aria-live', 'assertive');

            document.body.appendChild(alertDiv);

            setTimeout(() => {
                if (alertDiv.parentNode) {
                    alertDiv.remove();
                }
            }, 5000);
        },
        
        /**
         * Get CSRF cookie value securely
         * @param {string} name - Cookie name
         * @returns {string|null} - Cookie value or null
         */
        getCookie(name) {
            if (!name || typeof name !== 'string') {
                console.error('Invalid cookie name');
                return null;
            }
            
            let cookieValue = null;
            if (document.cookie && document.cookie !== '') {
                const cookies = document.cookie.split(';');
                for (let i = 0; i < cookies.length; i++) {
                    const cookie = cookies[i].trim();
                    if (cookie.substring(0, name.length + 1) === (name + '=')) {
                        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                        break;
                    }
                }
            }
            return cookieValue;
        }
    };

    /**
     * Initialize WebSocket Manager
     */
    function initializeWebSocket() {
        if (typeof WebSocketManager === 'undefined') {
            console.error('WebSocketManager not loaded');
            UIUtils.showErrorMessage('WebSocket manager not available');
            return;
        }

        wsManager = new WebSocketManager(CONFIG, {
            ValidationUtils,
            UIUtils
        });

        // Register message handlers
        wsManager.onMessage('comprehensive_game_status', handleGameStatusMessage);
        wsManager.onMessage('live_betting_stats', handleLiveBettingStats);
        wsManager.onMessage('bet_placed_update', handleBetPlacedUpdate);
        wsManager.onMessage('timer_info', handleTimerInfo);
        wsManager.onMessage('timer_sync', handleTimerSync);
        wsManager.onMessage('timer_update', handleTimerUpdate);
        wsManager.onMessage('color_selected', handleColorSelected);
        wsManager.onMessage('color_selection_confirmed', handleColorSelectionConfirmed);
        wsManager.onMessage('round_ended', handleRoundEnded);
        wsManager.onMessage('new_round_started', handleNewRoundStarted);
        wsManager.onMessage('state_synced', handleStateSynced);

        // Connect to WebSocket
        wsManager.connect();

        // Store globally for access from other functions
        window.wsManager = wsManager;
    }

    /**
     * Message handlers for WebSocket events
     */
    function handleGameStatusMessage(data) {
        console.log('Game status received:', data);
        // Handle game status updates
    }

    function handleLiveBettingStats(data) {
        console.log('Live betting stats received:', data);

        if (!data.stats) {
            console.warn('Invalid betting stats received:', data);
            return;
        }

        // Update betting statistics display for each color
        const colors = ['red', 'green', 'violet', 'blue'];

        colors.forEach(color => {
            const colorStats = data.stats[color] || { amount: 0, count: 0, users: 0 };

            // Update color statistics in round cards
            document.querySelectorAll(`[data-round-id]`).forEach(roundCard => {
                const colorStatsElement = roundCard.querySelector(`.color-stats-${color}`);
                const colorAmountElement = roundCard.querySelector(`.color-amount-${color}`);
                const colorCountElement = roundCard.querySelector(`.color-count-${color}`);
                const colorUsersElement = roundCard.querySelector(`.color-users-${color}`);

                if (colorStatsElement) {
                    colorStatsElement.textContent = `$${colorStats.amount} (${colorStats.count} bets)`;
                }

                if (colorAmountElement) {
                    colorAmountElement.textContent = `$${colorStats.amount}`;
                }

                if (colorCountElement) {
                    colorCountElement.textContent = colorStats.count;
                }

                if (colorUsersElement) {
                    colorUsersElement.textContent = colorStats.users;
                }
            });

            // Update global color statistics if elements exist
            const globalColorAmount = document.getElementById(`${color}-total-amount`);
            const globalColorCount = document.getElementById(`${color}-total-count`);
            const globalColorUsers = document.getElementById(`${color}-total-users`);
            const globalColorPercentage = document.getElementById(`${color}-percentage`);

            if (globalColorAmount) {
                globalColorAmount.textContent = `$${colorStats.amount}`;
            }

            if (globalColorCount) {
                globalColorCount.textContent = colorStats.count;
            }

            if (globalColorUsers) {
                globalColorUsers.textContent = colorStats.users;
            }

            // Calculate and update percentage
            if (globalColorPercentage) {
                const totalAmount = colors.reduce((sum, c) => sum + (data.stats[c]?.amount || 0), 0);
                const percentage = totalAmount > 0 ? ((colorStats.amount / totalAmount) * 100).toFixed(1) : 0;
                globalColorPercentage.textContent = `${percentage}% of total bets`;
            }
        });

        // Update total statistics
        const totalAmount = colors.reduce((sum, color) => sum + (data.stats[color]?.amount || 0), 0);
        const totalCount = colors.reduce((sum, color) => sum + (data.stats[color]?.count || 0), 0);
        const totalUsers = colors.reduce((sum, color) => sum + (data.stats[color]?.users || 0), 0);

        const totalAmountElement = document.getElementById('total-betting-amount');
        const totalCountElement = document.getElementById('total-betting-count');
        const totalUsersElement = document.getElementById('total-betting-users');
        const activeRoundsElement = document.getElementById('active-rounds-count');

        if (totalAmountElement) {
            totalAmountElement.textContent = `$${totalAmount}`;
        }

        if (totalCountElement) {
            totalCountElement.textContent = totalCount;
        }

        if (totalUsersElement) {
            totalUsersElement.textContent = totalUsers;
        }

        if (activeRoundsElement) {
            activeRoundsElement.textContent = data.active_rounds_count || 0;
        }

        // Update timestamp
        const timestampElement = document.getElementById('stats-timestamp');
        if (timestampElement && data.timestamp) {
            const timestamp = new Date(data.timestamp);
            timestampElement.textContent = `Last updated: ${timestamp.toLocaleTimeString()}`;
        }
    }

    function handleBetPlacedUpdate(data) {
        console.log('Bet placed update received:', data);

        // Show real-time bet notification
        const message = `${ValidationUtils.escapeHtml(data.username)} bet $${data.amount} on ${ValidationUtils.escapeHtml(data.color || data.number)}`;
        UIUtils.showSuccessMessage(message);

        // Update round-specific betting info if available
        const roundCard = document.querySelector(`[data-round-id="${CSS.escape(data.round_id)}"]`);
        if (roundCard) {
            // Add visual indicator for new bet
            roundCard.classList.add('new-bet-flash');
            setTimeout(() => {
                roundCard.classList.remove('new-bet-flash');
            }, 1000);

            // Update bet count indicator if it exists
            const betCountElement = roundCard.querySelector('.bet-count');
            if (betCountElement) {
                const currentCount = parseInt(betCountElement.textContent) || 0;
                betCountElement.textContent = currentCount + 1;
            }
        }

        // The live betting stats will be automatically updated by the server
        // after this event is processed
    }

    function handleTimerInfo(data) {
        console.log('Timer info received:', data);

        if (!data.success || !data.timers) {
            console.warn('Invalid timer info received:', data);
            return;
        }

        // Update timer displays for each round
        data.timers.forEach(timer => {
            const roundCard = document.querySelector(`[data-round-id="${CSS.escape(timer.round_id)}"]`);
            if (!roundCard) {
                return; // Round card not found, skip
            }

            const timerElement = roundCard.querySelector('.timer');
            if (!timerElement) {
                return; // Timer element not found, skip
            }

            // Update timer display
            const timeRemaining = timer.time_remaining;
            const phase = timer.phase;

            // Update timer text and styling
            if (phase === 'ended' || timeRemaining <= 0) {
                timerElement.textContent = 'ENDED';
                timerElement.className = 'timer ended';
            } else {
                timerElement.textContent = `${timeRemaining}s`;

                // Update timer styling based on time remaining
                if (timeRemaining <= 10) {
                    timerElement.className = 'timer critical';
                } else if (timeRemaining <= 20) {
                    timerElement.className = 'timer warning';
                } else {
                    timerElement.className = 'timer normal';
                }
            }

            // Update data attribute for potential CSS animations
            timerElement.setAttribute('data-time', timeRemaining);

            // Update round status and controls based on phase
            const statusBadge = roundCard.querySelector('.status-badge');
            const colorSelection = roundCard.querySelector('.color-selection');

            if (statusBadge) {
                if (phase === 'ended') {
                    statusBadge.textContent = 'ENDED';
                    statusBadge.className = 'status-badge ended';
                } else if (phase === 'result') {
                    statusBadge.textContent = 'RESULT';
                    statusBadge.className = 'status-badge result';
                } else {
                    statusBadge.textContent = 'LIVE';
                    statusBadge.className = 'status-badge active';
                }
            }

            // Show/hide color selection based on whether admin can still select
            if (colorSelection) {
                if (timer.can_select && phase !== 'ended') {
                    colorSelection.style.display = 'flex';
                } else {
                    colorSelection.style.display = 'none';
                }
            }
        });
    }

    function handleTimerSync(data) {
        console.log('Timer sync received:', data);

        // Update specific round timer based on sync data from user game consumer
        const roundCard = document.querySelector(`[data-round-id="${CSS.escape(data.round_id)}"]`);
        if (!roundCard) {
            return; // Round card not found, skip
        }

        const timerElement = roundCard.querySelector('.timer');
        if (!timerElement) {
            return; // Timer element not found, skip
        }

        const timeRemaining = data.time_remaining;
        const phase = data.phase;

        // Update timer display with synchronized data
        if (phase === 'ended' || timeRemaining <= 0) {
            timerElement.textContent = 'ENDED';
            timerElement.className = 'timer ended';
        } else {
            timerElement.textContent = `${timeRemaining}s`;

            // Update timer styling based on time remaining
            if (timeRemaining <= 10) {
                timerElement.className = 'timer critical';
            } else if (timeRemaining <= 20) {
                timerElement.className = 'timer warning';
            } else {
                timerElement.className = 'timer normal';
            }
        }

        // Update data attribute
        timerElement.setAttribute('data-time', timeRemaining);

        // Also update any global countdown displays (like in dashboard)
        const globalCountdown = document.getElementById('countdown');
        if (globalCountdown && timeRemaining > 0) {
            const minutes = Math.floor(timeRemaining / 60);
            const seconds = timeRemaining % 60;
            globalCountdown.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        }

        // Update round status indicators
        const statusBadge = roundCard.querySelector('.status-badge');
        const colorSelection = roundCard.querySelector('.color-selection');

        if (statusBadge) {
            if (phase === 'ended' || timeRemaining <= 0) {
                statusBadge.textContent = 'ENDED';
                statusBadge.className = 'status-badge ended';
            } else if (timeRemaining <= 10) {
                statusBadge.textContent = 'RESULT';
                statusBadge.className = 'status-badge result';
            } else {
                statusBadge.textContent = 'LIVE';
                statusBadge.className = 'status-badge active';
            }
        }

        // Show/hide color selection based on phase
        if (colorSelection) {
            if (timeRemaining > 0 && phase === 'betting') {
                colorSelection.style.display = 'flex';
            } else {
                colorSelection.style.display = 'none';
            }
        }
    }

    function handleTimerUpdate(data) {
        console.log('Timer update received:', data);

        // This is the same timer update that users receive - ensures perfect synchronization
        const timeRemaining = data.time_remaining;
        const phase = data.phase;
        const roundId = data.round_id;

        // Update specific round timer
        const roundCard = document.querySelector(`[data-round-id="${CSS.escape(roundId)}"]`);
        if (roundCard) {
            const timerElement = roundCard.querySelector('.timer');
            if (timerElement) {
                if (phase === 'result' || timeRemaining <= 0) {
                    timerElement.textContent = 'ENDED';
                    timerElement.className = 'timer ended';
                } else {
                    timerElement.textContent = `${timeRemaining}s`;

                    // Update timer styling based on time remaining
                    if (timeRemaining <= 10) {
                        timerElement.className = 'timer critical';
                    } else if (timeRemaining <= 20) {
                        timerElement.className = 'timer warning';
                    } else {
                        timerElement.className = 'timer normal';
                    }
                }
                timerElement.setAttribute('data-time', timeRemaining);
            }
        }

        // Update global countdown display
        const globalCountdown = document.getElementById('countdown');
        if (globalCountdown && timeRemaining > 0) {
            const minutes = Math.floor(timeRemaining / 60);
            const seconds = timeRemaining % 60;
            globalCountdown.textContent = `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
        } else if (globalCountdown && timeRemaining <= 0) {
            globalCountdown.textContent = 'Round Ended';
        }
    }

    function handleColorSelected(data) {
        console.log('Color selected:', data);
        // Handle color selection events
    }

    function handleColorSelectionConfirmed(data) {
        console.log('Color selection confirmed:', data);
        // Handle color selection confirmation
    }

    function handleRoundEnded(data) {
        console.log('Round ended:', data);
        // Handle round end events
    }

    function handleNewRoundStarted(data) {
        console.log('New round started:', data);
        // Handle new round events
    }

    function handleStateSynced(data) {
        console.log('State synchronized:', data);
        UIUtils.showSuccessMessage('State synchronized with server');
    }

    /**
     * Core game control functions
     * @namespace GameControl
     */
    const GameControl = {
        /**
         * Select color for a round with enhanced security validation
         * @param {string} roundId - Round ID
         * @param {string} color - Color to select
         */
        selectColor(roundId, color) {
            // Input validation
            const validatedRoundId = ValidationUtils.validateInput(roundId, 'roundId');
            const validatedColor = ValidationUtils.validateInput(color, 'color');

            if (!validatedRoundId || !validatedColor) {
                console.error('Invalid input parameters:', { roundId, color });
                UIUtils.showErrorMessage('Invalid selection parameters');
                return;
            }

            // Store selection locally first
            selectedColors[validatedRoundId] = validatedColor;

            // Update UI immediately for responsive feedback
            const roundCard = document.querySelector(`[data-round-id="${CSS.escape(validatedRoundId)}"]`);
            if (!roundCard) {
                console.error('Round card not found:', validatedRoundId);
                return;
            }

            const colorOptions = roundCard.querySelectorAll('.color-option');

            // Remove selected class from all options
            colorOptions.forEach(option => option.classList.remove('selected'));

            // Add selected class to clicked option
            const selectedOption = roundCard.querySelector(`.color-option.${validatedColor}`);
            if (selectedOption) {
                selectedOption.classList.add('selected');
            }

            // Update status message with XSS protection
            const statusText = roundCard.querySelector(`#status-text-${CSS.escape(validatedRoundId)}`);
            if (statusText) {
                statusText.innerHTML = `<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Selecting ${ValidationUtils.escapeHtml(validatedColor.toUpperCase())}...`;
            }

            // Call the API endpoint to save the color selection
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);

            fetch('/control-panel/api/select-color/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': UIUtils.getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({
                    round_id: validatedRoundId,
                    color: validatedColor,
                    timestamp: Date.now()
                }),
                signal: controller.signal
            })
            .then(response => {
                clearTimeout(timeoutId);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    // Update status message to show success
                    if (statusText) {
                        statusText.innerHTML = `<i class="fas fa-check-circle" aria-hidden="true"></i> ${ValidationUtils.escapeHtml(validatedColor.toUpperCase())} selected successfully`;
                    }

                    // Send WebSocket message for real-time sync after successful API call
                    WebSocketUtils.sendSecureMessage({
                        'type': 'color_selected_event',
                        'round_id': validatedRoundId,
                        'color': validatedColor,
                        'timestamp': Date.now()
                    });

                    UIUtils.showSuccessMessage(`Color ${validatedColor.toUpperCase()} selected for round ${validatedRoundId}`);
                } else {
                    throw new Error(data.error || 'Failed to select color');
                }
            })
            .catch(error => {
                clearTimeout(timeoutId);
                console.error('Error selecting color:', error);

                // Reset UI state on error
                colorOptions.forEach(option => option.classList.remove('selected'));
                delete selectedColors[validatedRoundId];

                let errorMessage = 'Failed to select color';
                if (error.name === 'AbortError') {
                    errorMessage = 'Request timed out. Please try again.';
                } else if (error.message) {
                    errorMessage = `Error: ${error.message}`;
                }

                if (statusText) {
                    statusText.innerHTML = `<i class="fas fa-exclamation-circle" aria-hidden="true"></i> ${errorMessage}`;
                }

                UIUtils.showErrorMessage(errorMessage);
            });
        },

        /**
         * Submit game result with enhanced security
         * @param {string} roundId - Round ID to submit result for
         */
        submitResult(roundId) {
            // Input validation
            const validatedRoundId = ValidationUtils.validateInput(roundId, 'roundId');
            if (!validatedRoundId) {
                console.error('Invalid round ID:', roundId);
                UIUtils.showErrorMessage('Invalid round ID');
                return;
            }

            const selectedColor = selectedColors[validatedRoundId];
            if (!selectedColor) {
                UIUtils.showErrorMessage('Please select a color first');
                return;
            }

            // Validate selected color
            const validatedColor = ValidationUtils.validateInput(selectedColor, 'color');
            if (!validatedColor) {
                console.error('Invalid selected color:', selectedColor);
                UIUtils.showErrorMessage('Invalid color selection');
                return;
            }

            // Disable the submit button to prevent double submission
            const submitBtn = document.getElementById(`submit-${CSS.escape(validatedRoundId)}`);
            if (!submitBtn) {
                console.error('Submit button not found for round:', validatedRoundId);
                return;
            }

            submitBtn.disabled = true;
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin" aria-hidden="true"></i> Submitting...';
            submitBtn.setAttribute('aria-busy', 'true');

            // Create secure request with timeout
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);

            // Submit the result with enhanced security
            fetch('/control-panel/api/submit-result/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': UIUtils.getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest' // CSRF protection
                },
                body: JSON.stringify({
                    round_id: validatedRoundId,
                    color: validatedColor,
                    timestamp: Date.now() // Prevent replay attacks
                }),
                signal: controller.signal
            })
            .then(response => {
                clearTimeout(timeoutId);

                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }

                return response.json();
            })
            .then(data => {
                if (data.success) {
                    this.handleSuccessfulSubmission(validatedRoundId, data);
                } else {
                    throw new Error(data.message || 'Unknown error occurred');
                }
            })
                .catch(error => {
                    clearTimeout(timeoutId);
                    this.handleSubmissionError(validatedRoundId, error, submitBtn);
                });
        },

        /**
         * Create test rounds for testing
         */
        createTestRounds() {
            if (!confirm('Create test rounds for testing? This will create active rounds for all game types.')) {
                return;
            }

            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), CONFIG.REQUEST_TIMEOUT);

            fetch('/control-panel/api/create-test-rounds/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': ValidationUtils.getCookie('csrftoken'),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                signal: controller.signal
            })
            .then(response => {
                clearTimeout(timeoutId);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    UIUtils.showSuccessMessage(`Success! ${ValidationUtils.escapeHtml(data.message)}`);
                    setTimeout(() => {
                        location.reload();
                    }, 2000);
                } else {
                    throw new Error(data.message || 'Unknown error');
                }
            })
            .catch(error => {
                clearTimeout(timeoutId);
                console.error('Error creating test rounds:', error);

                let errorMessage = 'Failed to create test rounds';
                if (error.name === 'AbortError') {
                    errorMessage = 'Request timed out. Please try again.';
                } else if (error.message) {
                    errorMessage = `Error: ${error.message}`;
                }

                UIUtils.showErrorMessage(errorMessage);
            });
        },

        /**
         * Refresh data via WebSocket
         */
        refreshData() {
            if (wsManager && wsManager.isConnected) {
                // Use WebSocket for faster refresh
                const success = WebSocketUtils.sendSecureMessage({ 'type': 'force_refresh' }) &&
                               WebSocketUtils.sendSecureMessage({ 'type': 'sync_state' }) &&
                               WebSocketUtils.sendSecureMessage({ 'type': 'get_game_status' }) &&
                               WebSocketUtils.sendSecureMessage({ 'type': 'get_live_stats' });

                if (success) {
                    UIUtils.showSuccessMessage('Data refreshed via WebSocket');
                } else {
                    UIUtils.showErrorMessage('Failed to refresh some data');
                }
            } else {
                // Try to reconnect WebSocket instead of page reload
                console.log('WebSocket not connected, attempting to reconnect...');
                WebSocketUtils.initWebSocket();
                UIUtils.showErrorMessage('WebSocket disconnected, attempting to reconnect...');
            }
        }
    };

    // Initialize WebSocket when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log('Initializing Admin Game Control Panel...');
        initializeWebSocket();
    });

    // Expose functions globally for template onclick handlers
    window.selectColor = GameControl.selectColor.bind(GameControl);
    window.submitResult = GameControl.submitResult.bind(GameControl);
    window.createTestRounds = GameControl.createTestRounds.bind(GameControl);
    window.refreshData = GameControl.refreshData.bind(GameControl);

})(); // Close the IIFE

