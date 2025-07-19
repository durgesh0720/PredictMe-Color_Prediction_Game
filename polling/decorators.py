"""
Authentication and authorization decorators for API endpoints.
"""

import json
import time
import functools
import logging
from django.http import JsonResponse
from django.shortcuts import redirect
from django.contrib import messages
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Player, Admin
from .security import SecurityAuditLogger, get_client_ip

logger = logging.getLogger(__name__)


def api_authentication_required(view_func):
    """
    Decorator to require user authentication for API endpoints.
    Returns JSON responses for API calls.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if user is authenticated
        if not request.session.get('is_authenticated'):
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'Please log in to access this endpoint'
            }, status=401)
        
        # Check if user still exists and is active
        user_id = request.session.get('user_id')
        if not user_id:
            request.session.flush()
            return JsonResponse({
                'error': 'Invalid session',
                'message': 'Session expired, please log in again'
            }, status=401)
        
        try:
            player = Player.objects.get(id=user_id, is_active=True)
            request.user = player
            request.player = player
        except Player.DoesNotExist:
            request.session.flush()
            return JsonResponse({
                'error': 'User not found',
                'message': 'User account is no longer active'
            }, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def admin_api_required(view_func):
    """
    Decorator to require admin authentication for admin API endpoints.
    Returns JSON responses for API calls.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Check if admin is authenticated
        if 'admin_id' not in request.session:
            return JsonResponse({
                'error': 'Admin authentication required',
                'message': 'Please log in as admin to access this endpoint'
            }, status=401)
        
        # Check session timeout
        admin_login_time = request.session.get('admin_login_time')
        if admin_login_time:
            from datetime import datetime
            login_time = datetime.fromisoformat(admin_login_time)
            timeout_duration = getattr(settings, 'ADMIN_SESSION_TIMEOUT', 1800)
            
            if (timezone.now() - login_time).total_seconds() > timeout_duration:
                request.session.flush()
                return JsonResponse({
                    'error': 'Session expired',
                    'message': 'Admin session has expired, please log in again'
                }, status=401)
        
        # Verify admin exists and is active
        try:
            admin = Admin.objects.get(id=request.session['admin_id'], is_active=True)
            request.admin = admin
            
            # Update last activity
            request.session['admin_last_activity'] = timezone.now().isoformat()
            
        except Admin.DoesNotExist:
            request.session.flush()
            return JsonResponse({
                'error': 'Admin not found',
                'message': 'Admin account is no longer active'
            }, status=401)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def rate_limit(requests_per_minute=60, requests_per_hour=1000):
    """
    Rate limiting decorator for API endpoints.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            client_ip = get_client_ip(request)
            
            # Check per-minute limit
            minute_key = f"rate_limit:{view_func.__name__}:{client_ip}:{int(time.time() // 60)}"
            minute_count = cache.get(minute_key, 0)
            
            if minute_count >= requests_per_minute:
                SecurityAuditLogger.log_security_event(
                    'rate_limit_exceeded',
                    ip_address=client_ip,
                    details={
                        'endpoint': request.path,
                        'function': view_func.__name__,
                        'limit_type': 'per_minute'
                    }
                )
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {requests_per_minute} requests per minute allowed'
                }, status=429)
            
            # Check per-hour limit
            hour_key = f"rate_limit:{view_func.__name__}:{client_ip}:{int(time.time() // 3600)}"
            hour_count = cache.get(hour_key, 0)
            
            if hour_count >= requests_per_hour:
                SecurityAuditLogger.log_security_event(
                    'rate_limit_exceeded',
                    ip_address=client_ip,
                    details={
                        'endpoint': request.path,
                        'function': view_func.__name__,
                        'limit_type': 'per_hour'
                    }
                )
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': f'Maximum {requests_per_hour} requests per hour allowed'
                }, status=429)
            
            # Increment counters
            cache.set(minute_key, minute_count + 1, 60)
            cache.set(hour_key, hour_count + 1, 3600)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_json_content_type(view_func):
    """
    Decorator to require JSON content type for POST/PUT requests.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            content_type = request.META.get('CONTENT_TYPE', '')
            if not content_type.startswith('application/json'):
                return JsonResponse({
                    'error': 'Invalid content type',
                    'message': 'Content-Type must be application/json'
                }, status=400)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper


def validate_json_data(required_fields=None):
    """
    Decorator to validate JSON data in request body.
    """
    def decorator(view_func):
        @functools.wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if request.method in ['POST', 'PUT', 'PATCH']:
                try:
                    request.json = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({
                        'error': 'Invalid JSON',
                        'message': 'Request body must contain valid JSON'
                    }, status=400)
                
                # Check required fields
                if required_fields:
                    missing_fields = []
                    for field in required_fields:
                        if field not in request.json:
                            missing_fields.append(field)
                    
                    if missing_fields:
                        return JsonResponse({
                            'error': 'Missing required fields',
                            'message': f'Required fields: {", ".join(missing_fields)}'
                        }, status=400)
            
            return view_func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def log_api_access(view_func):
    """
    Decorator to log API access for security monitoring.
    """
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        start_time = time.time()
        client_ip = get_client_ip(request)
        user_id = getattr(request, 'player', None)
        user_id = user_id.id if user_id else None
        admin_id = getattr(request, 'admin', None)
        admin_id = admin_id.id if admin_id else None
        
        # Log the request
        logger.info(f"API Call: {request.method} {request.path} - IP: {client_ip} - User: {user_id} - Admin: {admin_id}")
        
        try:
            response = view_func(request, *args, **kwargs)
            
            # Log successful response
            duration = time.time() - start_time
            logger.info(f"API Response: {response.status_code} - Duration: {duration:.3f}s")
            
            return response
            
        except Exception as e:
            # Log error
            duration = time.time() - start_time
            logger.error(f"API Error: {str(e)} - Duration: {duration:.3f}s")
            
            SecurityAuditLogger.log_security_event(
                'api_error',
                user_id=user_id,
                ip_address=client_ip,
                details={
                    'endpoint': request.path,
                    'error': str(e),
                    'duration': duration
                }
            )
            
            raise
    
    return wrapper


def secure_api_endpoint(
    authentication_required=True,
    admin_required=False,
    rate_limit_per_minute=60,
    rate_limit_per_hour=1000,
    require_json=False,
    required_fields=None,
    allowed_methods=None,
    csrf_required=True  # Default to requiring CSRF protection
):
    """
    Comprehensive decorator for securing API endpoints.
    Combines multiple security measures in one decorator.
    """
    def decorator(view_func):
        # Apply decorators in reverse order (they wrap from inside out)
        decorated_func = view_func
        
        # Log API access
        decorated_func = log_api_access(decorated_func)
        
        # Validate JSON data if required
        if required_fields:
            decorated_func = validate_json_data(required_fields)(decorated_func)
        
        # Require JSON content type if specified
        if require_json:
            decorated_func = require_json_content_type(decorated_func)
        
        # Skip rate limiting for admin endpoints (admin users have unlimited access)
        if not admin_required:
            decorated_func = rate_limit(rate_limit_per_minute, rate_limit_per_hour)(decorated_func)
        
        # Apply authentication
        if admin_required:
            decorated_func = admin_api_required(decorated_func)
        elif authentication_required:
            decorated_func = api_authentication_required(decorated_func)
        
        # Apply HTTP method restrictions
        if allowed_methods:
            decorated_func = require_http_methods(allowed_methods)(decorated_func)
        
        return decorated_func
    
    return decorator
