"""
Comprehensive Monitoring and Alerting System
Real-time monitoring of game state, WebSocket connections, and system health
"""
import asyncio
import logging
import time
import json
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import connection
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)

@dataclass
class Alert:
    """Represents a system alert"""
    alert_id: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    category: str  # 'game_state', 'websocket', 'database', 'security'
    title: str
    description: str
    timestamp: float
    resolved: bool = False
    resolution_time: Optional[float] = None

@dataclass
class SystemMetrics:
    """System performance metrics"""
    timestamp: float
    active_connections: int
    pending_messages: int
    failed_messages: int
    active_rounds: int
    stuck_rounds: int
    failed_transactions: int
    error_rate: float
    response_time_avg: float
    memory_usage: float
    cpu_usage: float

class MonitoringManager:
    """
    Comprehensive monitoring and alerting system
    """
    
    def __init__(self):
        # Alert management
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.alert_callbacks: List[Callable] = []
        
        # Metrics tracking
        self.metrics_history: List[SystemMetrics] = []
        self.performance_counters = {
            'requests_total': 0,
            'requests_failed': 0,
            'response_times': [],
            'websocket_connections': 0,
            'websocket_disconnections': 0,
            'bet_processing_errors': 0,
            'database_errors': 0
        }
        
        # Monitoring configuration
        self.check_interval = 30  # seconds
        self.metrics_retention = 86400  # 24 hours
        self.alert_thresholds = {
            'error_rate': 0.05,  # 5%
            'response_time': 5.0,  # 5 seconds
            'stuck_rounds': 1,
            'failed_transactions': 5,
            'websocket_failures': 10
        }
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.metrics_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start all monitoring tasks"""
        if not self.monitoring_task or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        if not self.metrics_task or self.metrics_task.done():
            self.metrics_task = asyncio.create_task(self._metrics_collection_loop())
        
        if not self.cleanup_task or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Check various system components
                await self._check_game_state()
                await self._check_websocket_health()
                await self._check_database_health()
                await self._check_error_rates()
                await self._check_performance_metrics()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    async def _metrics_collection_loop(self):
        """Collect system metrics periodically"""
        while True:
            try:
                await asyncio.sleep(60)  # Collect metrics every minute
                
                metrics = await self._collect_system_metrics()
                self.metrics_history.append(metrics)
                
                # Keep only recent metrics
                cutoff_time = time.time() - self.metrics_retention
                self.metrics_history = [
                    m for m in self.metrics_history 
                    if m.timestamp > cutoff_time
                ]
                
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
    
    async def _cleanup_loop(self):
        """Clean up old data periodically"""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                
                # Clean up old alerts
                cutoff_time = time.time() - (7 * 86400)  # 7 days
                self.alert_history = [
                    alert for alert in self.alert_history
                    if alert.timestamp > cutoff_time
                ]
                
                # Clean up performance counters
                self.performance_counters['response_times'] = \
                    self.performance_counters['response_times'][-1000:]  # Keep last 1000
                
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")
    
    async def _check_game_state(self):
        """Monitor game state health"""
        try:
            # Check for stuck rounds
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM polling_gameround 
                    WHERE ended = FALSE 
                    AND start_time < %s
                """, [timezone.now() - timedelta(minutes=10)])
                
                stuck_count = cursor.fetchone()[0]
                
                if stuck_count > self.alert_thresholds['stuck_rounds']:
                    await self._create_alert(
                        'stuck_rounds',
                        'high',
                        'game_state',
                        'Stuck Game Rounds Detected',
                        f'{stuck_count} game rounds have been running for over 10 minutes'
                    )
                
                # Check for failed bets
                cursor.execute("""
                    SELECT COUNT(*) FROM polling_bet b
                    LEFT JOIN polling_transaction t ON b.id = t.bet_id
                    WHERE t.id IS NULL
                    AND b.created_at > %s
                """, [timezone.now() - timedelta(hours=1)])
                
                failed_bets = cursor.fetchone()[0]
                
                if failed_bets > self.alert_thresholds['failed_transactions']:
                    await self._create_alert(
                        'failed_bets',
                        'critical',
                        'game_state',
                        'Failed Bet Processing',
                        f'{failed_bets} bets failed to process in the last hour'
                    )
        
        except Exception as e:
            logger.error(f"Error checking game state: {e}")
    
    async def _check_websocket_health(self):
        """Monitor WebSocket connection health"""
        try:
            # Import here to avoid circular imports
            from .websocket_reliability import reliable_ws_manager
            
            stats = reliable_ws_manager.get_stats()
            
            if stats['overdue_messages'] > self.alert_thresholds['websocket_failures']:
                await self._create_alert(
                    'websocket_failures',
                    'high',
                    'websocket',
                    'WebSocket Message Delivery Issues',
                    f'{stats["overdue_messages"]} messages are overdue for delivery'
                )
            
            if stats['total_pending'] > 100:  # Too many pending messages
                await self._create_alert(
                    'websocket_backlog',
                    'medium',
                    'websocket',
                    'WebSocket Message Backlog',
                    f'{stats["total_pending"]} messages pending delivery'
                )
        
        except Exception as e:
            logger.error(f"Error checking WebSocket health: {e}")
    
    async def _check_database_health(self):
        """Monitor database health"""
        try:
            # Check database connection
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            
            db_response_time = time.time() - start_time
            
            if db_response_time > 2.0:  # 2 second threshold
                await self._create_alert(
                    'slow_database',
                    'medium',
                    'database',
                    'Slow Database Response',
                    f'Database response time: {db_response_time:.2f}s'
                )
            
            # Check for database locks
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT COUNT(*) FROM pg_stat_activity 
                    WHERE state = 'active' AND waiting = true
                """)
                
                waiting_queries = cursor.fetchone()[0] if cursor.fetchone() else 0
                
                if waiting_queries > 5:
                    await self._create_alert(
                        'database_locks',
                        'high',
                        'database',
                        'Database Lock Contention',
                        f'{waiting_queries} queries waiting for locks'
                    )
        
        except Exception as e:
            logger.error(f"Error checking database health: {e}")
            await self._create_alert(
                'database_error',
                'critical',
                'database',
                'Database Connection Error',
                f'Unable to connect to database: {str(e)}'
            )
    
    async def _check_error_rates(self):
        """Monitor system error rates"""
        try:
            total_requests = self.performance_counters['requests_total']
            failed_requests = self.performance_counters['requests_failed']
            
            if total_requests > 100:  # Only check if we have enough data
                error_rate = failed_requests / total_requests
                
                if error_rate > self.alert_thresholds['error_rate']:
                    await self._create_alert(
                        'high_error_rate',
                        'high',
                        'performance',
                        'High Error Rate',
                        f'Error rate: {error_rate:.2%} ({failed_requests}/{total_requests})'
                    )
        
        except Exception as e:
            logger.error(f"Error checking error rates: {e}")
    
    async def _check_performance_metrics(self):
        """Monitor performance metrics"""
        try:
            response_times = self.performance_counters['response_times']
            
            if len(response_times) > 10:
                avg_response_time = sum(response_times[-100:]) / min(100, len(response_times))
                
                if avg_response_time > self.alert_thresholds['response_time']:
                    await self._create_alert(
                        'slow_response',
                        'medium',
                        'performance',
                        'Slow Response Times',
                        f'Average response time: {avg_response_time:.2f}s'
                    )
        
        except Exception as e:
            logger.error(f"Error checking performance metrics: {e}")
    
    async def _collect_system_metrics(self) -> SystemMetrics:
        """Collect current system metrics"""
        try:
            # Get WebSocket stats
            from .websocket_reliability import reliable_ws_manager
            ws_stats = reliable_ws_manager.get_stats()
            
            # Get database stats
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM polling_gameround WHERE ended = FALSE")
                active_rounds = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM polling_gameround 
                    WHERE ended = FALSE AND start_time < %s
                """, [timezone.now() - timedelta(minutes=10)])
                stuck_rounds = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT COUNT(*) FROM polling_bet b
                    LEFT JOIN polling_transaction t ON b.id = t.bet_id
                    WHERE t.id IS NULL AND b.created_at > %s
                """, [timezone.now() - timedelta(hours=1)])
                failed_transactions = cursor.fetchone()[0]
            
            # Calculate error rate
            total_requests = self.performance_counters['requests_total']
            failed_requests = self.performance_counters['requests_failed']
            error_rate = failed_requests / max(1, total_requests)
            
            # Calculate average response time
            response_times = self.performance_counters['response_times']
            avg_response_time = sum(response_times[-100:]) / max(1, len(response_times[-100:]))
            
            # Get system resource usage (simplified)
            import psutil
            memory_usage = psutil.virtual_memory().percent
            cpu_usage = psutil.cpu_percent()
            
            return SystemMetrics(
                timestamp=time.time(),
                active_connections=self.performance_counters['websocket_connections'],
                pending_messages=ws_stats['total_pending'],
                failed_messages=ws_stats['overdue_messages'],
                active_rounds=active_rounds,
                stuck_rounds=stuck_rounds,
                failed_transactions=failed_transactions,
                error_rate=error_rate,
                response_time_avg=avg_response_time,
                memory_usage=memory_usage,
                cpu_usage=cpu_usage
            )
        
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
            return SystemMetrics(
                timestamp=time.time(),
                active_connections=0,
                pending_messages=0,
                failed_messages=0,
                active_rounds=0,
                stuck_rounds=0,
                failed_transactions=0,
                error_rate=0.0,
                response_time_avg=0.0,
                memory_usage=0.0,
                cpu_usage=0.0
            )
    
    async def _create_alert(self, alert_id: str, severity: str, category: str, title: str, description: str):
        """Create a new alert"""
        try:
            # Check if alert already exists and is not resolved
            if alert_id in self.active_alerts and not self.active_alerts[alert_id].resolved:
                return  # Don't create duplicate alerts
            
            alert = Alert(
                alert_id=alert_id,
                severity=severity,
                category=category,
                title=title,
                description=description,
                timestamp=time.time()
            )
            
            self.active_alerts[alert_id] = alert
            self.alert_history.append(alert)
            
            logger.warning(f"ALERT [{severity.upper()}] {title}: {description}")
            
            # Trigger alert callbacks
            for callback in self.alert_callbacks:
                try:
                    await callback(alert)
                except Exception as e:
                    logger.error(f"Error in alert callback: {e}")
            
            # Send email for critical alerts
            if severity == 'critical':
                await self._send_email_alert(alert)
        
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    async def _send_email_alert(self, alert: Alert):
        """Send email notification for critical alerts"""
        try:
            if not hasattr(settings, 'ADMIN_EMAIL') or not settings.ADMIN_EMAIL:
                return
            
            subject = f"[CRITICAL ALERT] {alert.title}"
            message = f"""
            Critical Alert Detected:
            
            Title: {alert.title}
            Category: {alert.category}
            Description: {alert.description}
            Time: {datetime.fromtimestamp(alert.timestamp)}
            
            Please investigate immediately.
            """
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=True
            )
            
        except Exception as e:
            logger.error(f"Error sending email alert: {e}")
    
    def resolve_alert(self, alert_id: str):
        """Mark an alert as resolved"""
        if alert_id in self.active_alerts:
            self.active_alerts[alert_id].resolved = True
            self.active_alerts[alert_id].resolution_time = time.time()
            logger.info(f"Resolved alert: {alert_id}")
    
    def record_request(self, success: bool, response_time: float):
        """Record request metrics"""
        self.performance_counters['requests_total'] += 1
        if not success:
            self.performance_counters['requests_failed'] += 1
        
        self.performance_counters['response_times'].append(response_time)
    
    def record_websocket_event(self, event_type: str):
        """Record WebSocket events"""
        if event_type == 'connect':
            self.performance_counters['websocket_connections'] += 1
        elif event_type == 'disconnect':
            self.performance_counters['websocket_disconnections'] += 1
    
    def record_error(self, error_type: str):
        """Record system errors"""
        counter_key = f"{error_type}_errors"
        if counter_key in self.performance_counters:
            self.performance_counters[counter_key] += 1
    
    def get_dashboard_data(self) -> dict:
        """Get monitoring dashboard data"""
        current_time = time.time()
        
        # Get recent metrics
        recent_metrics = [
            m for m in self.metrics_history
            if current_time - m.timestamp < 3600  # Last hour
        ]
        
        # Get active alerts by severity
        alerts_by_severity = {}
        for alert in self.active_alerts.values():
            if not alert.resolved:
                severity = alert.severity
                if severity not in alerts_by_severity:
                    alerts_by_severity[severity] = []
                alerts_by_severity[severity].append(asdict(alert))
        
        return {
            'system_status': 'healthy' if not any(
                not alert.resolved and alert.severity == 'critical'
                for alert in self.active_alerts.values()
            ) else 'critical',
            'active_alerts': alerts_by_severity,
            'recent_metrics': [asdict(m) for m in recent_metrics[-60:]],  # Last 60 data points
            'performance_counters': self.performance_counters.copy(),
            'alert_summary': {
                'total_active': len([a for a in self.active_alerts.values() if not a.resolved]),
                'critical': len([a for a in self.active_alerts.values() if not a.resolved and a.severity == 'critical']),
                'high': len([a for a in self.active_alerts.values() if not a.resolved and a.severity == 'high']),
                'medium': len([a for a in self.active_alerts.values() if not a.resolved and a.severity == 'medium']),
                'low': len([a for a in self.active_alerts.values() if not a.resolved and a.severity == 'low'])
            }
        }
    
    def add_alert_callback(self, callback: Callable):
        """Add a callback function for alerts"""
        self.alert_callbacks.append(callback)
    
    async def shutdown(self):
        """Gracefully shutdown monitoring"""
        for task in [self.monitoring_task, self.metrics_task, self.cleanup_task]:
            if task and not task.done():
                task.cancel()
        
        logger.info("Monitoring system shutdown")

# Global instance
monitoring = MonitoringManager()
