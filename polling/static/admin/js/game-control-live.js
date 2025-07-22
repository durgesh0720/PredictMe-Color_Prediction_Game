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
            if (!window.wsManager || !window.wsManager.isConnected) {
                console.warn('WebSocket not connected. Message not sent:', message);
                return false;
            }

            return window.wsManager.sendMessage(message);
        },

        /**
         * Initialize WebSocket connection
         */
        initWebSocket() {
            if (window.wsManager) {
                window.wsManager.connect();
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

        // Register message handlers with debug logging
        const registerMessageHandler = (type, handler) => {
            const wrappedHandler = (data) => {
                if (window.DebugPanel) {
                    window.DebugPanel.addMessage('RECV', `${type}: ${JSON.stringify(data).substring(0, 100)}...`);
                }
                return handler(data);
            };
            wsManager.onMessage(type, wrappedHandler);
        };

        registerMessageHandler('comprehensive_game_status', handleGameStatusMessage);
        registerMessageHandler('live_betting_stats', handleLiveBettingStats);
        registerMessageHandler('bet_placed_update', handleBetPlacedUpdate);
        registerMessageHandler('timer_info', handleTimerInfo);
        registerMessageHandler('timer_sync', handleTimerSync);
        registerMessageHandler('timer_update', handleTimerUpdate);
        registerMessageHandler('color_selected', handleColorSelected);
        registerMessageHandler('color_selection_confirmed', handleColorSelectionConfirmed);
        registerMessageHandler('round_ended', handleRoundEnded);
        registerMessageHandler('new_round_started', handleNewRoundStarted);
        registerMessageHandler('state_synced', handleStateSynced);

        // Register connection event handlers
        wsManager.onConnection((isConnected) => {
            const connectionStatus = document.getElementById('connection-status');

            if (isConnected) {
                console.log('Admin WebSocket connected - requesting initial data');

                // Update connection status indicator
                if (connectionStatus) {
                    connectionStatus.textContent = 'Connected';
                    connectionStatus.style.background = '#28a745';
                }

                // Request initial game state and statistics
                setTimeout(() => {
                    WebSocketUtils.sendSecureMessage({ 'type': 'get_game_status' });
                    WebSocketUtils.sendSecureMessage({ 'type': 'get_live_stats' });
                    WebSocketUtils.sendSecureMessage({ 'type': 'sync_state' });

                    UIUtils.showSuccessMessage('Connected to live game data');
                }, 500); // Small delay to ensure connection is fully established
            } else {
                console.log('Admin WebSocket disconnected');

                // Update connection status indicator
                if (connectionStatus) {
                    connectionStatus.textContent = 'Disconnected';
                    connectionStatus.style.background = '#dc3545';
                }

                UIUtils.showErrorMessage('Lost connection to live game data');
            }
        });

        // Connect to WebSocket
        wsManager.connect();

        // Store globally for access from other functions
        window.wsManager = wsManager;

        // Add debug message logging to WebSocket events
        const originalSendMessage = wsManager.sendMessage;
        if (originalSendMessage) {
            wsManager.sendMessage = function(message) {
                if (window.DebugPanel) {
                    window.DebugPanel.addMessage('SEND', `${message.type || 'unknown'}: ${JSON.stringify(message).substring(0, 100)}...`);
                }
                return originalSendMessage.call(this, message);
            };
        }

        // Set up periodic stats refresh to ensure data stays current
        setInterval(() => {
            if (window.wsManager && window.wsManager.isConnected) {
                console.log('Periodic stats refresh');
                WebSocketUtils.sendSecureMessage({ 'type': 'get_live_stats' });
            }
        }, 5000); // Refresh every 5 seconds
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

        // Add debug logging
        if (window.DebugPanel) {
            window.DebugPanel.addMessage('STATS', `Updated betting stats for ${Object.keys(data.stats).length} colors`);
        }

        // Update betting statistics display for each color
        const colors = ['red', 'green', 'violet', 'blue'];

        colors.forEach(color => {
            const colorStats = data.stats[color] || { amount: 0, count: 0, users: 0 };
            console.log(`Updating ${color} stats:`, colorStats);

            // Update color statistics in round cards
            document.querySelectorAll(`[data-round-id]`).forEach(roundCard => {
                const colorStatsElement = roundCard.querySelector(`.color-stats-${color}`);
                const colorAmountElement = roundCard.querySelector(`.color-amount-${color}`);
                const colorCountElement = roundCard.querySelector(`.color-count-${color}`);
                const colorUsersElement = roundCard.querySelector(`.color-users-${color}`);

                if (colorAmountElement) {
                    const oldValue = colorAmountElement.textContent;
                    colorAmountElement.textContent = `₹${colorStats.amount}`;
                    console.log(`Updated ${color} amount: ${oldValue} -> ₹${colorStats.amount}`);

                    // Add visual feedback for updates
                    colorAmountElement.classList.add('stats-updated');
                    setTimeout(() => colorAmountElement.classList.remove('stats-updated'), 500);
                }

                if (colorCountElement) {
                    const oldValue = colorCountElement.textContent;
                    colorCountElement.textContent = `${colorStats.count} bets`;
                    console.log(`Updated ${color} count: ${oldValue} -> ${colorStats.count} bets`);

                    // Add visual feedback for updates
                    colorCountElement.classList.add('stats-updated');
                    setTimeout(() => colorCountElement.classList.remove('stats-updated'), 500);
                }

                if (colorUsersElement) {
                    const oldValue = colorUsersElement.textContent;
                    colorUsersElement.textContent = `${colorStats.users} players`;
                    console.log(`Updated ${color} users: ${oldValue} -> ${colorStats.users} players`);

                    // Add visual feedback for updates
                    colorUsersElement.classList.add('stats-updated');
                    setTimeout(() => colorUsersElement.classList.remove('stats-updated'), 500);
                }

                if (colorStatsElement) {
                    colorStatsElement.textContent = `₹${colorStats.amount} (${colorStats.count} bets)`;
                }
            });

            // Update global color statistics if elements exist
            const globalColorAmount = document.getElementById(`${color}-total-amount`);
            const globalColorCount = document.getElementById(`${color}-total-count`);
            const globalColorUsers = document.getElementById(`${color}-total-users`);
            const globalColorPercentage = document.getElementById(`${color}-percentage`);

            if (globalColorAmount) {
                globalColorAmount.textContent = `₹${colorStats.amount}`;
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

        console.log(`Total stats - Amount: ₹${totalAmount}, Count: ${totalCount}, Users: ${totalUsers}`);

        const totalAmountElement = document.getElementById('total-betting-amount');
        const totalCountElement = document.getElementById('total-betting-count');
        const totalUsersElement = document.getElementById('total-betting-users');
        const activeRoundsElement = document.getElementById('active-rounds-count');

        if (totalAmountElement) {
            const oldValue = totalAmountElement.textContent;
            totalAmountElement.textContent = `₹${totalAmount}`;
            console.log(`Updated total amount: ${oldValue} -> ₹${totalAmount}`);
            totalAmountElement.classList.add('stats-updated');
            setTimeout(() => totalAmountElement.classList.remove('stats-updated'), 500);
        }

        if (totalCountElement) {
            const oldValue = totalCountElement.textContent;
            totalCountElement.textContent = totalCount;
            console.log(`Updated total count: ${oldValue} -> ${totalCount}`);
            totalCountElement.classList.add('stats-updated');
            setTimeout(() => totalCountElement.classList.remove('stats-updated'), 500);
        }

        if (totalUsersElement) {
            const oldValue = totalUsersElement.textContent;
            totalUsersElement.textContent = totalUsers;
            console.log(`Updated total users: ${oldValue} -> ${totalUsers}`);
            totalUsersElement.classList.add('stats-updated');
            setTimeout(() => totalUsersElement.classList.remove('stats-updated'), 500);
        }

        if (activeRoundsElement) {
            const oldValue = activeRoundsElement.textContent;
            activeRoundsElement.textContent = data.active_rounds_count || 0;
            console.log(`Updated active rounds: ${oldValue} -> ${data.active_rounds_count || 0}`);
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

        // Add debug logging
        if (window.DebugPanel) {
            window.DebugPanel.addMessage('BET', `${data.username} bet ₹${data.amount} on ${data.color || data.number}`);
        }

        // Show real-time bet notification
        const message = `${ValidationUtils.escapeHtml(data.username)} bet ₹${data.amount} on ${ValidationUtils.escapeHtml(data.color || data.number)}`;
        UIUtils.showSuccessMessage(message);

        // Update round-specific betting info if available
        const roundCard = document.querySelector(`[data-round-id="${CSS.escape(data.round_id)}"]`);
        if (roundCard) {
            // Add visual indicator for new bet
            roundCard.classList.add('new-bet-flash');
            setTimeout(() => {
                roundCard.classList.remove('new-bet-flash');
            }, 1000);

            // Immediately update the color-specific betting display
            if (data.color) {
                const colorAmountElement = roundCard.querySelector(`.color-amount-${data.color}`);
                const colorCountElement = roundCard.querySelector(`.color-count-${data.color}`);

                if (colorAmountElement) {
                    // Extract current amount and add new bet amount
                    const currentAmountText = colorAmountElement.textContent.replace('₹', '');
                    const currentAmount = parseInt(currentAmountText) || 0;
                    const newAmount = currentAmount + data.amount;
                    colorAmountElement.textContent = `₹${newAmount}`;
                }

                if (colorCountElement) {
                    // Extract current count and increment
                    const currentCountText = colorCountElement.textContent.replace(' bets', '');
                    const currentCount = parseInt(currentCountText) || 0;
                    const newCount = currentCount + 1;
                    colorCountElement.textContent = `${newCount} bets`;
                }
            }

            // Update total bet count indicator if it exists
            const betCountElement = roundCard.querySelector('.bet-count');
            if (betCountElement) {
                const currentCount = parseInt(betCountElement.textContent) || 0;
                betCountElement.textContent = currentCount + 1;
            }
        }

        // Request immediate stats refresh to ensure accuracy
        if (window.wsManager && window.wsManager.isConnected) {
            WebSocketUtils.sendSecureMessage({ 'type': 'get_live_stats' });
        }
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

        // Update round status to show it's ended
        const statusElements = document.querySelectorAll('.round-status');
        statusElements.forEach(el => {
            el.textContent = 'Round Ended';
            el.className = 'round-status round-ended';
        });

        // Show result if available
        if (data.result_color && data.result_number) {
            UIUtils.showSuccessMessage(`Round ended: ${data.result_color.toUpperCase()} ${data.result_number}`);
        } else {
            UIUtils.showInfoMessage('Round ended - waiting for results');
        }

        // Request updated stats to show final betting results
        if (window.wsManager && window.wsManager.isConnected) {
            WebSocketUtils.sendSecureMessage({ 'type': 'get_game_status' });
            WebSocketUtils.sendSecureMessage({ 'type': 'get_live_stats' });
        }
    }

    function handleNewRoundStarted(data) {
        console.log('New round started:', data);

        // Clear current betting statistics for the new round
        clearBettingStats();

        // Request fresh data from server
        if (window.wsManager && window.wsManager.isConnected) {
            // Request updated game status and live stats
            WebSocketUtils.sendSecureMessage({ 'type': 'get_game_status' });
            WebSocketUtils.sendSecureMessage({ 'type': 'get_live_stats' });
            WebSocketUtils.sendSecureMessage({ 'type': 'sync_state' });
        }

        // Show notification to admin
        UIUtils.showSuccessMessage(`New round started: ${data.period_id || data.round_id}`);

        // Update UI to reflect new round state
        updateRoundDisplay(data);
    }

    function handleStateSynced(data) {
        console.log('State synchronized:', data);
        UIUtils.showSuccessMessage('State synchronized with server');
    }

    /**
     * Clear betting statistics display for new round
     */
    function clearBettingStats() {
        console.log('Clearing betting statistics for new round');

        // Reset color statistics to zero
        const colors = ['red', 'green', 'violet', 'blue'];

        colors.forEach(color => {
            // Update all round cards
            document.querySelectorAll(`[data-round-id]`).forEach(roundCard => {
                const colorAmountElement = roundCard.querySelector(`.color-amount-${color}`);
                const colorCountElement = roundCard.querySelector(`.color-count-${color}`);
                const colorUsersElement = roundCard.querySelector(`.color-users-${color}`);
                const colorStatsElement = roundCard.querySelector(`.color-stats-${color}`);

                if (colorAmountElement) {
                    colorAmountElement.textContent = '₹0';
                }
                if (colorCountElement) {
                    colorCountElement.textContent = '0';
                }
                if (colorUsersElement) {
                    colorUsersElement.textContent = '0';
                }
                if (colorStatsElement) {
                    colorStatsElement.textContent = '₹0 (0 bets)';
                }
            });

            // Update main betting stats display
            const mainColorElement = document.querySelector(`.color-bet.${color}`);
            if (mainColorElement) {
                const amountEl = mainColorElement.querySelector('.bet-amount');
                const countEl = mainColorElement.querySelector('.bet-count');
                const usersEl = mainColorElement.querySelector('.bet-users');

                if (amountEl) amountEl.textContent = '₹0';
                if (countEl) countEl.textContent = '0 bets';
                if (usersEl) usersEl.textContent = '0 players';
            }
        });

        // Reset total statistics
        const totalAmountEl = document.getElementById('total-amount');
        const totalPlayersEl = document.getElementById('total-players');

        if (totalAmountEl) totalAmountEl.textContent = '₹0';
        if (totalPlayersEl) totalPlayersEl.textContent = '0';

        // Reset round summary if it exists
        const summaryElements = document.querySelectorAll('.summary-value');
        summaryElements.forEach((el, index) => {
            if (index === 0) el.textContent = '0'; // Total bets
            else if (index === 1) el.textContent = '₹0'; // Total amount
            else if (index === 2) el.textContent = '0'; // Players
        });
    }

    /**
     * Update round display information
     */
    function updateRoundDisplay(data) {
        console.log('Updating round display:', data);

        // Update round ID displays
        if (data.round_id || data.period_id) {
            const roundIdElements = document.querySelectorAll('.round-id, .period-id');
            roundIdElements.forEach(el => {
                el.textContent = data.period_id || data.round_id;
            });
        }

        // Update round status indicators
        const statusElements = document.querySelectorAll('.round-status');
        statusElements.forEach(el => {
            el.textContent = 'Betting Open';
            el.className = 'round-status betting-open';
        });

        // Update timer displays if available
        if (data.time_remaining) {
            const timerElements = document.querySelectorAll('.timer-display, .time-remaining');
            timerElements.forEach(el => {
                el.textContent = `${data.time_remaining}s`;
            });
        }
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
            if (window.wsManager && window.wsManager.isConnected) {
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

        // Update JS status indicator
        const jsStatus = document.getElementById('js-status');
        if (jsStatus) {
            jsStatus.textContent = 'JS Loaded';
            jsStatus.style.background = '#28a745';
            jsStatus.style.color = 'white';
        }

        // Initialize debug panel first
        if (window.DebugPanel) {
            window.DebugPanel.addMessage('INIT', 'Admin panel initialized');
        }

        // Initialize WebSocket
        try {
            initializeWebSocket();
            if (jsStatus) {
                jsStatus.textContent = 'JS Ready';
            }
        } catch (error) {
            console.error('Error initializing WebSocket:', error);
            if (jsStatus) {
                jsStatus.textContent = 'JS Error';
                jsStatus.style.background = '#dc3545';
            }
        }

        // Run connection test after a short delay
        setTimeout(() => {
            if (window.DebugPanel) {
                // Test WebSocket connection after 3 seconds
                setTimeout(() => {
                    if (window.wsManager && window.wsManager.isConnected) {
                        window.DebugPanel.addMessage('TEST', 'Auto-testing WebSocket connection...');
                        WebSocketUtils.sendSecureMessage({ 'type': 'get_live_stats' });
                        window.DebugPanel.addMessage('SUCCESS', 'WebSocket connection test completed');
                    } else {
                        window.DebugPanel.addMessage('ERROR', 'WebSocket connection failed - check network and authentication');
                    }
                }, 3000);
            }
        }, 1000);
    });

    // Debug functionality
    window.DebugPanel = {
        messages: [],
        maxMessages: 50,

        addMessage(type, message) {
            const timestamp = new Date().toLocaleTimeString();
            this.messages.unshift(`[${timestamp}] ${type}: ${message}`);
            if (this.messages.length > this.maxMessages) {
                this.messages.pop();
            }
            this.updateDisplay();
        },

        updateDisplay() {
            const debugMessages = document.getElementById('debug-messages');
            if (debugMessages) {
                debugMessages.innerHTML = this.messages.join('<br>') || 'No messages yet...';
            }
        },

        updateStatus(status) {
            const debugStatus = document.getElementById('debug-ws-status');
            if (debugStatus) {
                debugStatus.innerHTML = status;
            }
        },

        clear() {
            this.messages = [];
            this.updateDisplay();
        }
    };

    // Debug message logging will be added after wsManager is created

    // Global debug functions
    window.toggleDebugPanel = function() {
        const panel = document.getElementById('debug-panel');
        if (panel) {
            panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        }
    };

    window.clearDebugMessages = function() {
        window.DebugPanel.clear();
    };

    window.testWebSocketConnection = function() {
        if (window.wsManager && window.wsManager.isConnected) {
            window.DebugPanel.addMessage('TEST', 'Sending test message...');
            WebSocketUtils.sendSecureMessage({ 'type': 'ping' });
        } else {
            window.DebugPanel.addMessage('ERROR', 'WebSocket not connected');
        }
    };

    // Update debug status when connection changes
    setInterval(() => {
        if (window.wsManager && window.DebugPanel) {
            const status = window.wsManager.isConnected ?
                `Connected (${window.wsManager.socket?.readyState})` :
                `Disconnected (attempts: ${window.wsManager.reconnectAttempts})`;
            window.DebugPanel.updateStatus(status);
        }
    }, 1000);

    // Expose functions globally for template onclick handlers
    window.selectColor = GameControl.selectColor.bind(GameControl);
    window.submitResult = GameControl.submitResult.bind(GameControl);
    window.createTestRounds = GameControl.createTestRounds.bind(GameControl);
    window.refreshData = GameControl.refreshData.bind(GameControl);

})(); // Close the IIFE

