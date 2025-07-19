# Enhanced Security utilities for Color Prediction Game

import hashlib
import hmac
import secrets
import time
import logging
import json
import base64
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.http import HttpResponseForbidden, JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_exempt
from functools import wraps
import re
import ipaddress
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Rate limiting
class RateLimiter:
    """Simple rate limiter using Django cache"""
    
    @staticmethod
    def is_rate_limited(key, limit, window_seconds):
        """
        Check if a key is rate limited
        
        Args:
            key: Unique identifier (e.g., IP address, user ID)
            limit: Maximum number of requests allowed
            window_seconds: Time window in seconds
            
        Returns:
            bool: True if rate limited, False otherwise
        """
        cache_key = f"rate_limit:{key}"
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        # Get current requests in window
        requests = cache.get(cache_key, [])
        
        # Filter requests within current window
        requests = [req_time for req_time in requests if req_time > window_start]
        
        # Check if limit exceeded
        if len(requests) >= limit:
            return True
        
        # Add current request
        requests.append(current_time)
        
        # Store updated requests list
        cache.set(cache_key, requests, window_seconds)
        
        return False
    
    @staticmethod
    def get_remaining_requests(key, limit, window_seconds):
        """Get remaining requests for a key"""
        cache_key = f"rate_limit:{key}"
        current_time = int(time.time())
        window_start = current_time - window_seconds
        
        requests = cache.get(cache_key, [])
        requests = [req_time for req_time in requests if req_time > window_start]
        
        return max(0, limit - len(requests))

