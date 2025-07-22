/**
 * WebSocket Manager for Admin Game Control
 * 
 * This module handles all WebSocket communication for the admin panel,
 * including connection management, message handling, and security validation.
 * 
 * @version 1.0.0
 * @author Admin Panel Team
 * @created 2024-01-19
 * 
 * Features:
 * - Secure WebSocket connection management
 * - Automatic reconnection with exponential backoff
 * - Message validation and rate limiting
 * - Connection health monitoring
 * - Error handling and recovery
 */

/**
 * WebSocket Manager Class
 * Handles all WebSocket communication with enhanced security and reliability
 */
class WebSocketManager {
    /**
     * Initialize WebSocket Manager
     * @param {Object} config - Configuration object
     * @param {Object} utils - Utility functions (ValidationUtils, UIUtils)
     */
    constructor(config, utils) {
        this.config = config;
        this.validationUtils = utils.ValidationUtils;
        this.uiUtils = utils.UIUtils;
        
        // Connection state
        this.socket = null;
        this.reconnectAttempts = 0;
        this.reconnectDelay = config.WEBSOCKET_RECONNECT_DELAY;
        this.isConnected = false;
        this.isPageVisible = true;
        
        // Health monitoring
        this.heartbeatInterval = null;
        this.lastPongReceived = Date.now();
        
        // Rate limiting
        this.lastMessageTime = 0;
        this.messageCount = 0;
        
        // Event handlers
        this.messageHandlers = new Map();
        this.connectionHandlers = new Set();
        
        this.setupEventListeners();
    }
    
