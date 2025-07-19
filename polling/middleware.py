"""
Custom middleware for security, authentication, and rate limiting.
"""

import json
import time
import hashlib
import logging
from django.http import JsonResponse
from django.core.cache import cache
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from .models import Player, Admin
from .security import get_client_ip, SecurityAuditLogger

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses"""

    def process_response(self, request, response):
        # Skip all security headers for debug routes to test Chrome compatibility
        debug_routes = ['/test-chrome/', '/minimal-login/', '/debug/']
        if settings.DEBUG and any(request.path.startswith(route) for route in debug_routes):
            # Remove all security headers for debugging Chrome issues
            headers_to_remove = [
                'X-Frame-Options', 'Content-Security-Policy', 'X-XSS-Protection',
                'Referrer-Policy', 'Permissions-Policy', 'Cross-Origin-Opener-Policy'
            ]
            for header in headers_to_remove:
                if header in response:
                    del response[header]
            # Keep only minimal headers
            response['X-Content-Type-Options'] = 'nosniff'
            return response

        # Security headers - Relaxed for debugging Chrome issues
        response['X-Content-Type-Options'] = 'nosniff'
        if settings.DEBUG:
            response['X-Frame-Options'] = 'SAMEORIGIN'  # Less restrictive for development
        else:
            response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Only add HSTS in production with HTTPS
        if not settings.DEBUG and request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        # Content Security Policy - Skip for debug routes
        debug_routes = ['/test-chrome/', '/minimal-login/', '/debug/']
        if settings.DEBUG and any(request.path.startswith(route) for route in debug_routes):
            # No CSP for debug routes
            pass
        elif settings.DEBUG:
            # More permissive CSP for development/debugging
            csp_directives = [
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://checkout.razorpay.com",
                "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
                "img-src 'self' data: https:",
                "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com",
                "connect-src 'self' ws: wss: https://api.razorpay.com https://lumberjack.razorpay.com",
                "frame-src 'self' https://api.razorpay.com https://checkout.razorpay.com",
                "frame-ancestors 'self'",
            ]
            response['Content-Security-Policy'] = '; '.join(csp_directives)
        else:
            # Strict CSP for production
            csp_directives = [
                "default-src 'self'",
                "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://checkout.razorpay.com",
                "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com",
                "img-src 'self' data: https:",
                "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com",
                "connect-src 'self' ws: wss: https://api.razorpay.com https://lumberjack.razorpay.com",
                "frame-src 'self' https://api.razorpay.com https://checkout.razorpay.com",
                "frame-ancestors 'none'",
            ]
            response['Content-Security-Policy'] = '; '.join(csp_directives)

        # Permissions Policy (replaces Feature Policy) - removed unsupported features
        permissions_policy = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=(self)",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()"
        ]
        response['Permissions-Policy'] = ', '.join(permissions_policy)

        return response


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting middleware for API endpoints"""
    
    def process_request(self, request):
        # Skip rate limiting for all admin panel requests (admin users should have unlimited access)
        if request.path.startswith('/control-panel/'):
            return None
        
        # Get client IP
        client_ip = get_client_ip(request)
        
        # Different rate limits for different endpoints
        if request.path.startswith('/api/'):
            return self._check_api_rate_limit(request, client_ip)
        elif request.path.startswith('/control-panel/api/'):
            return self._check_admin_api_rate_limit(request, client_ip)
        
        return None
    
    def _check_api_rate_limit(self, request, client_ip):
        """Check rate limit for public API endpoints"""
        # Per-minute limit
        minute_key = f"rate_limit:api:{client_ip}:{int(time.time() // 60)}"
        minute_count = cache.get(minute_key, 0)
        
        if minute_count >= getattr(settings, 'API_RATE_LIMIT_PER_MINUTE', 60):
            SecurityAuditLogger.log_security_event(
                'api_rate_limit_exceeded',
                ip_address=client_ip,
                details={'endpoint': request.path, 'limit_type': 'per_minute'}
            )
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests per minute'
            }, status=429)
        
        # Per-hour limit
        hour_key = f"rate_limit:api:{client_ip}:{int(time.time() // 3600)}"
        hour_count = cache.get(hour_key, 0)
        
        if hour_count >= getattr(settings, 'API_RATE_LIMIT_PER_HOUR', 1000):
            SecurityAuditLogger.log_security_event(
                'api_rate_limit_exceeded',
                ip_address=client_ip,
                details={'endpoint': request.path, 'limit_type': 'per_hour'}
            )
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many requests per hour'
            }, status=429)
        
        # Increment counters
        cache.set(minute_key, minute_count + 1, 60)
        cache.set(hour_key, hour_count + 1, 3600)
        
        return None
    
    def _check_admin_api_rate_limit(self, request, client_ip):
        """Check rate limit for admin API endpoints"""
        # More lenient rate limiting for admin APIs
        minute_key = f"rate_limit:admin_api:{client_ip}:{int(time.time() // 60)}"
        minute_count = cache.get(minute_key, 0)
        
        admin_limit = getattr(settings, 'ADMIN_PANEL_RATE_LIMIT', 100)
        if minute_count >= admin_limit:
            SecurityAuditLogger.log_security_event(
                'admin_api_rate_limit_exceeded',
                ip_address=client_ip,
                details={'endpoint': request.path}
            )
            return JsonResponse({
                'error': 'Rate limit exceeded',
                'message': 'Too many admin API requests per minute'
            }, status=429)
        
        cache.set(minute_key, minute_count + 1, 60)
        return None


