"""
WebSocket authentication middleware for secure WebSocket connections.
"""

import logging
from channels.middleware import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.sessions.models import Session
from django.utils import timezone
from .models import Player, Admin
from .security import SecurityAuditLogger, get_client_ip

logger = logging.getLogger(__name__)


class WebSocketAuthMiddleware(BaseMiddleware):
    """
    Custom WebSocket authentication middleware.

    Validates user sessions and adds user information to WebSocket scope.
    """

    def get_client_ip_from_scope(self, scope):
        """Extract client IP from WebSocket scope"""
        # Get client IP from scope
        client = scope.get('client', ['127.0.0.1', 0])
        if client and len(client) >= 1:
            return client[0]

        # Fallback: try to get from headers
        headers = dict(scope.get('headers', []))
        x_forwarded_for = headers.get(b'x-forwarded-for')
        if x_forwarded_for:
            return x_forwarded_for.decode('utf-8').split(',')[0].strip()

        x_real_ip = headers.get(b'x-real-ip')
        if x_real_ip:
            return x_real_ip.decode('utf-8').strip()

        # Default fallback
        return '127.0.0.1'

    async def __call__(self, scope, receive, send):
        # Only apply to WebSocket connections
        if scope['type'] != 'websocket':
            return await super().__call__(scope, receive, send)

        # Get session from scope
        session = scope.get('session', {})

        # Get client IP for logging
        client_ip = self._get_client_ip(scope)

        logger.debug(f"WebSocket connection attempt from {client_ip}")
        logger.debug(f"Session keys: {list(session.keys())}")

        # Initialize user information
        scope['user'] = None
        scope['player'] = None
        scope['admin'] = None
        scope['authenticated'] = False
        
        # Check for user authentication
        if session.get('is_authenticated') and session.get('user_id'):
            try:
                player = await database_sync_to_async(Player.objects.get)(
                    id=session['user_id'],
                    is_active=True
                )
                scope['user'] = player
                scope['player'] = player
                scope['authenticated'] = True
                
                logger.debug(f"WebSocket authenticated user: {player.username}")
                
            except Player.DoesNotExist:
                logger.warning(f"WebSocket authentication failed: User {session.get('user_id')} not found")
                # Clear invalid session
                session.flush()
        
        # Check for admin authentication with enhanced security
        elif session.get('admin_id'):
            try:
                admin = await database_sync_to_async(Admin.objects.get)(
                    id=session['admin_id'],
                    is_active=True
                )

                # Validate admin session integrity
                stored_ip = session.get('ip_address')
                current_ip = self.get_client_ip_from_scope(scope)

                # Allow IP changes for admins but log them for security
                if stored_ip and stored_ip != current_ip:
                    logger.warning(f"Admin {admin.username} IP changed from {stored_ip} to {current_ip}")
                    await database_sync_to_async(SecurityAuditLogger.log_security_event)(
                        'admin_ip_change',
                        user_id=admin.id,
                        ip_address=current_ip,
                        details={
                            'old_ip': stored_ip,
                            'new_ip': current_ip,
                            'admin_username': admin.username
                        }
                    )

                # Admin sessions never expire - unlimited time (consistent with admin_required decorator)
                scope['admin'] = admin
                scope['authenticated'] = True
                scope['user_type'] = 'admin'

                # Update last activity with enhanced tracking
                session['admin_last_activity'] = timezone.now().isoformat()
                session['ip_address'] = current_ip  # Update current IP

                logger.info(f"WebSocket authenticated admin: {admin.username} from {current_ip}")

            except Admin.DoesNotExist:
                logger.warning(f"WebSocket authentication failed: Admin {session.get('admin_id')} not found")
                await database_sync_to_async(SecurityAuditLogger.log_security_event)(
                    'invalid_admin_websocket_auth',
                    user_id=session.get('admin_id'),
                    ip_address=get_client_ip({'META': dict(scope.get('headers', []))}),
                    details={'session_admin_id': session.get('admin_id')}
                )
                session.flush()
        else:
            # Log session data for debugging
            logger.info(f"WebSocket authentication failed - Session data: {dict(session)}")
        
        # Log WebSocket connection attempt
        client_ip = self._get_client_ip(scope)
        user_info = None
        
        if scope.get('player'):
            user_info = f"user:{scope['player'].username}"
        elif scope.get('admin'):
            user_info = f"admin:{scope['admin'].username}"
        else:
            user_info = "anonymous"
        
        logger.info(f"WebSocket connection: {user_info} from {client_ip}")
        
        # Log security event for monitoring
        SecurityAuditLogger.log_security_event(
            'websocket_connection',
            user_id=scope.get('player', {}).id if scope.get('player') else None,
            ip_address=client_ip,
            details={
                'authenticated': scope['authenticated'],
                'user_type': 'admin' if scope.get('admin') else 'player' if scope.get('player') else 'anonymous',
                'path': scope.get('path', ''),
            }
        )
        
        return await super().__call__(scope, receive, send)
    
    def _get_client_ip(self, scope):
        """Extract client IP from WebSocket scope"""
        headers = dict(scope.get('headers', []))
        
        # Check for forwarded IP headers
        forwarded_for = headers.get(b'x-forwarded-for')
        if forwarded_for:
            return forwarded_for.decode().split(',')[0].strip()
        
        real_ip = headers.get(b'x-real-ip')
        if real_ip:
            return real_ip.decode().strip()
        
        # Fall back to client address
        client = scope.get('client', ['unknown', 0])
        return client[0] if client else 'unknown'


