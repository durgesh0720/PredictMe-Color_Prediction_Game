"""
Responsible Gambling and Betting Limits System
Implements comprehensive controls to prevent excessive gambling
"""
import asyncio
import logging
import time
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Count
from .models import Player, Bet, Transaction

logger = logging.getLogger(__name__)

@dataclass
class BettingLimits:
    """Player betting limits configuration"""
    daily_loss_limit: int = None
    daily_bet_limit: int = None
    session_loss_limit: int = None
    session_time_limit: int = None
    max_bet_amount: int = None
    min_bet_amount: int = None
    cooling_off_period: int = None

    def __post_init__(self):
        """Initialize with values from Django settings if not provided"""
        if self.daily_loss_limit is None:
            self.daily_loss_limit = getattr(settings, 'RG_DAILY_LOSS_LIMIT', 10000)
        if self.daily_bet_limit is None:
            self.daily_bet_limit = getattr(settings, 'RG_DAILY_BET_LIMIT', 50000)
        if self.session_loss_limit is None:
            self.session_loss_limit = getattr(settings, 'RG_SESSION_LOSS_LIMIT', 5000)
        if self.session_time_limit is None:
            self.session_time_limit = getattr(settings, 'RG_SESSION_TIME_LIMIT', 7200)
        if self.max_bet_amount is None:
            self.max_bet_amount = getattr(settings, 'RG_MAX_BET_AMOUNT', 2000)
        if self.min_bet_amount is None:
            self.min_bet_amount = getattr(settings, 'RG_MIN_BET_AMOUNT', 100)
        if self.cooling_off_period is None:
            self.cooling_off_period = getattr(settings, 'RG_COOLING_OFF_PERIOD', 86400)

@dataclass
class SessionData:
    """Player session tracking data"""
    start_time: float
    total_bets: int
    total_losses: int
    last_activity: float
    warnings_sent: int
    cooling_off_until: Optional[float] = None

