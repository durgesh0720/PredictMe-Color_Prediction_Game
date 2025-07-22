/**
 * Optimized WebSocket Manager
 * Prevents memory leaks and manages connections efficiently
 */
(function() {
    'use strict';
    
    function WebSocketManager(url, options) {
        this.url = url;
        this.options = Object.assign({
            maxReconnectAttempts: 5,
            reconnectDelay: 1000,
            heartbeatInterval: 30000,
            debug: false
        }, options);
        
        this.ws = null;
        this.reconnectAttempts = 0;
        this.reconnectTimer = null;
        this.heartbeatTimer = null;
        this.isConnecting = false;
        this.isDestroyed = false;
        
        // Event handlers
        this.handlers = {
            open: [],
            message: [],
            close: [],
            error: []
        };
        
        // Auto-connect
        this.connect();
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => this.destroy());
        window.addEventListener('pagehide', () => this.destroy());
    }
    
    WebSocketManager.prototype = {
        connect: function() {
            if (this.isDestroyed || this.isConnecting) return;
            
            this.isConnecting = true;
            this.clearTimers();
            
            try {
                this.ws = new WebSocket(this.url);
                this.setupEventHandlers();
                
                // Connection timeout
                const timeout = setTimeout(() => {
                    if (this.ws && this.ws.readyState === WebSocket.CONNECTING) {
                        this.ws.close(4000, 'Connection timeout');
                    }
                }, 10000);
                
                this.ws.addEventListener('open', () => clearTimeout(timeout), { once: true });
                
            } catch (error) {
                this.isConnecting = false;
                this.handleError(error);
            }
        },
        
        setupEventHandlers: function() {
            if (!this.ws) return;
            
            this.ws.onopen = (e) => {
                this.isConnecting = false;
                this.reconnectAttempts = 0;
                this.startHeartbeat();
                this.emit('open', e);
            };
            
            this.ws.onmessage = (e) => {
                this.emit('message', e);
            };
            
            this.ws.onclose = (e) => {
                this.isConnecting = false;
                this.clearTimers();
                this.emit('close', e);
                
                // Auto-reconnect unless destroyed or auth failed
                if (!this.isDestroyed && e.code !== 4001 && this.reconnectAttempts < this.options.maxReconnectAttempts) {
                    this.scheduleReconnect();
                }
            };
            
            this.ws.onerror = (e) => {
                this.isConnecting = false;
                this.emit('error', e);
            };
        },
        
        scheduleReconnect: function() {
            if (this.reconnectTimer) return;
            
            const delay = Math.min(
                this.options.reconnectDelay * Math.pow(2, this.reconnectAttempts) + Math.random() * 1000,
                30000
            );
            
            this.reconnectTimer = setTimeout(() => {
                this.reconnectTimer = null;
                this.reconnectAttempts++;
                this.connect();
            }, delay);
        },
        
        startHeartbeat: function() {
            if (!this.options.heartbeatInterval) return;
            
            this.heartbeatTimer = setInterval(() => {
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.send({ type: 'ping' });
                }
            }, this.options.heartbeatInterval);
        },
        
        send: function(data) {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
                return true;
            }
            return false;
        },
        
        on: function(event, handler) {
            if (this.handlers[event]) {
                this.handlers[event].push(handler);
            }
        },
        
        off: function(event, handler) {
            if (this.handlers[event]) {
                const index = this.handlers[event].indexOf(handler);
                if (index > -1) {
                    this.handlers[event].splice(index, 1);
                }
            }
        },
        
        emit: function(event, data) {
            if (this.handlers[event]) {
                this.handlers[event].forEach(handler => {
                    try {
                        handler(data);
                    } catch (error) {
                        console.error('WebSocket event handler error:', error);
                    }
                });
            }
        },
        
        clearTimers: function() {
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
            if (this.heartbeatTimer) {
                clearInterval(this.heartbeatTimer);
                this.heartbeatTimer = null;
            }
        },
        
        destroy: function() {
            if (this.isDestroyed) return;
            
            this.isDestroyed = true;
            this.clearTimers();
            
            if (this.ws) {
                this.ws.onopen = null;
                this.ws.onmessage = null;
                this.ws.onclose = null;
                this.ws.onerror = null;
                
                if (this.ws.readyState === WebSocket.OPEN) {
                    this.ws.close(1000, 'Client disconnect');
                }
                this.ws = null;
            }
            
            // Clear all handlers
            Object.keys(this.handlers).forEach(event => {
                this.handlers[event] = [];
            });
        },
        
        getState: function() {
            return {
                readyState: this.ws ? this.ws.readyState : WebSocket.CLOSED,
                reconnectAttempts: this.reconnectAttempts,
                isConnecting: this.isConnecting,
                isDestroyed: this.isDestroyed
            };
        }
    };
    
    // Export
    window.WebSocketManager = WebSocketManager;
    
    // Utility function for game WebSocket
    window.createGameWebSocket = function(roomName, handlers) {
        const url = window.WsConfig ? 
            window.WsConfig.gameUrl(roomName) : 
            (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws/game/' + (roomName || 'main') + '/';
        
        const config = window.WsConfig ? window.WsConfig.config : {
            reconnectDelay: 1000,
            heartbeat: 30000
        };
        
        const wsManager = new WebSocketManager(url, {
            maxReconnectAttempts: 5,
            reconnectDelay: config.reconnectDelay,
            heartbeatInterval: config.heartbeat
        });
        
        // Attach handlers
        if (handlers) {
            Object.keys(handlers).forEach(event => {
                if (typeof handlers[event] === 'function') {
                    wsManager.on(event, handlers[event]);
                }
            });
        }
        
        return wsManager;
    };
})();