class WebSocketRateLimitMiddleware(BaseMiddleware):
    """
    Rate limiting middleware for WebSocket connections.
    """
    
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'websocket':
            return await super().__call__(scope, receive, send)
        
        client_ip = self._get_client_ip(scope)
        
        # Check rate limits
        if await self._is_rate_limited(client_ip, scope):
            # Close connection with rate limit code
            await send({
                'type': 'websocket.close',
                'code': 4029  # Custom code for rate limiting
            })
            return
        
        return await super().__call__(scope, receive, send)
    
    async def _is_rate_limited(self, client_ip, scope):
        """Check if client is rate limited"""
        from django.core.cache import cache
        from django.conf import settings

        # Skip rate limiting for admin users (as per user preference)
        if 'admin' in scope.get('path', '') or 'control-panel' in scope.get('path', ''):
            # Admin users should have unlimited access
            return False

        # Rate limiting only for regular user WebSocket connections
        limit_key = f"ws_rate_limit:user:{client_ip}"

        # More generous limits for development
        if getattr(settings, 'DEBUG', False):
            max_connections = 50  # Very high limit for development
            timeout = 300  # 5 minutes timeout
        else:
            max_connections = 20  # Production limit for users
            timeout = 60  # 1 minute timeout

        current_connections = cache.get(limit_key, 0)

        if current_connections >= max_connections:
            SecurityAuditLogger.log_security_event(
                'websocket_rate_limit_exceeded',
                ip_address=client_ip,
                details={
                    'current_connections': current_connections,
                    'max_connections': max_connections,
                    'path': scope.get('path', ''),
                    'user_type': 'user'
                }
            )
            return True

        # Increment connection count with appropriate timeout
        cache.set(limit_key, current_connections + 1, timeout)
        return False
    
    def _get_client_ip(self, scope):
        """Extract client IP from WebSocket scope"""
        headers = dict(scope.get('headers', []))
        
        forwarded_for = headers.get(b'x-forwarded-for')
        if forwarded_for:
            return forwarded_for.decode().split(',')[0].strip()
        
        real_ip = headers.get(b'x-real-ip')
        if real_ip:
            return real_ip.decode().strip()
        
        client = scope.get('client', ['unknown', 0])
        return client[0] if client else 'unknown'