class ResponsibleGamblingManager:
    """
    Manages responsible gambling features and betting limits
    """
    
    def __init__(self):
        # Active sessions by player ID
        self.active_sessions: Dict[str, SessionData] = {}
        
        # Player-specific limits (overrides defaults)
        self.player_limits: Dict[str, BettingLimits] = {}
        
        # Default limits
        self.default_limits = BettingLimits()
        
        # Background tasks
        self.monitoring_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.session_timeout = 1800  # 30 minutes of inactivity
        self.warning_thresholds = [0.5, 0.75, 0.9]  # Warning at 50%, 75%, 90% of limits
        
        # Don't start monitoring during import - will be started when needed
        # self.start_monitoring()
    
    def start_monitoring(self):
        """Start background monitoring tasks"""
        if not self.monitoring_task or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        
        if not self.cleanup_task or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring for responsible gambling"""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                current_time = time.time()
                
                for player_id, session in list(self.active_sessions.items()):
                    # Check session timeout
                    if current_time - session.last_activity > self.session_timeout:
                        await self._end_session(player_id, "timeout")
                        continue
                    
                    # Check session time limits
                    session_duration = current_time - session.start_time
                    limits = self.get_player_limits(player_id)
                    
                    if session_duration > limits.session_time_limit:
                        await self._trigger_session_limit(player_id, "time_limit")
                    
                    # Check for warning thresholds
                    await self._check_warning_thresholds(player_id, session, limits)
                
            except Exception as e:
                logger.error(f"Error in responsible gambling monitoring: {e}")
    
    async def _cleanup_loop(self):
        """Background cleanup of old data"""
        while True:
            try:
                await asyncio.sleep(3600)  # Every hour
                
                current_time = time.time()
                
                # Clean up old sessions
                expired_sessions = [
                    player_id for player_id, session in self.active_sessions.items()
                    if current_time - session.last_activity > 86400  # 24 hours
                ]
                
                for player_id in expired_sessions:
                    del self.active_sessions[player_id]
                    logger.debug(f"Cleaned up expired session for player {player_id}")
                
            except Exception as e:
                logger.error(f"Error in responsible gambling cleanup: {e}")
    
    def get_player_limits(self, player_id: str) -> BettingLimits:
        """Get betting limits for a specific player"""
        return self.player_limits.get(player_id, self.default_limits)
    
    def set_player_limits(self, player_id: str, limits: BettingLimits):
        """Set custom limits for a player"""
        self.player_limits[player_id] = limits
        logger.info(f"Updated betting limits for player {player_id}")
    
    async def start_session(self, player_id: str) -> bool:
        """
        Start a gambling session for a player
        Returns False if player is in cooling-off period
        """
        try:
            current_time = time.time()
            
            # Check if player is in cooling-off period
            if player_id in self.active_sessions:
                session = self.active_sessions[player_id]
                if session.cooling_off_until and current_time < session.cooling_off_until:
                    remaining = session.cooling_off_until - current_time
                    logger.info(f"Player {player_id} in cooling-off period for {remaining:.0f} more seconds")
                    return False
            
            # Start new session
            self.active_sessions[player_id] = SessionData(
                start_time=current_time,
                total_bets=0,
                total_losses=0,
                last_activity=current_time,
                warnings_sent=0
            )
            
            logger.info(f"Started gambling session for player {player_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting session for player {player_id}: {e}")
            return False
    
    async def validate_bet(self, player_id: str, bet_amount: int) -> Tuple[bool, str]:
        """
        Validate if a bet is allowed under responsible gambling rules
        Returns (is_allowed, reason)
        """
        try:
            limits = self.get_player_limits(player_id)
            current_time = time.time()
            
            # Check basic bet amount limits
            if bet_amount < limits.min_bet_amount:
                return False, f"Minimum bet amount is ₹{limits.min_bet_amount/100:.2f}"

            if bet_amount > limits.max_bet_amount:
                return False, f"Maximum bet amount is ₹{limits.max_bet_amount/100:.2f}"
            
            # Check if player has active session
            if player_id not in self.active_sessions:
                session_started = await self.start_session(player_id)
                if not session_started:
                    return False, "Unable to start gambling session"
            
            session = self.active_sessions[player_id]
            
            # Check cooling-off period
            if session.cooling_off_until and current_time < session.cooling_off_until:
                remaining = session.cooling_off_until - current_time
                return False, f"Cooling-off period active for {remaining/3600:.1f} more hours"
            
            # Check daily limits
            daily_stats = await self._get_daily_stats(player_id)
            
            if daily_stats['total_bets'] + bet_amount > limits.daily_bet_limit:
                return False, f"Daily betting limit of ₹{limits.daily_bet_limit/100:.2f} would be exceeded"

            if daily_stats['total_losses'] + bet_amount > limits.daily_loss_limit:
                return False, f"Daily loss limit of ₹{limits.daily_loss_limit/100:.2f} would be exceeded"

            # Check session limits
            if session.total_losses + bet_amount > limits.session_loss_limit:
                return False, f"Session loss limit of ₹{limits.session_loss_limit/100:.2f} would be exceeded"
            
            # Check session time limit
            session_duration = current_time - session.start_time
            if session_duration > limits.session_time_limit:
                return False, "Session time limit exceeded. Please take a break."
            
            return True, "Bet allowed"
            
        except Exception as e:
            logger.error(f"Error validating bet for player {player_id}: {e}")
            return False, "Unable to validate bet"
    
    async def record_bet(self, player_id: str, bet_amount: int, won: bool, payout: int = 0):
        """Record a bet outcome for responsible gambling tracking"""
        try:
            if player_id not in self.active_sessions:
                await self.start_session(player_id)
            
            session = self.active_sessions[player_id]
            session.total_bets += bet_amount
            session.last_activity = time.time()
            
            if not won:
                session.total_losses += bet_amount
            else:
                # Reduce losses by net win amount
                net_win = payout - bet_amount
                if net_win > 0:
                    session.total_losses = max(0, session.total_losses - net_win)
            
            # Check if limits are being approached
            limits = self.get_player_limits(player_id)
            await self._check_warning_thresholds(player_id, session, limits)
            
        except Exception as e:
            logger.error(f"Error recording bet for player {player_id}: {e}")
    
    async def _get_daily_stats(self, player_id: str) -> dict:
        """Get daily betting statistics for a player"""
        try:
            from channels.db import database_sync_to_async

            @database_sync_to_async
            def get_stats():
                today = timezone.now().date()

                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute("""
                        SELECT
                            COALESCE(SUM(amount), 0) as total_bets,
                            COUNT(*) as bet_count
                        FROM polling_bet
                        WHERE player_id = %s
                        AND DATE(created_at) = %s
                    """, [player_id, today])

                    bet_stats = cursor.fetchone()
                    total_bets, bet_count = bet_stats or (0, 0)

                    # Calculate losses (bets - winnings)
                    cursor.execute("""
                        SELECT COALESCE(SUM(amount), 0) as total_winnings
                        FROM polling_transaction
                        WHERE player_id = %s
                        AND transaction_type = 'win'
                        AND DATE(created_at) = %s
                    """, [player_id, today])

                    winnings = cursor.fetchone()[0] or 0
                    total_losses = max(0, total_bets - winnings)

                    return {
                        'total_bets': total_bets,
                        'total_losses': total_losses,
                        'bet_count': bet_count,
                        'total_winnings': winnings
                    }

            return await get_stats()

        except Exception as e:
            logger.error(f"Error getting daily stats for player {player_id}: {e}")
            return {'total_bets': 0, 'total_losses': 0, 'bet_count': 0, 'total_winnings': 0}
    
    async def _check_warning_thresholds(self, player_id: str, session: SessionData, limits: BettingLimits):
        """Check if player should receive warnings about approaching limits"""
        try:
            daily_stats = await self._get_daily_stats(player_id)
            
            # Check various thresholds
            loss_ratio = session.total_losses / limits.session_loss_limit if limits.session_loss_limit > 0 else 0
            daily_loss_ratio = daily_stats['total_losses'] / limits.daily_loss_limit if limits.daily_loss_limit > 0 else 0
            time_ratio = (time.time() - session.start_time) / limits.session_time_limit if limits.session_time_limit > 0 else 0
            
            max_ratio = max(loss_ratio, daily_loss_ratio, time_ratio)
            
            # Send warnings at threshold points
            for i, threshold in enumerate(self.warning_thresholds):
                if max_ratio >= threshold and session.warnings_sent <= i:
                    await self._send_warning(player_id, threshold, max_ratio)
                    session.warnings_sent = i + 1
                    break
        
        except Exception as e:
            logger.error(f"Error checking warning thresholds for player {player_id}: {e}")
    
    async def _send_warning(self, player_id: str, threshold: float, current_ratio: float):
        """Send a responsible gambling warning to the player"""
        try:
            warning_messages = {
                0.5: "You've reached 50% of your gambling limits. Please gamble responsibly.",
                0.75: "You've reached 75% of your gambling limits. Consider taking a break.",
                0.9: "You've reached 90% of your gambling limits. We recommend stopping for today."
            }
            
            message = warning_messages.get(threshold, "Please gamble responsibly.")
            
            # Here you would send the warning via WebSocket or notification system
            logger.warning(f"Responsible gambling warning for player {player_id}: {message}")
            
            # You could integrate with your notification system here
            # await send_notification(player_id, message, 'warning')
            
        except Exception as e:
            logger.error(f"Error sending warning to player {player_id}: {e}")
    
    async def _trigger_session_limit(self, player_id: str, limit_type: str):
        """Trigger when a session limit is reached"""
        try:
            if player_id in self.active_sessions:
                session = self.active_sessions[player_id]
                limits = self.get_player_limits(player_id)
                
                # Set cooling-off period
                session.cooling_off_until = time.time() + limits.cooling_off_period
                
                logger.warning(f"Session limit triggered for player {player_id}: {limit_type}")
                
                # Send notification about cooling-off period
                await self._send_cooling_off_notification(player_id, limits.cooling_off_period)
        
        except Exception as e:
            logger.error(f"Error triggering session limit for player {player_id}: {e}")
    
    async def _send_cooling_off_notification(self, player_id: str, cooling_off_seconds: int):
        """Send cooling-off period notification"""
        try:
            hours = cooling_off_seconds / 3600
            message = f"You've reached your gambling limits. Cooling-off period: {hours:.1f} hours."
            
            logger.info(f"Cooling-off notification for player {player_id}: {message}")
            
            # Integrate with notification system
            # await send_notification(player_id, message, 'cooling_off')
            
        except Exception as e:
            logger.error(f"Error sending cooling-off notification to player {player_id}: {e}")
    
    async def _end_session(self, player_id: str, reason: str):
        """End a gambling session"""
        try:
            if player_id in self.active_sessions:
                session = self.active_sessions[player_id]
                duration = time.time() - session.start_time
                
                logger.info(f"Ended session for player {player_id} ({reason}): {duration:.0f}s, {session.total_bets/100:.2f} bet, {session.total_losses/100:.2f} lost")
                
                # Keep session data but mark as inactive for cooling-off tracking
                # Don't delete immediately in case of cooling-off period
                
        except Exception as e:
            logger.error(f"Error ending session for player {player_id}: {e}")
    
    def get_session_stats(self, player_id: str) -> dict:
        """Get current session statistics for a player"""
        if player_id not in self.active_sessions:
            return {'active': False}
        
        session = self.active_sessions[player_id]
        limits = self.get_player_limits(player_id)
        current_time = time.time()
        
        return {
            'active': True,
            'session_duration': current_time - session.start_time,
            'total_bets': session.total_bets,
            'total_losses': session.total_losses,
            'warnings_sent': session.warnings_sent,
            'cooling_off_until': session.cooling_off_until,
            'limits': {
                'daily_loss_limit': limits.daily_loss_limit,
                'daily_bet_limit': limits.daily_bet_limit,
                'session_loss_limit': limits.session_loss_limit,
                'session_time_limit': limits.session_time_limit,
                'max_bet_amount': limits.max_bet_amount,
                'min_bet_amount': limits.min_bet_amount
            }
        }
    
    async def force_cooling_off(self, player_id: str, duration_hours: int = 24):
        """Manually trigger cooling-off period for a player"""
        try:
            if player_id not in self.active_sessions:
                await self.start_session(player_id)
            
            session = self.active_sessions[player_id]
            session.cooling_off_until = time.time() + (duration_hours * 3600)
            
            logger.info(f"Forced cooling-off period for player {player_id}: {duration_hours} hours")
            await self._send_cooling_off_notification(player_id, duration_hours * 3600)
            
        except Exception as e:
            logger.error(f"Error forcing cooling-off for player {player_id}: {e}")
    
    async def shutdown(self):
        """Gracefully shutdown the responsible gambling system"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
        
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
        
        logger.info("Responsible gambling system shutdown")

# Global instance
responsible_gambling = ResponsibleGamblingManager()
