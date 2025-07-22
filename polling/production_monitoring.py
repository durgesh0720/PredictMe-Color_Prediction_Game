"""
Production-grade monitoring and metrics for gaming platform
Industry-standard implementation with Prometheus-compatible metrics
"""
import time
import logging
import asyncio
from typing import Dict, Any, List
from collections import defaultdict, deque
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)

class ProductionMetrics:
    """
    Production-grade metrics collection for gaming platform
    Compatible with Prometheus, Grafana, and other monitoring tools
    """
    
    def __init__(self):
        # Business Metrics
        self.total_rounds_played = 0
        self.total_bets_placed = 0
        self.total_revenue = 0.0
        self.total_payouts = 0.0
        
        # Performance Metrics
        self.active_connections = 0
        self.peak_concurrent_users = 0
        self.average_response_time = 0.0
        self.error_rate = 0.0
        
        # Real-time Metrics
        self.current_active_rooms = set()
        self.players_per_room = defaultdict(int)
        self.bets_per_minute = deque(maxlen=60)  # Last 60 minutes
        self.revenue_per_hour = deque(maxlen=24)  # Last 24 hours
        
        # System Health
        self.system_status = "healthy"
        self.last_health_check = time.time()
        self.alerts = []
        
        # Detailed Analytics
        self.color_betting_stats = {
            'red': {'total_bets': 0, 'total_amount': 0, 'wins': 0},
            'green': {'total_bets': 0, 'total_amount': 0, 'wins': 0},
            'violet': {'total_bets': 0, 'total_amount': 0, 'wins': 0}
        }
        
        self.player_analytics = {
            'new_players_today': 0,
            'returning_players': 0,
            'average_session_duration': 0.0,
            'player_retention_rate': 0.0
        }
        
        # Start time for uptime calculation
        self.start_time = time.time()
    
    def record_round_completed(self, room_name: str, round_data: Dict[str, Any]):
        """Record completion of a game round"""
        self.total_rounds_played += 1
        
        # Update room activity
        self.current_active_rooms.add(room_name)
        
        # Record betting statistics
        winning_color = round_data.get('result_color', 'red')
        total_bets = round_data.get('total_bets', 0)
        total_amount = round_data.get('total_amount', 0)
        
        self.total_bets_placed += total_bets
        self.total_revenue += total_amount
        
        # Update color statistics
        if winning_color in self.color_betting_stats:
            self.color_betting_stats[winning_color]['wins'] += 1
        
        # Calculate payout (simplified - actual calculation would be more complex)
        payout = self._calculate_payout(round_data)
        self.total_payouts += payout
        
        logger.info(f"Round completed: {room_name}, Bets: {total_bets}, Revenue: ₹{total_amount}")
    
    def record_bet_placed(self, player_id: str, amount: float, color: str, room_name: str):
        """Record a bet placement"""
        # Update betting statistics
        if color in self.color_betting_stats:
            self.color_betting_stats[color]['total_bets'] += 1
            self.color_betting_stats[color]['total_amount'] += amount
        
        # Update real-time metrics
        current_minute = int(time.time() / 60)
        if not self.bets_per_minute or self.bets_per_minute[-1][0] != current_minute:
            self.bets_per_minute.append([current_minute, 1])
        else:
            self.bets_per_minute[-1][1] += 1
        
        # Update room activity
        self.players_per_room[room_name] += 1
    
    def record_player_connection(self, player_id: str, room_name: str):
        """Record player connection"""
        self.active_connections += 1
        self.peak_concurrent_users = max(self.peak_concurrent_users, self.active_connections)
        self.players_per_room[room_name] += 1
        
        logger.debug(f"Player connected: {player_id} to {room_name}. Active: {self.active_connections}")
    
    def record_player_disconnection(self, player_id: str, room_name: str):
        """Record player disconnection"""
        self.active_connections = max(0, self.active_connections - 1)
        self.players_per_room[room_name] = max(0, self.players_per_room[room_name] - 1)
        
        # Clean up empty rooms
        if self.players_per_room[room_name] == 0:
            self.current_active_rooms.discard(room_name)
            del self.players_per_room[room_name]
        
        logger.debug(f"Player disconnected: {player_id} from {room_name}. Active: {self.active_connections}")
    
    def record_error(self, error_type: str, error_message: str, severity: str = "warning"):
        """Record system error"""
        error_data = {
            'type': error_type,
            'message': error_message,
            'severity': severity,
            'timestamp': time.time(),
            'datetime': datetime.now().isoformat()
        }
        
        self.alerts.append(error_data)
        
        # Keep only last 100 alerts
        if len(self.alerts) > 100:
            self.alerts = self.alerts[-100:]
        
        # Update error rate
        self._update_error_rate()
        
        if severity == "critical":
            logger.error(f"CRITICAL ERROR: {error_type} - {error_message}")
        else:
            logger.warning(f"ERROR: {error_type} - {error_message}")
    
    def get_prometheus_metrics(self) -> str:
        """Generate Prometheus-compatible metrics"""
        uptime = time.time() - self.start_time
        
        metrics = [
            f"# HELP gaming_rounds_total Total number of game rounds completed",
            f"# TYPE gaming_rounds_total counter",
            f"gaming_rounds_total {self.total_rounds_played}",
            "",
            f"# HELP gaming_bets_total Total number of bets placed",
            f"# TYPE gaming_bets_total counter", 
            f"gaming_bets_total {self.total_bets_placed}",
            "",
            f"# HELP gaming_revenue_total Total revenue in rupees",
            f"# TYPE gaming_revenue_total counter",
            f"gaming_revenue_total {self.total_revenue}",
            "",
            f"# HELP gaming_active_connections Current active WebSocket connections",
            f"# TYPE gaming_active_connections gauge",
            f"gaming_active_connections {self.active_connections}",
            "",
            f"# HELP gaming_active_rooms Current number of active game rooms",
            f"# TYPE gaming_active_rooms gauge",
            f"gaming_active_rooms {len(self.current_active_rooms)}",
            "",
            f"# HELP gaming_uptime_seconds System uptime in seconds",
            f"# TYPE gaming_uptime_seconds counter",
            f"gaming_uptime_seconds {uptime}",
            "",
            f"# HELP gaming_error_rate Current error rate percentage",
            f"# TYPE gaming_error_rate gauge",
            f"gaming_error_rate {self.error_rate}",
        ]
        
        # Color-specific metrics
        for color, stats in self.color_betting_stats.items():
            metrics.extend([
                f"gaming_color_bets_total{{color=\"{color}\"}} {stats['total_bets']}",
                f"gaming_color_amount_total{{color=\"{color}\"}} {stats['total_amount']}",
                f"gaming_color_wins_total{{color=\"{color}\"}} {stats['wins']}",
            ])
        
        return "\n".join(metrics)
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        uptime = time.time() - self.start_time
        
        # Calculate rates
        bets_per_minute = len(self.bets_per_minute)
        revenue_per_hour = sum(hour[1] for hour in self.revenue_per_hour) if self.revenue_per_hour else 0
        
        # Calculate win rates
        total_rounds = max(1, self.total_rounds_played)
        color_win_rates = {}
        for color, stats in self.color_betting_stats.items():
            color_win_rates[color] = (stats['wins'] / total_rounds) * 100
        
        return {
            'system_status': self.system_status,
            'uptime_hours': uptime / 3600,
            'performance': {
                'active_connections': self.active_connections,
                'peak_concurrent_users': self.peak_concurrent_users,
                'active_rooms': len(self.current_active_rooms),
                'error_rate': self.error_rate,
                'average_response_time': self.average_response_time
            },
            'business_metrics': {
                'total_rounds': self.total_rounds_played,
                'total_bets': self.total_bets_placed,
                'total_revenue': self.total_revenue,
                'total_payouts': self.total_payouts,
                'profit_margin': ((self.total_revenue - self.total_payouts) / max(1, self.total_revenue)) * 100
            },
            'real_time': {
                'bets_per_minute': bets_per_minute,
                'revenue_per_hour': revenue_per_hour,
                'players_per_room': dict(self.players_per_room)
            },
            'analytics': {
                'color_statistics': self.color_betting_stats,
                'color_win_rates': color_win_rates,
                'player_analytics': self.player_analytics
            },
            'recent_alerts': self.alerts[-10:],  # Last 10 alerts
            'timestamp': time.time()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform system health check"""
        current_time = time.time()
        
        # Check various health indicators
        health_issues = []
        
        # Check error rate
        if self.error_rate > 5.0:  # More than 5% error rate
            health_issues.append("High error rate")
        
        # Check if system is responsive
        if current_time - self.last_health_check > 300:  # 5 minutes
            health_issues.append("Health check overdue")
        
        # Check active connections
        if self.active_connections > 5000:  # High load
            health_issues.append("High connection load")
        
        # Determine overall status
        if not health_issues:
            self.system_status = "healthy"
        elif len(health_issues) == 1:
            self.system_status = "warning"
        else:
            self.system_status = "critical"
        
        self.last_health_check = current_time
        
        return {
            'status': self.system_status,
            'issues': health_issues,
            'timestamp': current_time,
            'uptime': current_time - self.start_time
        }
    
    def _calculate_payout(self, round_data: Dict[str, Any]) -> float:
        """Calculate payout for a round (simplified)"""
        # This is a simplified calculation
        # Real implementation would consider betting odds, house edge, etc.
        total_amount = round_data.get('total_amount', 0)
        return total_amount * 0.95  # 95% payout rate (5% house edge)
    
    def _update_error_rate(self):
        """Update error rate based on recent alerts"""
        recent_time = time.time() - 3600  # Last hour
        recent_errors = [alert for alert in self.alerts if alert['timestamp'] > recent_time]
        
        # Calculate error rate as percentage
        total_operations = max(1, self.total_bets_placed + self.total_rounds_played)
        self.error_rate = (len(recent_errors) / total_operations) * 100

# Global production metrics instance
production_metrics = ProductionMetrics()