# Security decorators
def rate_limit(limit=10, window=60, key_func=None):
    """
    Rate limiting decorator
    
    Args:
        limit: Maximum requests allowed
        window: Time window in seconds
        key_func: Function to generate rate limit key (default: uses IP)
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if key_func:
                key = key_func(request)
            else:
                key = get_client_ip(request)
            
            if RateLimiter.is_rate_limited(key, limit, window):
                logger.warning(f"Rate limit exceeded for {key}")
                return HttpResponseForbidden("Rate limit exceeded. Please try again later.")
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def login_rate_limit(view_func):
    """Rate limit for login attempts"""
    return rate_limit(limit=5, window=300)(view_func)  # 5 attempts per 5 minutes

def api_rate_limit(view_func):
    """Rate limit for API endpoints"""
    return rate_limit(limit=100, window=60)(view_func)  # 100 requests per minute

# IP and client information
def get_client_ip(request):
    """Get client IP address from request or scope"""
    # Handle Django request objects
    if hasattr(request, 'META'):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    # Handle WebSocket scope or dictionary format
    elif isinstance(request, dict):
        meta = request.get('META', {})
        x_forwarded_for = meta.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = meta.get('REMOTE_ADDR')
        return ip

    # Fallback for unknown format
    else:
        return '127.0.0.1'

def get_user_agent(request):
    """Get user agent from request"""
    return request.META.get('HTTP_USER_AGENT', '')

# Session security
class SessionSecurity:
    """Enhanced session security"""
    
    @staticmethod
    def create_secure_session(request, user):
        """Create a secure session for user"""
        # Clear any existing session
        request.session.flush()
        
        # Set user session data
        request.session['user_id'] = user.id
        request.session['username'] = user.username
        request.session['is_authenticated'] = True
        request.session['login_time'] = timezone.now().isoformat()
        request.session['ip_address'] = get_client_ip(request)
        request.session['user_agent_hash'] = hashlib.sha256(
            get_user_agent(request).encode()
        ).hexdigest()
        
        # Update user's last login
        user.update_last_login()
        
        # Log successful login
        logger.info(f"User {user.username} logged in from {get_client_ip(request)}")
    
    @staticmethod
    def validate_session(request):
        """Validate session security"""
        if not request.session.get('is_authenticated'):
            return False
        
        # Check IP address consistency (optional, can be disabled for mobile users)
        stored_ip = request.session.get('ip_address')
        current_ip = get_client_ip(request)
        
        # Check user agent consistency
        stored_ua_hash = request.session.get('user_agent_hash')
        current_ua_hash = hashlib.sha256(
            get_user_agent(request).encode()
        ).hexdigest()
        
        if stored_ua_hash != current_ua_hash:
            logger.warning(f"User agent mismatch for session {request.session.session_key}")
            return False
        
        # Check session age
        login_time_str = request.session.get('login_time')
        if login_time_str:
            login_time = datetime.fromisoformat(login_time_str.replace('Z', '+00:00'))
            if timezone.now() - login_time > timedelta(hours=24):
                logger.info(f"Session expired for user {request.session.get('username')}")
                return False
        
        return True
    
    @staticmethod
    def invalidate_session(request):
        """Safely invalidate session"""
        user_id = request.session.get('user_id')
        username = request.session.get('username')
        
        request.session.flush()
        
        if username:
            logger.info(f"Session invalidated for user {username}")

# Password security
class PasswordSecurity:
    """Password security utilities"""
    
    @staticmethod
    def validate_password_strength(password):
        """Validate password strength"""
        errors = []
        
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long")
        
        if not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")
        
        if not re.search(r'[a-z]', password):
            errors.append("Password must contain at least one lowercase letter")
        
        if not re.search(r'\d', password):
            errors.append("Password must contain at least one number")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")
        
        # Check for common passwords
        common_passwords = [
            'password', '123456', '123456789', 'qwerty', 'abc123',
            'password123', 'admin', 'letmein', 'welcome', 'monkey'
        ]
        
        if password.lower() in common_passwords:
            errors.append("Password is too common")
        
        return errors
    
    @staticmethod
    def generate_secure_token(length=32):
        """Generate a secure random token"""
        return secrets.token_urlsafe(length)

# Input validation and sanitization
class InputValidator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not username:
            return False, "Username is required"
        
        username = username.strip()
        
        if len(username) < 3:
            return False, "Username must be at least 3 characters long"
        
        if len(username) > 30:
            return False, "Username must be less than 30 characters"
        
        if not re.match(r'^[a-zA-Z0-9_-]+$', username):
            return False, "Username can only contain letters, numbers, underscores, and hyphens"
        
        return True, username
    
    @staticmethod
    def validate_email(email):
        """Validate email format and domain restrictions"""
        if not email:
            return False, "Email is required"

        email = email.strip().lower()

        email_regex = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )

        if not email_regex.match(email):
            return False, "Invalid email format"

        # Check allowed domains for security
        allowed_domains = ['gmail.com', 'outlook.com', 'yahoo.com', 'hotmail.com']
        domain = email.split('@')[1] if '@' in email else ''

        if domain not in allowed_domains:
            return False, f"Only emails from {', '.join(allowed_domains)} are allowed for security purposes"

        return True, email
    
    @staticmethod
    def validate_phone(phone):
        """Validate phone number format"""
        if not phone:
            return True, ""  # Phone is optional
        
        phone = re.sub(r'[^\d+]', '', phone)  # Remove non-digit characters except +
        
        if not re.match(r'^\+?[\d]{10,15}$', phone):
            return False, "Invalid phone number format"
        
        return True, phone
    
    @staticmethod
    def sanitize_input(text, max_length=None):
        """Sanitize text input"""
        if not text:
            return ""
        
        # Strip whitespace
        text = text.strip()
        
        # Remove null bytes
        text = text.replace('\x00', '')
        
        # Limit length
        if max_length:
            text = text[:max_length]
        
        return text

    @staticmethod
    def validate_bet_amount(amount, max_amount=None):
        """Validate bet amount"""
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            return False, "Invalid bet amount"

        if amount <= 0:
            return False, "Bet amount must be positive"

        if amount > 10000:  # Maximum bet limit
            return False, "Bet amount too high (max: 10000)"

        if max_amount and amount > max_amount:
            return False, f"Insufficient balance (max: {max_amount})"

        return True, amount

# CSRF protection utilities
def verify_csrf_token(request):
    """Verify CSRF token for AJAX requests"""
    from django.middleware.csrf import get_token
    from django.views.decorators.csrf import _compare_salted_tokens

    token = request.META.get('HTTP_X_CSRFTOKEN')
    if not token:
        token = request.POST.get('csrfmiddlewaretoken')

    if not token:
        return False

    # Get the CSRF token from the session/cookie
    csrf_token = get_token(request)

    # Use Django's built-in CSRF token comparison
    try:
        return _compare_salted_tokens(token, csrf_token)
    except Exception:
        return False

# Advanced Security Features

class SecurityAuditLogger:
    """Security audit logging system"""

    @staticmethod
    def log_security_event(event_type, user_id=None, ip_address=None, details=None):
        """Log security-related events"""
        event = {
            'timestamp': timezone.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details or {}
        }

        logger.warning(f"SECURITY_EVENT: {json.dumps(event)}")

        # Store in cache for recent events monitoring
        cache_key = f"security_events:{event_type}"
        events = cache.get(cache_key, [])
        events.append(event)

        # Keep only last 100 events per type
        if len(events) > 100:
            events = events[-100:]

        cache.set(cache_key, events, 3600)  # 1 hour

    @staticmethod
    def get_recent_events(event_type=None, limit=50):
        """Get recent security events"""
        if event_type:
            return cache.get(f"security_events:{event_type}", [])[-limit:]

        # Get all event types
        all_events = []
        event_types = ['failed_login', 'suspicious_activity', 'rate_limit_exceeded', 'invalid_token']

        for event_type in event_types:
            events = cache.get(f"security_events:{event_type}", [])
            all_events.extend(events)

        # Sort by timestamp and return latest
        all_events.sort(key=lambda x: x['timestamp'], reverse=True)
        return all_events[:limit]

class IPWhitelist:
    """IP address whitelist management"""

    @staticmethod
    def is_whitelisted(ip_address):
        """Check if IP is whitelisted"""
        whitelist = cache.get('ip_whitelist', set())

        try:
            ip = ipaddress.ip_address(ip_address)
            for whitelisted_ip in whitelist:
                if ip in ipaddress.ip_network(whitelisted_ip, strict=False):
                    return True
        except ValueError:
            logger.warning(f"Invalid IP address format: {ip_address}")

        return False

    @staticmethod
    def add_to_whitelist(ip_address, duration_hours=24):
        """Add IP to whitelist"""
        whitelist = cache.get('ip_whitelist', set())
        whitelist.add(ip_address)
        cache.set('ip_whitelist', whitelist, duration_hours * 3600)

        SecurityAuditLogger.log_security_event(
            'ip_whitelisted',
            details={'ip_address': ip_address, 'duration_hours': duration_hours}
        )

class SecurityTokenManager:
    """Secure token management for API access"""

    @staticmethod
    def generate_api_token(user_id, permissions=None, expires_in=3600):
        """Generate secure API token"""
        payload = {
            'user_id': user_id,
            'permissions': permissions or [],
            'issued_at': int(time.time()),
            'expires_at': int(time.time()) + expires_in,
            'nonce': secrets.token_hex(16)
        }

        # Create signature
        payload_json = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            payload_json.encode(),
            hashlib.sha256
        ).hexdigest()

        # Encode token
        token_data = {
            'payload': base64.b64encode(payload_json.encode()).decode(),
            'signature': signature
        }

        return base64.b64encode(json.dumps(token_data).encode()).decode()

    @staticmethod
    def verify_api_token(token):
        """Verify API token"""
        try:
            # Decode token
            token_data = json.loads(base64.b64decode(token).decode())
            payload_json = base64.b64decode(token_data['payload']).decode()
            signature = token_data['signature']

            # Verify signature
            expected_signature = hmac.new(
                settings.SECRET_KEY.encode(),
                payload_json.encode(),
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(signature, expected_signature):
                return None, "Invalid signature"

            # Parse payload
            payload = json.loads(payload_json)

            # Check expiration
            if payload['expires_at'] < int(time.time()):
                return None, "Token expired"

            return payload, None

        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
            return None, "Invalid token format"

# Enhanced security headers
def add_security_headers(response):
    """Add comprehensive security headers to response"""
    # Basic security headers
    response['X-Content-Type-Options'] = 'nosniff'
    response['X-Frame-Options'] = 'DENY'
    response['X-XSS-Protection'] = '1; mode=block'
    response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    response['X-Permitted-Cross-Domain-Policies'] = 'none'

    # HSTS (HTTP Strict Transport Security)
    if not settings.DEBUG:
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

    # Content Security Policy
    if settings.DEBUG:
        csp = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://checkout.razorpay.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' ws: wss: https://api.razorpay.com https://lumberjack.razorpay.com; "
            "frame-src 'self' https://api.razorpay.com https://checkout.razorpay.com; "
            "font-src 'self' data: https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self';"
        )
    else:
        csp = (
            "default-src 'self'; "
            "script-src 'self' https://checkout.razorpay.com; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
            "img-src 'self' data:; "
            "connect-src 'self' wss: https://api.razorpay.com https://lumberjack.razorpay.com; "
            "frame-src 'self' https://api.razorpay.com https://checkout.razorpay.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "media-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests;"
        )

    response['Content-Security-Policy'] = csp

    # Feature Policy / Permissions Policy
    response['Permissions-Policy'] = (
        "geolocation=(), "
        "microphone=(), "
        "camera=(), "
        "payment=(), "
        "usb=(), "
        "magnetometer=(), "
        "gyroscope=(), "
        "speaker=()"
    )

    return response

# Advanced rate limiting with different strategies
def adaptive_rate_limit(key_func=None, base_limit=10, window=60):
    """Adaptive rate limiting that adjusts based on user behavior"""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if key_func:
                key = key_func(request)
            else:
                key = get_client_ip(request)

            # Get user's historical behavior
            history_key = f"rate_limit_history:{key}"
            history = cache.get(history_key, [])

            # Calculate adaptive limit based on history
            if len(history) > 10:
                # Good behavior = higher limit
                violations = sum(1 for h in history[-10:] if h.get('violated', False))
                if violations == 0:
                    limit = base_limit * 2  # Double limit for good users
                elif violations < 3:
                    limit = base_limit
                else:
                    limit = max(1, base_limit // 2)  # Halve limit for bad users
            else:
                limit = base_limit

            # Check current rate limit
            if RateLimiter.is_rate_limited(key, limit, window):
                # Log violation
                history.append({
                    'timestamp': time.time(),
                    'violated': True,
                    'limit': limit
                })
                cache.set(history_key, history[-20:], 3600)  # Keep last 20 entries

                SecurityAuditLogger.log_security_event(
                    'rate_limit_exceeded',
                    ip_address=key,
                    details={'limit': limit, 'window': window}
                )

                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'retry_after': window
                }, status=429)

            # Log successful request
            history.append({
                'timestamp': time.time(),
                'violated': False,
                'limit': limit
            })
            cache.set(history_key, history[-20:], 3600)

            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
