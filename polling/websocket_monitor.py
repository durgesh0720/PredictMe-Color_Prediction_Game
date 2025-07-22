"""
WebSocket connection monitoring utilities
"""

import logging
from django.core.cache import cache
from django.conf import settings
from typing import Dict, List, Optional
import time

logger = logging.getLogger(__name__)

class WebSocketConnectionMonitor:
    """Monitor and manage WebSocket connections"""
    
    def __init__(self):
        self.cache_timeout = 3600  # 1 hour
        
    def get_active_connections(self, ip_address: str) -> int:
        """Get number of active connections for an IP"""
        key = f"ws_active_connections:{ip_address}"
        return cache.get(key, 0)
    
    def get_connection_attempts(self, ip_address: str) -> int:
        """Get number of connection attempts in the last minute for an IP"""
        key = f"ws_connection_attempts:{ip_address}"
        return cache.get(key, 0)
    
    def get_all_connection_stats(self) -> Dict[str, int]:
        """Get overall connection statistics"""
        stats = {
            'total_active_connections': 0,
            'total_unique_ips': 0,
            'rate_limited_ips': 0,
            'max_connections_per_ip': 0
        }
        
        try:
            # This would require Redis-specific commands for full implementation
            # For now, provide basic functionality
            
            # Get development limits
            if getattr(settings, 'DEBUG', False):
                max_active = 200
                max_attempts = 100
            else:
                max_active = 50
                max_attempts = 30
            
            stats['max_active_connections_limit'] = max_active
            stats['max_attempts_per_minute_limit'] = max_attempts
            
        except Exception as e:
            logger.error(f"Error getting connection stats: {e}")
        
        return stats
    
    def is_ip_rate_limited(self, ip_address: str) -> bool:
        """Check if an IP is currently rate limited"""
        active = self.get_active_connections(ip_address)
        attempts = self.get_connection_attempts(ip_address)
        
        # Get limits based on environment
        if getattr(settings, 'DEBUG', False):
            max_active = 200
            max_attempts = 100
        else:
            max_active = 50
            max_attempts = 30
        
        return active >= max_active or attempts >= max_attempts
    
    def reset_ip_limits(self, ip_address: str) -> bool:
        """Reset rate limits for a specific IP"""
        try:
            active_key = f"ws_active_connections:{ip_address}"
            attempts_key = f"ws_connection_attempts:{ip_address}"
            
            cache.delete(active_key)
            cache.delete(attempts_key)
            
            logger.info(f"Reset WebSocket limits for IP: {ip_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting limits for IP {ip_address}: {e}")
            return False
    
    def cleanup_stale_connections(self) -> int:
        """Clean up stale connection counts"""
        cleaned = 0
        
        try:
            # This would require more sophisticated logic in production
            # For now, just log the action
            logger.info("WebSocket connection cleanup initiated")
            
            # In a full implementation, you would:
            # 1. Get all active connection keys
            # 2. Check if they're actually still active
            # 3. Remove stale entries
            
        except Exception as e:
            logger.error(f"Error during connection cleanup: {e}")
        
        return cleaned
    
    def get_connection_history(self, ip_address: str, hours: int = 1) -> List[Dict]:
        """Get connection history for an IP (if available)"""
        # This would require storing historical data
        # For now, return current status
        return [{
            'timestamp': time.time(),
            'active_connections': self.get_active_connections(ip_address),
            'connection_attempts': self.get_connection_attempts(ip_address),
            'is_rate_limited': self.is_ip_rate_limited(ip_address)
        }]
    
    def log_connection_event(self, event_type: str, ip_address: str, details: Dict = None):
        """Log a connection event for monitoring"""
        log_data = {
            'event_type': event_type,
            'ip_address': ip_address,
            'timestamp': time.time(),
            'active_connections': self.get_active_connections(ip_address),
            'connection_attempts': self.get_connection_attempts(ip_address)
        }
        
        if details:
            log_data.update(details)
        
        logger.info(f"WebSocket event: {event_type} for {ip_address}", extra=log_data)

class WebSocketHealthChecker:
    """Health checker for WebSocket system"""
    
    def __init__(self):
        self.monitor = WebSocketConnectionMonitor()
    
    def check_system_health(self) -> Dict[str, any]:
        """Check overall WebSocket system health"""
        health = {
            'status': 'healthy',
            'issues': [],
            'stats': {},
            'recommendations': []
        }
        
        try:
            # Get connection stats
            stats = self.monitor.get_all_connection_stats()
            health['stats'] = stats
            
            # Check for potential issues
            if stats.get('rate_limited_ips', 0) > 10:
                health['issues'].append('High number of rate-limited IPs')
                health['status'] = 'warning'
            
            # Check cache connectivity
            try:
                cache.set('ws_health_check', 'ok', 60)
                if cache.get('ws_health_check') != 'ok':
                    health['issues'].append('Cache connectivity issue')
                    health['status'] = 'error'
            except Exception as e:
                health['issues'].append(f'Cache error: {e}')
                health['status'] = 'error'
            
            # Provide recommendations
            if getattr(settings, 'DEBUG', False):
                health['recommendations'].append('Running in DEBUG mode - connection limits are relaxed')
            
            if not health['issues']:
                health['recommendations'].append('WebSocket system is operating normally')
            
        except Exception as e:
            health['status'] = 'error'
            health['issues'].append(f'Health check failed: {e}')
        
        return health
    
    def get_troubleshooting_info(self) -> Dict[str, any]:
        """Get troubleshooting information"""
        info = {
            'current_settings': {
                'debug_mode': getattr(settings, 'DEBUG', False),
                'cache_backend': str(cache.__class__),
                'channel_layer_backend': getattr(settings, 'CHANNEL_LAYERS', {}).get('default', {}).get('BACKEND', 'Unknown')
            },
            'common_issues': [
                'Rate limit exceeded: Too many connections from same IP',
                'Cache connectivity: Redis connection issues',
                'Stale connections: Old connection counts not cleaned up',
                'Origin validation: Invalid origin headers'
            ],
            'solutions': [
                'Use cleanup_websocket_connections management command',
                'Check Redis connectivity and configuration',
                'Verify ALLOWED_HOSTS and WS_ALLOWED_ORIGINS settings',
                'Monitor connection patterns for abuse'
            ]
        }
        
        return info

# Global instances
connection_monitor = WebSocketConnectionMonitor()
health_checker = WebSocketHealthChecker()
