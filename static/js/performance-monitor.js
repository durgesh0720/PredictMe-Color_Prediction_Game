/**
 * Performance Monitor for WebSocket Implementation
 * Lightweight monitoring for production use
 */
(function() {
    'use strict';
    
    // Only enable in development or when explicitly requested
    if (!window.location.host.includes('localhost') && !window.location.search.includes('debug=1')) {
        return;
    }
    
    const monitor = {
        startTime: performance.now(),
        metrics: {
            wsConnections: 0,
            wsReconnections: 0,
            wsErrors: 0,
            memoryLeaks: 0,
            messagesSent: 0,
            messagesReceived: 0
        },
        
        init: function() {
            this.monitorWebSocket();
            this.monitorMemory();
            this.monitorPerformance();
            
            // Report every 30 seconds in development
            setInterval(() => this.report(), 30000);
        },
        
        monitorWebSocket: function() {
            // Monitor WebSocket creation
            const originalWebSocket = window.WebSocket;
            window.WebSocket = function(url, protocols) {
                monitor.metrics.wsConnections++;
                const ws = new originalWebSocket(url, protocols);
                
                const originalSend = ws.send;
                ws.send = function(data) {
                    monitor.metrics.messagesSent++;
                    return originalSend.call(this, data);
                };
                
                ws.addEventListener('message', () => {
                    monitor.metrics.messagesReceived++;
                });
                
                ws.addEventListener('error', () => {
                    monitor.metrics.wsErrors++;
                });
                
                ws.addEventListener('close', (e) => {
                    if (e.code !== 1000) {
                        monitor.metrics.wsReconnections++;
                    }
                });
                
                return ws;
            };
        },
        
        monitorMemory: function() {
            if (!performance.memory) return;
            
            setInterval(() => {
                const memory = performance.memory;
                const used = memory.usedJSHeapSize;
                const total = memory.totalJSHeapSize;
                
                // Simple leak detection: if used memory keeps growing
                if (used > total * 0.9) {
                    monitor.metrics.memoryLeaks++;
                    console.warn('Potential memory leak detected');
                }
            }, 10000);
        },
        
        monitorPerformance: function() {
            // Monitor page load performance
            window.addEventListener('load', () => {
                setTimeout(() => {
                    const navigation = performance.getEntriesByType('navigation')[0];
                    if (navigation) {
                        console.log('Page Load Performance:', {
                            domContentLoaded: navigation.domContentLoadedEventEnd - navigation.domContentLoadedEventStart,
                            loadComplete: navigation.loadEventEnd - navigation.loadEventStart,
                            totalTime: navigation.loadEventEnd - navigation.fetchStart
                        });
                    }
                }, 1000);
            });
        },
        
        report: function() {
            const runtime = ((performance.now() - this.startTime) / 1000).toFixed(1);
            
            console.group('🔍 WebSocket Performance Report');
            console.log('Runtime:', runtime + 's');
            console.log('Metrics:', this.metrics);
            
            if (performance.memory) {
                const memory = performance.memory;
                console.log('Memory:', {
                    used: (memory.usedJSHeapSize / 1024 / 1024).toFixed(2) + 'MB',
                    total: (memory.totalJSHeapSize / 1024 / 1024).toFixed(2) + 'MB',
                    limit: (memory.jsHeapSizeLimit / 1024 / 1024).toFixed(2) + 'MB'
                });
            }
            
            // Performance warnings
            if (this.metrics.wsConnections > 10) {
                console.warn('⚠️ High WebSocket connection count:', this.metrics.wsConnections);
            }
            
            if (this.metrics.wsErrors > 5) {
                console.warn('⚠️ High WebSocket error count:', this.metrics.wsErrors);
            }
            
            if (this.metrics.memoryLeaks > 0) {
                console.warn('⚠️ Potential memory leaks detected:', this.metrics.memoryLeaks);
            }
            
            console.groupEnd();
        },
        
        getMetrics: function() {
            return {
                ...this.metrics,
                runtime: (performance.now() - this.startTime) / 1000,
                memory: performance.memory ? {
                    used: performance.memory.usedJSHeapSize,
                    total: performance.memory.totalJSHeapSize,
                    limit: performance.memory.jsHeapSizeLimit
                } : null
            };
        }
    };
    
    // Initialize monitoring
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => monitor.init());
    } else {
        monitor.init();
    }
    
    // Expose for debugging
    window.PerformanceMonitor = monitor;
    
    console.log('🔍 Performance monitoring enabled');
})();