    /**
     * Setup page event listeners
     * @private
     */
    setupEventListeners() {
        // Page visibility changes
        document.addEventListener('visibilitychange', () => {
            this.isPageVisible = !document.hidden;
            
            if (this.isPageVisible) {
                console.log('Page became visible');
                if (!this.isConnected) {
                    this.connect();
                }
                this.startHeartbeat();
            } else {
                console.log('Page became hidden, conserving resources');
                this.stopHeartbeat();
            }
        });
        
        // Network status changes
        window.addEventListener('online', () => {
            console.log('Network connection restored');
            if (this.isPageVisible && !this.isConnected) {
                setTimeout(() => this.connect(), 1000);
            }
        });
        
        window.addEventListener('offline', () => {
            console.log('Network connection lost');
            this.updateConnectionStatus(false);
            this.uiUtils.showErrorMessage('Network connection lost. Will reconnect when online.');
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }
    
    /**
     * Connect to WebSocket server
     * @public
     */
    connect() {
        if (this.socket && this.socket.readyState === WebSocket.CONNECTING) {
            console.log('WebSocket connection already in progress');
            return;
        }
        
        // Use optimized WebSocket configuration
        const wsUrl = window.WsConfig ?
            window.WsConfig.adminUrl('game-control') :
            `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws/control-panel/game-control/`;
        
        try {
            this.socket = new WebSocket(wsUrl);
            
            // Set connection timeout
            const connectionTimeout = setTimeout(() => {
                if (this.socket.readyState === WebSocket.CONNECTING) {
                    console.warn('WebSocket connection timeout');
                    this.socket.close();
                }
            }, 10000);
            
            this.socket.onopen = (event) => {
                clearTimeout(connectionTimeout);
                this.handleOpen(event);
            };
            
            this.socket.onmessage = (event) => {
                this.handleMessage(event);
            };
            
            this.socket.onclose = (event) => {
                clearTimeout(connectionTimeout);
                this.handleClose(event);
            };
            
            this.socket.onerror = (error) => {
                clearTimeout(connectionTimeout);
                this.handleError(error);
            };
            
        } catch (error) {
            console.error('Failed to create WebSocket connection:', error);
            this.updateConnectionStatus(false);
            
            if (this.isPageVisible) {
                setTimeout(() => this.connect(), this.config.WEBSOCKET_RECONNECT_DELAY);
            }
        }
    }
    
    /**
     * Handle WebSocket open event
     * @private
     * @param {Event} event - Open event
     */
    handleOpen(event) {
        console.log('Admin WebSocket connected');
        
        this.isConnected = true;
        this.reconnectAttempts = 0;
        this.reconnectDelay = this.config.WEBSOCKET_RECONNECT_DELAY;
        
        this.updateConnectionStatus(true);
        this.removeReconnectionStatus();
        
        // Send initial data request
        this.sendMessage({ type: 'get_game_status' });
        
        // Start periodic tasks
        setTimeout(() => {
            this.sendMessage({ type: 'sync_state' });
            this.sendMessage({ type: 'get_live_stats' });
        }, 1000);
        
        this.startHeartbeat();
        
        // Notify connection handlers
        this.connectionHandlers.forEach(handler => {
            try {
                handler(true);
            } catch (error) {
                console.error('Error in connection handler:', error);
            }
        });
        
        if (this.reconnectAttempts > 0) {
            this.uiUtils.showSuccessMessage('WebSocket reconnected successfully!');
        }
    }
    
    /**
     * Handle WebSocket message event
     * @private
     * @param {MessageEvent} event - Message event
     */
    handleMessage(event) {
        try {
            // Validate message size
            if (event.data.length > this.config.MESSAGE_SIZE_LIMIT) {
                console.error('WebSocket message too large, ignoring');
                return;
            }
            
            const data = JSON.parse(event.data);
            
            // Basic message validation
            if (!data || typeof data !== 'object' || !data.type) {
                console.error('Invalid WebSocket message format:', data);
                return;
            }
            
            // Skip timestamp validation for server-originated messages
            // Only validate timestamps for client-originated messages to prevent replay attacks
            if (data.timestamp && data.client_id && !this.validationUtils.validateTimestamp(data.timestamp, 300000)) {
                console.warn('Message timestamp too old, ignoring:', data.type);
                return;
            }
            
            // Rate limiting check
            if (!this.checkRateLimit()) {
                console.warn('Message rate limit exceeded, ignoring:', data.type);
                return;
            }
            
            // Validate message type
            const validMessageTypes = [
                'comprehensive_game_status', 'live_betting_stats', 'timer_info', 'timer_sync', 'timer_update',
                'color_selected', 'color_selected_event', 'color_selection_confirmed', 'round_ended',
                'new_round_started', 'state_synced', 'bet_placed_update', 'error', 'pong'
            ];
            
            if (!validMessageTypes.includes(data.type)) {
                console.warn('Unknown or invalid message type:', data.type);
                return;
            }
            
            // Handle special message types
            if (data.type === 'pong') {
                this.lastPongReceived = Date.now();
                return;
            }
            
            if (data.type === 'error') {
                console.error('WebSocket error:', data.message);
                if (data.message && typeof data.message === 'string') {
                    this.uiUtils.showErrorMessage(this.validationUtils.escapeHtml(data.message));
                }
                return;
            }
            
            // Dispatch to registered handlers
            const handler = this.messageHandlers.get(data.type);
            if (handler) {
                try {
                    handler(data);
                } catch (error) {
                    console.error(`Error in message handler for ${data.type}:`, error);
                }
            } else {
                console.log('No handler registered for message type:', data.type);
            }
            
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
            this.uiUtils.showErrorMessage('Error processing server message');
        }
    }
    
    /**
     * Handle WebSocket close event
     * @private
     * @param {CloseEvent} event - Close event
     */
    handleClose(event) {
        console.log('Admin WebSocket disconnected:', event.code, event.reason);
        
        this.isConnected = false;
        this.updateConnectionStatus(false);
        this.stopHeartbeat();
        
        // Notify connection handlers
        this.connectionHandlers.forEach(handler => {
            try {
                handler(false);
            } catch (error) {
                console.error('Error in connection handler:', error);
            }
        });
        
        // Show reconnection status for unexpected disconnections
        if (event.code !== 1000 && event.code !== 1001 && this.isPageVisible) {
            this.showReconnectionStatus();
        }
        
        // Attempt reconnection with exponential backoff
        if (this.reconnectAttempts < this.config.WEBSOCKET_RECONNECT_ATTEMPTS && this.isPageVisible) {
            const delay = Math.min(this.reconnectDelay, this.config.MAX_RECONNECT_DELAY);
            
            setTimeout(() => {
                this.reconnectAttempts++;
                this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.config.MAX_RECONNECT_DELAY);
                console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.config.WEBSOCKET_RECONNECT_ATTEMPTS})...`);
                this.connect();
            }, delay);
        } else if (this.reconnectAttempts >= this.config.WEBSOCKET_RECONNECT_ATTEMPTS) {
            console.error('Max reconnection attempts reached. Will retry in 2 minutes...');
            setTimeout(() => {
                if (this.isPageVisible) {
                    this.reconnectAttempts = 0;
                    this.reconnectDelay = this.config.WEBSOCKET_RECONNECT_DELAY;
                    this.connect();
                }
            }, this.config.FALLBACK_RECONNECT_INTERVAL);
        }
    }
    
    /**
     * Handle WebSocket error event
     * @private
     * @param {Event} error - Error event
     */
    handleError(error) {
        console.error('WebSocket error:', error);
        this.updateConnectionStatus(false);
    }
    
    /**
     * Send message through WebSocket with validation
     * @public
     * @param {Object} message - Message to send
     * @returns {boolean} - True if message was sent successfully
     */
    sendMessage(message) {
        if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
            console.warn('WebSocket not connected. Message not sent:', message);
            return false;
        }
        
        // Validate message structure
        if (!message.type || !this.validationUtils.validateInput(message.type, 'messageType')) {
            console.error('Invalid message type:', message.type);
            return false;
        }
        
        // Add security context
        const secureMessage = {
            ...message,
            timestamp: Date.now(),
            client_id: this.generateClientId()
        };
        
        try {
            const messageStr = JSON.stringify(secureMessage);
            if (messageStr.length > this.config.MESSAGE_SIZE_LIMIT) {
                console.error('Message too large:', messageStr.length);
                return false;
            }

            this.socket.send(messageStr);
            return true;
        } catch (error) {
            console.error('Failed to send WebSocket message:', error);
            return false;
        }
    }

    /**
     * Check rate limiting for incoming messages
     * @private
     * @returns {boolean} - True if within rate limits
     */
    checkRateLimit() {
        const now = Date.now();
        if (!this.lastMessageTime) this.lastMessageTime = 0;

        // More lenient rate limiting for admin panel - allow up to 100 messages per second
        // This is necessary for real-time updates like timer sync
        if (now - this.lastMessageTime < 10) { // Max 100 messages per second
            return false;
        }
        this.lastMessageTime = now;
        return true;
    }

    /**
     * Start heartbeat monitoring
     * @private
     */
    startHeartbeat() {
        if (this.heartbeatInterval) clearInterval(this.heartbeatInterval);

        this.heartbeatInterval = setInterval(() => {
            if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                this.sendMessage({ type: 'ping' });

                // Check if we received a pong recently
                if (Date.now() - this.lastPongReceived > 60000) { // 1 minute without pong
                    console.warn('No pong received for 1 minute, connection may be stale');
                    this.socket.close();
                }
            }
        }, 15000); // Every 15 seconds
    }

    /**
     * Stop heartbeat monitoring
     * @private
     */
    stopHeartbeat() {
        if (this.heartbeatInterval) {
            clearInterval(this.heartbeatInterval);
            this.heartbeatInterval = null;
        }
    }

    /**
     * Update connection status indicator
     * @private
     * @param {boolean} connected - Connection status
     */
    updateConnectionStatus(connected) {
        const indicator = document.querySelector('.live-indicator .live-dot');
        const text = document.querySelector('.live-indicator');

        if (indicator && text) {
            if (connected) {
                indicator.style.backgroundColor = '#28a745';
                indicator.style.animation = 'pulse 2s infinite';
                text.innerHTML = '<div class="live-dot"></div>LIVE GAME CONTROL (Connected)';
                text.style.color = '#28a745';
            } else {
                indicator.style.backgroundColor = '#dc3545';
                indicator.style.animation = 'none';
                text.innerHTML = '<div class="live-dot"></div>LIVE GAME CONTROL (Reconnecting...)';
                text.style.color = '#dc3545';
            }
        }
    }

    /**
     * Show reconnection status message
     * @private
     */
    showReconnectionStatus() {
        const statusDiv = document.createElement('div');
        statusDiv.className = 'alert alert-warning';
        statusDiv.id = 'reconnection-status';
        statusDiv.innerHTML = `
            <strong>Connection Lost!</strong>
            Attempting to reconnect WebSocket connection...
            <button class="btn btn-sm btn-outline-warning ms-2" onclick="window.wsManager.connect()">
                <i class="fas fa-sync-alt"></i> Retry Now
            </button>
        `;

        this.removeReconnectionStatus();

        const container = document.querySelector('.container-fluid');
        if (container) {
            container.insertBefore(statusDiv, container.firstChild);
        }

        // Auto-remove after successful reconnection
        setTimeout(() => {
            if (this.isConnected) {
                this.removeReconnectionStatus();
            }
        }, 5000);
    }

    /**
     * Remove reconnection status message
     * @private
     */
    removeReconnectionStatus() {
        const existing = document.getElementById('reconnection-status');
        if (existing) existing.remove();
    }

    /**
     * Generate unique client ID
     * @private
     * @returns {string} - Unique client ID
     */
    generateClientId() {
        return 'admin_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    /**
     * Register message handler
     * @public
     * @param {string} messageType - Message type to handle
     * @param {Function} handler - Handler function
     */
    onMessage(messageType, handler) {
        this.messageHandlers.set(messageType, handler);
    }

    /**
     * Register connection handler
     * @public
     * @param {Function} handler - Handler function
     */
    onConnection(handler) {
        this.connectionHandlers.add(handler);
    }

    /**
     * Cleanup resources
     * @public
     */
    cleanup() {
        console.log('Cleaning up WebSocket resources');

        if (this.socket) {
            this.socket.close(1000, 'Page unloading');
            this.socket = null;
        }

        this.stopHeartbeat();
        this.messageHandlers.clear();
        this.connectionHandlers.clear();
    }
}

// Export for use in other modules
window.WebSocketManager = WebSocketManager;