class AuthenticationMiddleware(MiddlewareMixin):
    """Custom authentication middleware for API requests"""
    
    def process_request(self, request):
        # Add user object to request for session-based auth
        request.user = AnonymousUser()
        request.player = None
        request.admin = None
        
        # Check for user session authentication
        if request.session.get('is_authenticated') and request.session.get('user_id'):
            try:
                player = Player.objects.get(
                    id=request.session['user_id'],
                    is_active=True
                )
                request.user = player
                request.player = player
            except Player.DoesNotExist:
                request.session.flush()
        
        # Check for admin session authentication
        if request.session.get('admin_id'):
            try:
                admin = Admin.objects.get(
                    id=request.session['admin_id'],
                    is_active=True
                )
                request.admin = admin
            except Admin.DoesNotExist:
                request.session.flush()
        
        return None


class APISecurityMiddleware(MiddlewareMixin):
    """Security middleware specifically for API endpoints"""
    
    def process_request(self, request):
        # Only apply to API endpoints
        if not request.path.startswith('/api/') and not request.path.startswith('/control-panel/api/'):
            return None
        
        # Log API access
        client_ip = get_client_ip(request)
        user_id = getattr(request, 'player', None)
        user_id = user_id.id if user_id else None
        
        logger.info(f"API Access: {request.method} {request.path} from {client_ip} user:{user_id}")
        
        # Check for suspicious patterns
        if self._is_suspicious_request(request):
            SecurityAuditLogger.log_security_event(
                'suspicious_api_request',
                user_id=user_id,
                ip_address=client_ip,
                details={
                    'method': request.method,
                    'path': request.path,
                    'user_agent': request.META.get('HTTP_USER_AGENT', '')
                }
            )
        
        return None
    
    def _is_suspicious_request(self, request):
        """Detect suspicious request patterns"""
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        # Check for bot-like user agents
        bot_indicators = ['bot', 'crawler', 'spider', 'scraper', 'curl', 'wget']
        if any(indicator in user_agent for indicator in bot_indicators):
            return True
        
        # Check for missing or suspicious headers
        if not request.META.get('HTTP_REFERER') and request.method == 'POST':
            return True
        
        # Check for unusual request patterns
        if len(request.path) > 200:  # Unusually long paths
            return True
        
        return False


class CSRFExemptionMiddleware(MiddlewareMixin):
    """Handle CSRF exemption for specific API endpoints"""

    def process_request(self, request):
        # Exempt WebSocket upgrade requests
        if request.META.get('HTTP_UPGRADE', '').lower() == 'websocket':
            setattr(request, '_dont_enforce_csrf_checks', True)
            return None

        # Exempt specific API endpoints that handle CSRF manually
        # Only exempt read-only endpoints or those with their own security
        exempt_paths = [
            '/api/player/',  # Player stats API (read-only)
            '/webhooks/razorpay/',  # Payment webhook (has signature verification)
        ]

        # Only exempt exact paths, not partial matches
        if any(request.path.startswith(path) for path in exempt_paths):
            # Log CSRF exemptions in debug mode
            if settings.DEBUG:
                logger = logging.getLogger(__name__)
                logger.debug(f"CSRF exemption for path: {request.path}")

            setattr(request, '_dont_enforce_csrf_checks', True)

        return None
