"""
Redis-backed game state management for horizontal scalability
Industry-standard implementation for production gaming systems
"""
import json
import time
import logging
import asyncio
from typing import Dict, Any, Optional, Set
from datetime import datetime, timedelta
import redis.asyncio as redis
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class RedisGameStateManager:
    """
    Production-ready game state management using Redis
    Supports horizontal scaling and high availability
    """
    
    def __init__(self):
        # Redis connection configuration
        self.redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        self.redis_pool = None
        self.redis_client = None
        
        # Key prefixes for different data types
        self.ROOM_PREFIX = "game:room:"
        self.ROUND_PREFIX = "game:round:"
        self.PLAYER_PREFIX = "game:player:"
        self.TIMER_PREFIX = "game:timer:"
        self.LOCK_PREFIX = "game:lock:"
        
        # TTL settings (in seconds)
        self.ROOM_TTL = 3600      # 1 hour
        self.ROUND_TTL = 86400    # 24 hours
        self.PLAYER_TTL = 1800    # 30 minutes
        self.TIMER_TTL = 300      # 5 minutes
        self.LOCK_TTL = 30        # 30 seconds
        
    async def initialize(self):
        """Initialize Redis connection pool"""
        try:
            self.redis_pool = redis.ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            self.redis_client = redis.Redis(connection_pool=self.redis_pool)
            
            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            # Fallback to in-memory for development
            self.redis_client = None
    
    async def close(self):
        """Close Redis connections"""
        if self.redis_client:
            await self.redis_client.close()
        if self.redis_pool:
            await self.redis_pool.disconnect()
    
    # Room State Management
    async def get_room_state(self, room_name: str) -> Dict[str, Any]:
        """Get complete room state"""
        if not self.redis_client:
            return await self._get_fallback_room_state(room_name)
        
        try:
            key = f"{self.ROOM_PREFIX}{room_name}"
            data = await self.redis_client.hgetall(key)
            
            if not data:
                return self._create_default_room_state(room_name)
            
            # Deserialize JSON fields
            state = {}
            for field, value in data.items():
                field = field.decode('utf-8')
                value = value.decode('utf-8')
                
                if field in ['players', 'recent_results', 'betting_stats']:
                    state[field] = json.loads(value)
                elif field in ['time_remaining', 'total_bets', 'total_amount']:
                    state[field] = int(value)
                elif field in ['betting_closed', 'has_active_round']:
                    state[field] = value.lower() == 'true'
                else:
                    state[field] = value
            
            return state
            
        except Exception as e:
            logger.error(f"Error getting room state for {room_name}: {e}")
            return await self._get_fallback_room_state(room_name)
    
    async def update_room_state(self, room_name: str, updates: Dict[str, Any]):
        """Update room state atomically"""
        if not self.redis_client:
            return await self._update_fallback_room_state(room_name, updates)
        
        try:
            key = f"{self.ROOM_PREFIX}{room_name}"
            
            # Serialize complex fields
            serialized_updates = {}
            for field, value in updates.items():
                if isinstance(value, (dict, list)):
                    serialized_updates[field] = json.dumps(value)
                elif isinstance(value, bool):
                    serialized_updates[field] = str(value).lower()
                else:
                    serialized_updates[field] = str(value)
            
            # Atomic update
            pipe = self.redis_client.pipeline()
            pipe.hset(key, mapping=serialized_updates)
            pipe.expire(key, self.ROOM_TTL)
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Error updating room state for {room_name}: {e}")
    
    # Player Management
    async def add_player_to_room(self, room_name: str, player_id: str, player_data: Dict[str, Any]):
        """Add player to room with atomic operations"""
        if not self.redis_client:
            return
        
        try:
            # Add to room's player set
            room_players_key = f"{self.ROOM_PREFIX}{room_name}:players"
            player_key = f"{self.PLAYER_PREFIX}{room_name}:{player_id}"
            
            pipe = self.redis_client.pipeline()
            pipe.sadd(room_players_key, player_id)
            pipe.expire(room_players_key, self.ROOM_TTL)
            pipe.hset(player_key, mapping={
                'username': player_data.get('username', ''),
                'balance': str(player_data.get('balance', 0)),
                'joined_at': str(time.time()),
                'last_activity': str(time.time())
            })
            pipe.expire(player_key, self.PLAYER_TTL)
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Error adding player {player_id} to room {room_name}: {e}")
    
    async def remove_player_from_room(self, room_name: str, player_id: str):
        """Remove player from room"""
        if not self.redis_client:
            return
        
        try:
            room_players_key = f"{self.ROOM_PREFIX}{room_name}:players"
            player_key = f"{self.PLAYER_PREFIX}{room_name}:{player_id}"
            
            pipe = self.redis_client.pipeline()
            pipe.srem(room_players_key, player_id)
            pipe.delete(player_key)
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Error removing player {player_id} from room {room_name}: {e}")
    
    async def get_room_players(self, room_name: str) -> Set[str]:
        """Get all players in room"""
        if not self.redis_client:
            return set()
        
        try:
            room_players_key = f"{self.ROOM_PREFIX}{room_name}:players"
            players = await self.redis_client.smembers(room_players_key)
            return {player.decode('utf-8') for player in players}
            
        except Exception as e:
            logger.error(f"Error getting players for room {room_name}: {e}")
            return set()
    
    # Distributed Locking
    async def acquire_lock(self, lock_name: str, timeout: int = 30) -> bool:
        """Acquire distributed lock for critical sections"""
        if not self.redis_client:
            return True  # Fallback: assume lock acquired
        
        try:
            key = f"{self.LOCK_PREFIX}{lock_name}"
            lock_id = f"{time.time()}_{id(self)}"
            
            # Try to acquire lock
            result = await self.redis_client.set(
                key, lock_id, nx=True, ex=timeout
            )
            
            if result:
                logger.debug(f"Acquired lock: {lock_name}")
                return True
            else:
                logger.debug(f"Failed to acquire lock: {lock_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error acquiring lock {lock_name}: {e}")
            return False
    
    async def release_lock(self, lock_name: str):
        """Release distributed lock"""
        if not self.redis_client:
            return
        
        try:
            key = f"{self.LOCK_PREFIX}{lock_name}"
            await self.redis_client.delete(key)
            logger.debug(f"Released lock: {lock_name}")
            
        except Exception as e:
            logger.error(f"Error releasing lock {lock_name}: {e}")
    
    # Fallback methods for development/testing
    async def _get_fallback_room_state(self, room_name: str) -> Dict[str, Any]:
        """Fallback to in-memory state when Redis unavailable"""
        from .consumers import game_room_manager
        room_data = await game_room_manager.get_room(room_name)
        return room_data if room_data else self._create_default_room_state(room_name)
    
    async def _update_fallback_room_state(self, room_name: str, updates: Dict[str, Any]):
        """Fallback update for in-memory state"""
        from .consumers import game_room_manager
        room_data = await game_room_manager.get_room(room_name)
        if not room_data:
            await game_room_manager.create_room(room_name, self._create_default_room_state(room_name))
        await game_room_manager.update_room(room_name, lambda room: room.update(updates))
    
    def _create_default_room_state(self, room_name: str) -> Dict[str, Any]:
        """Create default room state structure"""
        return {
            'room_name': room_name,
            'players': [],
            'current_round': None,
            'time_remaining': 0,
            'phase': 'waiting',
            'betting_closed': False,
            'has_active_round': False,
            'total_bets': 0,
            'total_amount': 0,
            'recent_results': [],
            'betting_stats': {
                'red': {'count': 0, 'amount': 0},
                'green': {'count': 0, 'amount': 0},
                'violet': {'count': 0, 'amount': 0}
            },
            'created_at': time.time(),
            'last_updated': time.time()
        }

# Global instance
redis_game_state = RedisGameStateManager()
