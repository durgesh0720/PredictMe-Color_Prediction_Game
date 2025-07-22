"""
Game state management with database synchronization
"""
import asyncio
import logging
import time
from typing import Dict, Any, Optional
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import GameRound, Bet

logger = logging.getLogger(__name__)

class GameStateManager:
    """Manages game state with database persistence"""
    
    def __init__(self):
        self.state_cache = {}  # Room -> state cache
        self.cache_ttl = 30    # Cache TTL in seconds
        self.sync_lock = asyncio.Lock()
    
    async def get_room_state(self, room_name: str, force_refresh: bool = False) -> Dict[str, Any]:
        """Get room state with caching"""
        cache_key = f"room_state_{room_name}"
        current_time = time.time()
        
        # Check cache first
        if not force_refresh and cache_key in self.state_cache:
            cached_data = self.state_cache[cache_key]
            if current_time - cached_data['timestamp'] < self.cache_ttl:
                return cached_data['data']
        
        # Fetch from database
        state = await self._fetch_room_state_from_db(room_name)
        
        # Update cache
        self.state_cache[cache_key] = {
            'data': state,
            'timestamp': current_time
        }
        
        return state
    
    @database_sync_to_async
    def _fetch_room_state_from_db(self, room_name: str) -> Dict[str, Any]:
        """Fetch room state from database"""
        try:
            # Get active round
            active_round = GameRound.objects.filter(
                room=room_name,
                ended=False
            ).first()
            
            if not active_round:
                return {
                    'has_active_round': False,
                    'round_id': None,
                    'time_remaining': 0,
                    'phase': 'waiting',
                    'total_bets': 0,
                    'total_amount': 0
                }
            
            # Calculate time remaining
            elapsed = (timezone.now() - active_round.start_time).total_seconds()
            time_remaining = max(0, 50 - elapsed)  # 50 second rounds
            
            # Determine phase
            if time_remaining > 10:
                phase = 'betting'
            elif time_remaining > 0:
                phase = 'result'
            else:
                phase = 'ended'
            
            # Get betting statistics
            bets = Bet.objects.filter(round=active_round)
            total_bets = bets.count()
            total_amount = sum(bet.amount for bet in bets)
            
            return {
                'has_active_round': True,
                'round_id': active_round.id,
                'period_id': active_round.period_id,
                'time_remaining': int(time_remaining),
                'phase': phase,
                'total_bets': total_bets,
                'total_amount': total_amount,
                'start_time': active_round.start_time.timestamp(),
                'result_color': active_round.result_color,
                'result_number': active_round.result_number
            }
            
        except Exception as e:
            logger.error(f"Error fetching room state for {room_name}: {e}")
            return {
                'has_active_round': False,
                'round_id': None,
                'time_remaining': 0,
                'phase': 'error',
                'total_bets': 0,
                'total_amount': 0
            }
    
    async def sync_round_to_db(self, room_name: str, round_data: Dict[str, Any]):
        """Synchronize round data to database"""
        async with self.sync_lock:
            try:
                await self._update_round_in_db(round_data)
                # Invalidate cache
                cache_key = f"room_state_{room_name}"
                if cache_key in self.state_cache:
                    del self.state_cache[cache_key]
                    
            except Exception as e:
                logger.error(f"Error syncing round to DB: {e}")
    
    @database_sync_to_async
    def _update_round_in_db(self, round_data: Dict[str, Any]):
        """Update round in database"""
        try:
            round_id = round_data.get('round_id')
            if not round_id:
                return
            
            GameRound.objects.filter(id=round_id).update(
                result_color=round_data.get('result_color'),
                result_number=round_data.get('result_number'),
                ended=round_data.get('ended', False)
            )
            
        except Exception as e:
            logger.error(f"Error updating round in DB: {e}")
    
    async def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, cached_data in self.state_cache.items():
            if current_time - cached_data['timestamp'] > self.cache_ttl * 2:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.state_cache[key]
        
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")
    
    async def get_admin_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive data for admin dashboard"""
        try:
            return await self._fetch_admin_data_from_db()
        except Exception as e:
            logger.error(f"Error fetching admin dashboard data: {e}")
            return {
                'active_rounds': [],
                'total_players': 0,
                'total_bets_today': 0,
                'total_amount_today': 0
            }
    
    @database_sync_to_async
    def _fetch_admin_data_from_db(self) -> Dict[str, Any]:
        """Fetch admin dashboard data from database"""
        from django.db.models import Sum, Count
        from datetime import date
        
        # Get active rounds
        active_rounds = list(GameRound.objects.filter(ended=False).values(
            'id', 'period_id', 'room', 'start_time'
        ))
        
        # Get today's statistics
        today = date.today()
        today_bets = Bet.objects.filter(created_at__date=today)
        
        total_bets_today = today_bets.count()
        total_amount_today = today_bets.aggregate(
            total=Sum('amount')
        )['total'] or 0
        
        # Get unique players today
        total_players = today_bets.values('player').distinct().count()
        
        return {
            'active_rounds': active_rounds,
            'total_players': total_players,
            'total_bets_today': total_bets_today,
            'total_amount_today': total_amount_today
        }

# Global instance
game_state_manager = GameStateManager()
