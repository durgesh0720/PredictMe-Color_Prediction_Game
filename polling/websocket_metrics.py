"""
WebSocket connection metrics and monitoring
"""
import time
import logging
from collections import defaultdict, deque
from typing import Dict, Any
import asyncio

logger = logging.getLogger(__name__)

class WebSocketMetrics:
    """Collect and track WebSocket connection metrics"""
    
    def __init__(self):
        # Connection metrics
        self.active_connections = 0
        self.total_connections = 0
        self.total_disconnections = 0
        self.connection_errors = defaultdict(int)
        
        # Message metrics
        self.messages_sent = 0
        self.messages_received = 0
        self.message_errors = 0
        
        # Performance metrics
        self.connection_times = deque(maxlen=1000)  # Last 1000 connection times
        self.message_processing_times = deque(maxlen=1000)
        
        # Error tracking
        self.error_counts = defaultdict(int)
        self.recent_errors = deque(maxlen=100)  # Last 100 errors
        
        # Room metrics
        self.room_stats = defaultdict(lambda: {
            'connections': 0,
            'messages': 0,
            'errors': 0
        })
        
        # Start time for uptime calculation
        self.start_time = time.time()
    
    def record_connection(self, room_name: str = None, connection_time: float = None):
        """Record a new WebSocket connection"""
        self.active_connections += 1
        self.total_connections += 1
        
        if connection_time:
            self.connection_times.append(connection_time)
        
        if room_name:
            self.room_stats[room_name]['connections'] += 1
        
        logger.debug(f"WebSocket connection recorded. Active: {self.active_connections}")
    
    def record_disconnection(self, room_name: str = None, close_code: int = None):
        """Record a WebSocket disconnection"""
        self.active_connections = max(0, self.active_connections - 1)
        self.total_disconnections += 1
        
        if close_code:
            self.connection_errors[close_code] += 1
        
        if room_name and room_name in self.room_stats:
            self.room_stats[room_name]['connections'] = max(0, 
                self.room_stats[room_name]['connections'] - 1)
        
        logger.debug(f"WebSocket disconnection recorded. Active: {self.active_connections}")
    
    def record_message_sent(self, room_name: str = None):
        """Record a message sent"""
        self.messages_sent += 1
        
        if room_name:
            self.room_stats[room_name]['messages'] += 1
    
    def record_message_received(self, room_name: str = None, processing_time: float = None):
        """Record a message received"""
        self.messages_received += 1
        
        if processing_time:
            self.message_processing_times.append(processing_time)
        
        if room_name:
            self.room_stats[room_name]['messages'] += 1
    
    def record_error(self, error_type: str, error_message: str, room_name: str = None):
        """Record an error"""
        self.error_counts[error_type] += 1
        self.message_errors += 1
        
        error_data = {
            'type': error_type,
            'message': error_message,
            'timestamp': time.time(),
            'room': room_name
        }
        self.recent_errors.append(error_data)
        
        if room_name:
            self.room_stats[room_name]['errors'] += 1
        
        logger.warning(f"WebSocket error recorded: {error_type} - {error_message}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics"""
        current_time = time.time()
        uptime = current_time - self.start_time
        
        # Calculate averages
        avg_connection_time = (
            sum(self.connection_times) / len(self.connection_times)
            if self.connection_times else 0
        )
        
        avg_processing_time = (
            sum(self.message_processing_times) / len(self.message_processing_times)
            if self.message_processing_times else 0
        )
        
        return {
            'uptime_seconds': uptime,
            'connections': {
                'active': self.active_connections,
                'total': self.total_connections,
                'disconnections': self.total_disconnections,
                'avg_connection_time_ms': avg_connection_time * 1000,
                'error_codes': dict(self.connection_errors)
            },
            'messages': {
                'sent': self.messages_sent,
                'received': self.messages_received,
                'errors': self.message_errors,
                'avg_processing_time_ms': avg_processing_time * 1000
            },
            'errors': {
                'total_types': len(self.error_counts),
                'by_type': dict(self.error_counts),
                'recent_count': len(self.recent_errors)
            },
            'rooms': dict(self.room_stats),
            'performance': {
                'messages_per_second': self.messages_received / uptime if uptime > 0 else 0,
                'connections_per_hour': (self.total_connections / uptime) * 3600 if uptime > 0 else 0,
                'error_rate': (self.message_errors / max(1, self.messages_received)) * 100
            }
        }
    
    def get_recent_errors(self, limit: int = 10) -> list:
        """Get recent errors"""
        return list(self.recent_errors)[-limit:]
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)"""
        self.__init__()
        logger.info("WebSocket metrics reset")
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status for monitoring"""
        metrics = self.get_metrics()
        
        # Determine health status
        error_rate = metrics['performance']['error_rate']
        active_connections = metrics['connections']['active']
        
        if error_rate > 10:  # More than 10% error rate
            status = 'unhealthy'
            issues = ['High error rate']
        elif active_connections > 1000:  # Too many connections
            status = 'warning'
            issues = ['High connection count']
        else:
            status = 'healthy'
            issues = []
        
        return {
            'status': status,
            'issues': issues,
            'metrics_summary': {
                'active_connections': active_connections,
                'error_rate': error_rate,
                'uptime_hours': metrics['uptime_seconds'] / 3600
            }
        }

# Global metrics instance
websocket_metrics = WebSocketMetrics()

# Async task for periodic metrics logging
async def log_metrics_periodically():
    """Log metrics periodically for monitoring"""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            
            metrics = websocket_metrics.get_metrics()
            health = websocket_metrics.get_health_status()
            
            logger.info(f"WebSocket Metrics - Active: {metrics['connections']['active']}, "
                       f"Total: {metrics['connections']['total']}, "
                       f"Error Rate: {metrics['performance']['error_rate']:.2f}%, "
                       f"Status: {health['status']}")
            
            # Log warnings for issues
            if health['issues']:
                logger.warning(f"WebSocket Health Issues: {', '.join(health['issues'])}")
                
        except Exception as e:
            logger.error(f"Error in metrics logging: {e}")

# Start metrics logging task
def start_metrics_logging():
    """Start the metrics logging task"""
    try:
        asyncio.create_task(log_metrics_periodically())
        logger.info("WebSocket metrics logging started")
    except Exception as e:
        logger.error(f"Failed to start metrics logging: {e}")
