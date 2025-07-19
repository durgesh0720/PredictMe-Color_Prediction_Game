"""
WebSocket Message Reliability System
Implements guaranteed message delivery with acknowledgments and retry mechanisms
"""
import asyncio
import json
import logging
import time
import uuid
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, asdict
from channels.layers import get_channel_layer

logger = logging.getLogger(__name__)

@dataclass
class PendingMessage:
    """Represents a message waiting for acknowledgment"""
    message_id: str
    message_data: dict
    target_group: str
    target_channel: Optional[str]
    timestamp: float
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 10.0  # seconds
    critical: bool = False  # Critical messages get more retries

class ReliableWebSocketManager:
    """
    Manages reliable WebSocket message delivery with acknowledgments and retries
    """
    
    def __init__(self):
        self.pending_messages: Dict[str, PendingMessage] = {}
        self.channel_layer = get_channel_layer()
        self.cleanup_task: Optional[asyncio.Task] = None
        self.retry_task: Optional[asyncio.Task] = None
        self.message_handlers: Dict[str, Callable] = {}
        
        # Configuration
        self.cleanup_interval = 30  # seconds
        self.retry_interval = 5     # seconds
        self.max_pending_messages = 1000
        
        # Start background tasks
        self._start_background_tasks()
    
    def _start_background_tasks(self):
        """Start background tasks for cleanup and retry"""
        if not self.cleanup_task or self.cleanup_task.done():
            self.cleanup_task = asyncio.create_task(self._cleanup_expired_messages())
        
        if not self.retry_task or self.retry_task.done():
            self.retry_task = asyncio.create_task(self._retry_failed_messages())
    
    async def send_reliable_message(
        self, 
        group_name: str, 
        message_data: dict, 
        critical: bool = False,
        timeout: float = 10.0,
        max_retries: int = 3
    ) -> str:
        """
        Send a message with guaranteed delivery
        Returns message_id for tracking
        """
        message_id = str(uuid.uuid4())
        
        # Add reliability metadata
        enhanced_message = {
            **message_data,
            'message_id': message_id,
            'requires_ack': True,
            'timestamp': time.time()
        }
        
        # Store pending message
        pending_msg = PendingMessage(
            message_id=message_id,
            message_data=enhanced_message,
            target_group=group_name,
            target_channel=None,
            timestamp=time.time(),
            max_retries=max_retries if not critical else max_retries * 2,
            timeout=timeout,
            critical=critical
        )
        
        self.pending_messages[message_id] = pending_msg
        
        # Send initial message
        try:
            await self.channel_layer.group_send(group_name, enhanced_message)
            logger.debug(f"Sent reliable message {message_id} to group {group_name}")
        except Exception as e:
            logger.error(f"Failed to send message {message_id}: {e}")
            # Will be retried by retry task
        
        return message_id
    
    async def send_reliable_message_to_channel(
        self, 
        channel_name: str, 
        message_data: dict, 
        critical: bool = False,
        timeout: float = 10.0,
        max_retries: int = 3
    ) -> str:
        """
        Send a message to specific channel with guaranteed delivery
        """
        message_id = str(uuid.uuid4())
        
        enhanced_message = {
            **message_data,
            'message_id': message_id,
            'requires_ack': True,
            'timestamp': time.time()
        }
        
        pending_msg = PendingMessage(
            message_id=message_id,
            message_data=enhanced_message,
            target_group="",
            target_channel=channel_name,
            timestamp=time.time(),
            max_retries=max_retries if not critical else max_retries * 2,
            timeout=timeout,
            critical=critical
        )
        
        self.pending_messages[message_id] = pending_msg
        
        try:
            await self.channel_layer.send(channel_name, enhanced_message)
            logger.debug(f"Sent reliable message {message_id} to channel {channel_name}")
        except Exception as e:
            logger.error(f"Failed to send message {message_id} to channel: {e}")
        
        return message_id
    
    async def acknowledge_message(self, message_id: str, channel_name: str = None):
        """
        Acknowledge receipt of a message
        """
        if message_id in self.pending_messages:
            del self.pending_messages[message_id]
            logger.debug(f"Acknowledged message {message_id}")
        else:
            logger.warning(f"Attempted to acknowledge unknown message {message_id}")
    
    async def _retry_failed_messages(self):
        """Background task to retry failed messages"""
        while True:
            try:
                await asyncio.sleep(self.retry_interval)
                
                current_time = time.time()
                messages_to_retry = []
                
                for msg_id, pending_msg in list(self.pending_messages.items()):
                    if current_time - pending_msg.timestamp > pending_msg.timeout:
                        if pending_msg.retry_count < pending_msg.max_retries:
                            messages_to_retry.append(pending_msg)
                        else:
                            # Max retries exceeded
                            logger.error(f"Message {msg_id} failed after {pending_msg.retry_count} retries")
                            del self.pending_messages[msg_id]
                
                # Retry messages
                for pending_msg in messages_to_retry:
                    try:
                        pending_msg.retry_count += 1
                        pending_msg.timestamp = current_time
                        
                        if pending_msg.target_channel:
                            await self.channel_layer.send(
                                pending_msg.target_channel, 
                                pending_msg.message_data
                            )
                        else:
                            await self.channel_layer.group_send(
                                pending_msg.target_group, 
                                pending_msg.message_data
                            )
                        
                        logger.info(f"Retried message {pending_msg.message_id} (attempt {pending_msg.retry_count})")
                        
                    except Exception as e:
                        logger.error(f"Failed to retry message {pending_msg.message_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in retry task: {e}")
    
    async def _cleanup_expired_messages(self):
        """Background task to clean up expired messages"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                
                current_time = time.time()
                expired_messages = []
                
                for msg_id, pending_msg in list(self.pending_messages.items()):
                    # Clean up messages that are too old (even if not max retries)
                    if current_time - pending_msg.timestamp > (pending_msg.timeout * 5):
                        expired_messages.append(msg_id)
                
                for msg_id in expired_messages:
                    if msg_id in self.pending_messages:
                        del self.pending_messages[msg_id]
                        logger.warning(f"Cleaned up expired message {msg_id}")
                
                # Prevent memory leaks
                if len(self.pending_messages) > self.max_pending_messages:
                    # Remove oldest messages
                    sorted_messages = sorted(
                        self.pending_messages.items(),
                        key=lambda x: x[1].timestamp
                    )
                    
                    to_remove = len(self.pending_messages) - self.max_pending_messages
                    for i in range(to_remove):
                        msg_id = sorted_messages[i][0]
                        del self.pending_messages[msg_id]
                        logger.warning(f"Removed old message {msg_id} due to memory limit")
                
            except Exception as e:
                logger.error(f"Error in cleanup task: {e}")
    
    def get_pending_count(self) -> int:
        """Get number of pending messages"""
        return len(self.pending_messages)
    
    def get_stats(self) -> dict:
        """Get reliability statistics"""
        current_time = time.time()
        
        total_pending = len(self.pending_messages)
        overdue_count = sum(
            1 for msg in self.pending_messages.values()
            if current_time - msg.timestamp > msg.timeout
        )
        critical_count = sum(
            1 for msg in self.pending_messages.values()
            if msg.critical
        )
        
        return {
            'total_pending': total_pending,
            'overdue_messages': overdue_count,
            'critical_messages': critical_count,
            'cleanup_task_running': not (self.cleanup_task and self.cleanup_task.done()),
            'retry_task_running': not (self.retry_task and self.retry_task.done())
        }
    
    async def shutdown(self):
        """Gracefully shutdown the manager"""
        if self.cleanup_task and not self.cleanup_task.done():
            self.cleanup_task.cancel()
        
        if self.retry_task and not self.retry_task.done():
            self.retry_task.cancel()
        
        logger.info("WebSocket reliability manager shutdown")

# Global instance
reliable_ws_manager = ReliableWebSocketManager()
