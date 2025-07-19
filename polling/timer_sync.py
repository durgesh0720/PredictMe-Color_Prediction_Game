"""
Server-Authoritative Timer Synchronization System
Prevents timing inconsistencies and ensures fair game timing
"""
import asyncio
import time
import logging
from typing import Dict, Optional, Callable
from dataclasses import dataclass
from django.utils import timezone
from django.db import transaction
from .models import GameRound

logger = logging.getLogger(__name__)

@dataclass
class TimerState:
    """Represents the current state of a game timer"""
    round_id: str
    start_time: float  # Server timestamp
    duration: float    # Total duration in seconds
    betting_duration: float  # Betting phase duration
    current_phase: str  # 'betting', 'result', 'ended'
    is_active: bool
    last_sync: float   # Last synchronization timestamp

class ServerAuthoritativeTimer:
    """
    Server-authoritative timer that prevents client-side timing manipulation
    and ensures consistent timing across all clients
    """
    
    def __init__(self, round_duration: int = 50, betting_duration: int = 40):
        self.round_duration = round_duration
        self.betting_duration = betting_duration
        self.result_duration = round_duration - betting_duration
        
        # Active timers by room
        self.active_timers: Dict[str, TimerState] = {}
        
        # Callbacks for timer events
        self.phase_change_callbacks: Dict[str, Callable] = {}
        self.timer_update_callbacks: Dict[str, Callable] = {}
        
        # Synchronization settings
        self.sync_interval = 1.0  # Sync every second
        self.tolerance = 0.5      # Tolerance for timing differences
        
        # Background task for timer management
        self.timer_task: Optional[asyncio.Task] = None
        self.start_timer_management()
    
    def start_timer_management(self):
        """Start the background timer management task"""
        if not self.timer_task or self.timer_task.done():
            self.timer_task = asyncio.create_task(self._timer_management_loop())
    
    async def start_round_timer(self, room_name: str, game_round) -> bool:
        """
        Start a new round timer with server-authoritative timing
        Returns True if timer started successfully
        """
        try:
            current_time = time.time()
            
            # Calculate actual elapsed time from database
            db_start_time = game_round.start_time.timestamp()
            elapsed_time = current_time - db_start_time
            
            # Validate that the round hasn't already expired
            if elapsed_time >= self.round_duration:
                logger.warning(f"Cannot start timer for expired round {game_round.period_id}")
                return False
            
            # Create timer state
            timer_state = TimerState(
                round_id=game_round.period_id,
                start_time=db_start_time,
                duration=self.round_duration,
                betting_duration=self.betting_duration,
                current_phase='betting' if elapsed_time < self.betting_duration else 'result',
                is_active=True,
                last_sync=current_time
            )
            
            self.active_timers[room_name] = timer_state
            
            logger.info(f"Started server-authoritative timer for room {room_name}, round {game_round.period_id}")
            logger.info(f"Elapsed: {elapsed_time:.1f}s, Phase: {timer_state.current_phase}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error starting round timer: {e}")
            return False
    
    def get_timer_state(self, room_name: str) -> Optional[TimerState]:
        """Get current timer state for a room"""
        return self.active_timers.get(room_name)
    
    def get_accurate_time_remaining(self, room_name: str) -> tuple[float, str]:
        """
        Get server-authoritative time remaining and current phase
        Returns (time_remaining, phase)
        """
        timer_state = self.active_timers.get(room_name)
        if not timer_state or not timer_state.is_active:
            return 0.0, 'ended'
        
        current_time = time.time()
        elapsed_time = current_time - timer_state.start_time
        
        # Determine phase and time remaining
        if elapsed_time < timer_state.betting_duration:
            # Still in betting phase
            time_remaining = timer_state.betting_duration - elapsed_time
            phase = 'betting'
        elif elapsed_time < timer_state.duration:
            # In result phase
            time_remaining = timer_state.duration - elapsed_time
            phase = 'result'
        else:
            # Round ended
            time_remaining = 0.0
            phase = 'ended'
            timer_state.is_active = False
        
        return max(0.0, time_remaining), phase
    
    def is_betting_allowed(self, room_name: str) -> bool:
        """
        Check if betting is currently allowed (server-authoritative)
        """
        time_remaining, phase = self.get_accurate_time_remaining(room_name)
        return phase == 'betting' and time_remaining > 0
    
    def validate_bet_timing(self, room_name: str, client_timestamp: float = None) -> tuple[bool, str]:
        """
        Validate that a bet is placed within the allowed time window
        Returns (is_valid, reason)
        """
        if not self.is_betting_allowed(room_name):
            time_remaining, phase = self.get_accurate_time_remaining(room_name)
            return False, f"Betting not allowed. Phase: {phase}, Time remaining: {time_remaining:.1f}s"
        
        # Additional validation against client timestamp if provided
        if client_timestamp:
            server_time = time.time()
            time_diff = abs(server_time - client_timestamp)
            
            if time_diff > 5.0:  # 5 second tolerance
                return False, f"Client time too far from server time (diff: {time_diff:.1f}s)"
        
        return True, "Bet timing valid"
    
    async def force_end_round(self, room_name: str, reason: str = "Manual"):
        """Force end a round timer"""
        timer_state = self.active_timers.get(room_name)
        if timer_state:
            timer_state.is_active = False
            timer_state.current_phase = 'ended'
            
            logger.info(f"Force ended timer for room {room_name}: {reason}")
            
            # Trigger phase change callback
            if room_name in self.phase_change_callbacks:
                try:
                    await self.phase_change_callbacks[room_name]('ended', 0.0)
                except Exception as e:
                    logger.error(f"Error in phase change callback: {e}")
    
    def register_phase_change_callback(self, room_name: str, callback: Callable):
        """Register callback for phase changes"""
        self.phase_change_callbacks[room_name] = callback
    
    def register_timer_update_callback(self, room_name: str, callback: Callable):
        """Register callback for timer updates"""
        self.timer_update_callbacks[room_name] = callback
    
    async def _timer_management_loop(self):
        """Background loop for timer management and synchronization"""
        while True:
            try:
                await asyncio.sleep(self.sync_interval)
                current_time = time.time()
                
                rooms_to_remove = []
                
                for room_name, timer_state in list(self.active_timers.items()):
                    if not timer_state.is_active:
                        rooms_to_remove.append(room_name)
                        continue
                    
                    # Get current state
                    time_remaining, phase = self.get_accurate_time_remaining(room_name)
                    
                    # Check for phase changes
                    if phase != timer_state.current_phase:
                        old_phase = timer_state.current_phase
                        timer_state.current_phase = phase
                        
                        logger.info(f"Phase change in room {room_name}: {old_phase} -> {phase}")
                        
                        # Trigger phase change callback
                        if room_name in self.phase_change_callbacks:
                            try:
                                await self.phase_change_callbacks[room_name](phase, time_remaining)
                            except Exception as e:
                                logger.error(f"Error in phase change callback for {room_name}: {e}")
                    
                    # Send timer updates
                    if room_name in self.timer_update_callbacks:
                        try:
                            await self.timer_update_callbacks[room_name](time_remaining, phase)
                        except Exception as e:
                            logger.error(f"Error in timer update callback for {room_name}: {e}")
                    
                    # Update last sync time
                    timer_state.last_sync = current_time
                    
                    # Check if round has ended
                    if phase == 'ended':
                        timer_state.is_active = False
                
                # Clean up inactive timers
                for room_name in rooms_to_remove:
                    del self.active_timers[room_name]
                    logger.debug(f"Cleaned up timer for room {room_name}")
                
            except Exception as e:
                logger.error(f"Error in timer management loop: {e}")
    
    def get_sync_data(self, room_name: str) -> dict:
        """
        Get synchronization data for clients
        """
        timer_state = self.active_timers.get(room_name)
        if not timer_state:
            return {
                'server_time': time.time(),
                'time_remaining': 0,
                'phase': 'ended',
                'round_active': False
            }
        
        time_remaining, phase = self.get_accurate_time_remaining(room_name)
        
        return {
            'server_time': time.time(),
            'round_start_time': timer_state.start_time,
            'time_remaining': time_remaining,
            'phase': phase,
            'round_active': timer_state.is_active,
            'round_id': timer_state.round_id,
            'betting_duration': timer_state.betting_duration,
            'total_duration': timer_state.duration
        }
    
    async def shutdown(self):
        """Gracefully shutdown the timer system"""
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            try:
                await self.timer_task
            except asyncio.CancelledError:
                pass
        
        self.active_timers.clear()
        logger.info("Server-authoritative timer system shutdown")

# Global instance
server_timer = ServerAuthoritativeTimer()