class WebSocketSecurityMiddleware(BaseMiddleware):
    """
    Security middleware for WebSocket connections.
    """
    
    async def __call__(self, scope, receive, send):
        if scope['type'] != 'websocket':
            return await super().__call__(scope, receive, send)
        
        # Enhanced origin validation
        if not await self._validate_origin(scope):
            headers = dict(scope.get('headers', []))
            origin = headers.get(b'origin', b'').decode()
            client_ip = get_client_ip({'META': dict(headers)})

            logger.warning(f"WebSocket origin validation failed for: {origin} from {client_ip}")

            # Log security event
            await database_sync_to_async(SecurityAuditLogger.log_security_event)(
                'websocket_invalid_origin',
                ip_address=client_ip,
                details={
                    'origin': origin,
                    'path': scope.get('path', ''),
                    'user_agent': headers.get(b'user-agent', b'').decode()
                }
            )

            await send({
                'type': 'websocket.close',
                'code': 4003  # Forbidden origin
            })
            return
        
        # Check for suspicious patterns
        if await self._is_suspicious_connection(scope):
            await send({
                'type': 'websocket.close',
                'code': 4004  # Suspicious activity
            })
            return
        
        return await super().__call__(scope, receive, send)
    
    async def _validate_origin(self, scope):
        """Enhanced WebSocket origin validation with security improvements"""
        from django.conf import settings
        import re
        from urllib.parse import urlparse

        headers = dict(scope.get('headers', []))
        origin = headers.get(b'origin')

        if not origin:
            logger.warning("WebSocket connection attempted without origin header")
            return False  # Require origin header for security

        try:
            origin = origin.decode('utf-8')
        except UnicodeDecodeError:
            logger.warning("WebSocket origin header contains invalid UTF-8")
            return False

        # Validate origin format
        if not re.match(r'^https?://[a-zA-Z0-9.-]+(?::[0-9]+)?$', origin):
            logger.warning(f"WebSocket origin has invalid format: {origin}")
            return False

        # Parse origin URL for validation
        try:
            parsed = urlparse(origin)
            if not parsed.hostname:
                logger.warning(f"WebSocket origin missing hostname: {origin}")
                return False
        except Exception as e:
            logger.warning(f"Failed to parse WebSocket origin {origin}: {e}")
            return False

        logger.debug(f"WebSocket origin validation for: {origin}")

        # In development mode, be more permissive but still secure
        if getattr(settings, 'DEBUG', False):
            # Allow specific development domains only
            dev_patterns = [
                r'^https?://localhost(:[0-9]+)?$',
                r'^https?://127\.0\.0\.1(:[0-9]+)?$',
                r'^https?://.*\.ngrok-free\.app$',
                r'^https?://.*\.ngrok\.io$'
            ]

            for pattern in dev_patterns:
                if re.match(pattern, origin):
                    logger.debug(f"WebSocket origin allowed (development): {origin}")
                    return True

        # Check against explicitly allowed origins
        allowed_origins = getattr(settings, 'WS_ALLOWED_ORIGINS', [])
        if allowed_origins:
            for allowed in allowed_origins:
                if allowed.startswith('*'):
                    # Handle wildcard patterns securely
                    pattern = re.escape(allowed[1:])  # Escape special regex chars
                    if re.search(pattern, origin):
                        logger.debug(f"WebSocket origin allowed (wildcard): {origin}")
                        return True
                elif origin == allowed:  # Exact match only
                    logger.debug(f"WebSocket origin allowed (exact): {origin}")
                    return True

        # Fall back to ALLOWED_HOSTS check with protocol validation
        allowed_hosts = getattr(settings, 'ALLOWED_HOSTS', [])
        if allowed_hosts:
            for host in allowed_hosts:
                if host == '*':
                    continue  # Skip wildcard in production

                # Check both HTTP and HTTPS
                allowed_origins_from_hosts = [
                    f"http://{host}",
                    f"https://{host}"
                ]

                if origin in allowed_origins_from_hosts:
                    logger.debug(f"WebSocket origin allowed (ALLOWED_HOSTS): {origin}")
                    return True

        return False
    
    async def _is_suspicious_connection(self, scope):
        """Detect suspicious WebSocket connection patterns"""
        headers = dict(scope.get('headers', []))
        
        # Check user agent
        user_agent = headers.get(b'user-agent', b'').decode().lower()
        
        # Block known bot user agents
        bot_indicators = ['bot', 'crawler', 'spider', 'scraper']
        if any(indicator in user_agent for indicator in bot_indicators):
            return True
        
        # Check for missing standard headers
        if not headers.get(b'user-agent'):
            return True
        return False
