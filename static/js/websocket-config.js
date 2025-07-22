/**
 * Lightweight WebSocket Configuration Manager
 * Optimized for minimal overhead and maximum performance
 */
(function() {
    'use strict';
    
    // Cache DOM queries and environment detection
    const host = window.location.host;
    const isHttps = window.location.protocol === 'https:';
    const isNgrok = host.includes('ngrok');
    const isLocal = host.includes('localhost') || host.includes('127.0.0.1');
    
    // Optimized configuration based on environment
    const config = isNgrok ? {
        protocol: 'wss:',
        reconnectDelay: 2000,
        timeout: 15000,
        heartbeat: 25000
    } : isLocal ? {
        protocol: isHttps ? 'wss:' : 'ws:',
        reconnectDelay: 500,
        timeout: 5000,
        heartbeat: 30000
    } : {
        protocol: isHttps ? 'wss:' : 'ws:',
        reconnectDelay: 1000,
        timeout: 10000,
        heartbeat: 30000
    };
    
    /**
     * Lightweight WebSocket URL builder
     * @param {string} path - WebSocket path
     * @returns {string} Complete WebSocket URL
     */
    function buildWsUrl(path) {
        return config.protocol + '//' + host + path;
    }
    
    /**
     * Enhanced WebSocket creator with minimal overhead
     * @param {string} url - WebSocket URL
     * @param {Object} handlers - Event handlers {onOpen, onMessage, onClose, onError}
     * @returns {WebSocket} Enhanced WebSocket instance
     */
    function createWebSocket(url, handlers) {
        const ws = new WebSocket(url);
        let timeoutId;
        
        // Connection timeout
        timeoutId = setTimeout(() => {
            if (ws.readyState === WebSocket.CONNECTING) {
                ws.close(4000, 'Timeout');
            }
        }, config.timeout);
        
        // Optimized event handlers
        ws.onopen = function(e) {
            clearTimeout(timeoutId);
            handlers.onOpen && handlers.onOpen(e);
        };
        
        ws.onmessage = handlers.onMessage || null;
        
        ws.onclose = function(e) {
            clearTimeout(timeoutId);
            handlers.onClose && handlers.onClose(e);
        };
        
        ws.onerror = function(e) {
            clearTimeout(timeoutId);
            handlers.onError && handlers.onError(e);
        };
        
        return ws;
    }
    
    // Expose minimal API
    window.WsConfig = {
        // URL builders
        gameUrl: function(room) { return buildWsUrl('/ws/game/' + (room || 'main') + '/'); },
        adminUrl: function(endpoint) { return buildWsUrl('/ws/control-panel/' + (endpoint || 'game-control') + '/'); },
        dashboardUrl: function() { return buildWsUrl('/ws/control-panel/dashboard/'); },
        
        // WebSocket creator
        create: createWebSocket,
        
        // Configuration access
        config: config,
        
        // Environment flags
        isNgrok: isNgrok,
        isLocal: isLocal
    };
    
    // Conditional debug info (only in development)
    if (isLocal && console.debug) {
        console.debug('WsConfig loaded:', {
            env: isNgrok ? 'ngrok' : isLocal ? 'local' : 'prod',
            protocol: config.protocol,
            host: host
        });
    }
})();
