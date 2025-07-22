"""
WebSocket security utilities for rate limiting and validation
"""
import time
import json
import logging
from typing import Dict, Any, Optional
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class WebSocketRateLimiter:
    """Rate limiter for WebSocket connections"""
    
    def __init__(self):
        # Connection-based rate limiting
        self.connection_attempts = defaultdict(deque)  # IP -> timestamps
        self.message_counts = defaultdict(deque)       # connection_id -> timestamps
        
        # Limits
        self.max_connections_per_ip = 5
        self.max_messages_per_minute = 60
        self.connection_window = 300  # 5 minutes
        self.message_window = 60      # 1 minute
        
    def check_connection_rate(self, ip_address: str) -> bool:
        """Check if IP can establish new connection"""
        now = time.time()
        
        # Clean old attempts
        attempts = self.connection_attempts[ip_address]
        while attempts and attempts[0] < now - self.connection_window:
            attempts.popleft()
        
        # Check limit
        if len(attempts) >= self.max_connections_per_ip:
            logger.warning(f"Rate limit exceeded for IP {ip_address}: {len(attempts)} connections")
            return False
        
        # Record attempt
        attempts.append(now)
        return True
    
    def check_message_rate(self, connection_id: str) -> bool:
        """Check if connection can send message"""
        now = time.time()
        
        # Clean old messages
        messages = self.message_counts[connection_id]
        while messages and messages[0] < now - self.message_window:
            messages.popleft()
        
        # Check limit
        if len(messages) >= self.max_messages_per_minute:
            logger.warning(f"Message rate limit exceeded for connection {connection_id}")
            return False
        
        # Record message
        messages.append(now)
        return True
    
    def cleanup_connection(self, connection_id: str):
        """Clean up rate limiting data for disconnected connection"""
        if connection_id in self.message_counts:
            del self.message_counts[connection_id]

class WebSocketValidator:
    """Validator for WebSocket messages"""
    
    MAX_MESSAGE_SIZE = 10 * 1024  # 10KB
    MAX_STRING_LENGTH = 1000
    
    @classmethod
    def validate_message_size(cls, message: bytes) -> bool:
        """Validate message size"""
        if len(message) > cls.MAX_MESSAGE_SIZE:
            logger.warning(f"Message too large: {len(message)} bytes")
            return False
        return True
    
    @classmethod
    def validate_json_message(cls, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate JSON message structure and content"""
        try:
            # Check required fields
            if 'type' not in data:
                return False, "Missing 'type' field"
            
            message_type = data['type']
            if not isinstance(message_type, str) or len(message_type) > 50:
                return False, "Invalid message type"
            
            # Validate specific message types
            if message_type == 'place_bet':
                return cls._validate_bet_message(data)
            elif message_type == 'admin_select_color':
                return cls._validate_admin_color_message(data)
            elif message_type == 'heartbeat':
                return cls._validate_heartbeat_message(data)
            
            return True, None
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    @classmethod
    def _validate_bet_message(cls, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate bet placement message"""
        required_fields = ['color', 'amount', 'round_id']  # Re-enabled round_id validation

        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate color
        valid_colors = ['red', 'green', 'violet']
        if data['color'] not in valid_colors:
            return False, f"Invalid color '{data['color']}'. Valid colors are: {', '.join(valid_colors)}"
        
        # Validate amount
        try:
            amount = float(data['amount'])
            if amount <= 0 or amount > 10000:  # Max ₹100
                return False, f"Invalid bet amount: {amount}"
        except (ValueError, TypeError):
            return False, "Invalid amount format"
        
        # Validate round_id (accept both string and integer, but not None)
        round_id = data.get('round_id')
        if round_id is None:
            return False, "Missing required field: round_id"

        if isinstance(round_id, int):
            # Convert integer to string for consistency
            round_id = str(round_id)
            data['round_id'] = round_id
        elif not isinstance(round_id, str):
            return False, "Invalid round_id type"

        if len(round_id) > 50:
            return False, "Invalid round_id length"
        
        # Validate timestamp (prevent replay attacks)
        timestamp = data.get('timestamp')
        if timestamp:
            try:
                msg_time = float(timestamp)
                now = time.time()
                if abs(now - msg_time) > 30:  # 30 second window
                    return False, "Message timestamp too old or future"
            except (ValueError, TypeError):
                return False, "Invalid timestamp format"
        
        return True, None
    
    @classmethod
    def _validate_admin_color_message(cls, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate admin color selection message"""
        required_fields = ['round_id', 'color']
        
        for field in required_fields:
            if field not in data:
                return False, f"Missing required field: {field}"
        
        # Validate color
        valid_colors = ['red', 'green', 'violet']
        if data['color'] not in valid_colors:
            return False, f"Invalid color: {data['color']}"
        
        # Validate round_id (accept both string and integer, but not None)
        round_id = data.get('round_id')
        if round_id is None:
            return False, "Missing required field: round_id"

        if isinstance(round_id, int):
            # Convert integer to string for consistency
            round_id = str(round_id)
            data['round_id'] = round_id
        elif not isinstance(round_id, str):
            return False, "Invalid round_id type"

        if len(round_id) > 50:
            return False, "Invalid round_id length"
        
        return True, None
    
    @classmethod
    def _validate_heartbeat_message(cls, data: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate heartbeat message"""
        # Heartbeat can be simple
        return True, None
    
    @classmethod
    def sanitize_string(cls, value: str) -> str:
        """Sanitize string input"""
        if not isinstance(value, str):
            return str(value)
        
        # Truncate if too long
        if len(value) > cls.MAX_STRING_LENGTH:
            value = value[:cls.MAX_STRING_LENGTH]
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
        for char in dangerous_chars:
            value = value.replace(char, '')
        
        return value.strip()

# Global instances
rate_limiter = WebSocketRateLimiter()
validator = WebSocketValidator()
