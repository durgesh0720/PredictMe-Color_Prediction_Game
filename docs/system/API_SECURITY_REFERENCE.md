# API Security Reference

## Overview

This document provides a comprehensive reference for the API security implementation in the Color Prediction Game. All APIs are now secured with proper authentication, authorization, and rate limiting.

## Secured API Endpoints

### Public APIs (Limited Access)

#### Player Statistics API
```
GET /api/player/<username>/
```
- **Authentication**: Not required (public)
- **Rate Limit**: 30 requests/minute, 500 requests/hour
- **Security**: Input validation, rate limiting
- **Response**: Player statistics (non-sensitive data only)

### User APIs (Authentication Required)

#### Player Bet History API
```
GET /api/player/<username>/history/
```
- **Authentication**: Required (user must be authenticated)
- **Rate Limit**: 20 requests/minute, 200 requests/hour
- **Security**: User validation, data filtering
- **Response**: User's betting history

#### Wallet Operations
```
POST /wallet/add-money/
```
- **Authentication**: Required
- **Rate Limit**: 10 requests/minute, 50 requests/hour
- **Security**: Amount validation, transaction logging
- **Required Fields**: `amount`
- **Validation**: 
  - Amount must be positive
  - Maximum amount limit enforced
  - Balance verification

### Admin APIs (Admin Authentication Required)

#### Game Control APIs
```
POST /control-panel/api/select-color/
GET /control-panel/api/game-status/
GET /control-panel/api/live-betting-stats/
POST /control-panel/api/submit-result/
GET /control-panel/api/timer-info/
```
- **Authentication**: Admin required
- **Rate Limit**: 30-120 requests/minute (varies by endpoint)
- **Security**: Admin session validation, action logging
- **Logging**: All admin actions logged with IP and timestamp

## Security Decorators

### @secure_api_endpoint

The main security decorator that combines multiple security measures:

```python
@secure_api_endpoint(
    authentication_required=True,      # Require user authentication
    admin_required=False,              # Require admin authentication
    rate_limit_per_minute=60,         # Rate limit per minute
    rate_limit_per_hour=1000,         # Rate limit per hour
    require_json=False,               # Require JSON content type
    required_fields=None,             # Required JSON fields
    allowed_methods=['GET', 'POST']   # Allowed HTTP methods
)
```

### Individual Decorators

#### @api_authentication_required
```python
@api_authentication_required
def my_endpoint(request):
    # request.user and request.player are available
    pass
```

#### @admin_api_required
```python
@admin_api_required
def admin_endpoint(request):
    # request.admin is available
    pass
```

#### @rate_limit
```python
@rate_limit(requests_per_minute=30, requests_per_hour=500)
def limited_endpoint(request):
    pass
```

## Rate Limiting Configuration

### Default Limits

| Endpoint Type | Per Minute | Per Hour | Notes |
|---------------|------------|----------|-------|
| Public APIs | 60 | 1000 | General public access |
| User APIs | 30 | 500 | Authenticated users |
| Admin APIs | 120 | 2000 | Admin operations |
| Wallet APIs | 10 | 50 | Financial operations |
| WebSocket | 10 connections | - | Per IP address |

### Rate Limit Headers

Rate limit information is included in response headers:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1640995200
```

### Rate Limit Responses

When rate limit is exceeded:
```json
{
    "error": "Rate limit exceeded",
    "message": "Too many requests per minute",
    "retry_after": 60
}
```

## Authentication Methods

### Session-Based Authentication

For web interface and standard API calls:
```python
# User authentication
if request.session.get('is_authenticated'):
    user_id = request.session.get('user_id')
    player = Player.objects.get(id=user_id, is_active=True)

# Admin authentication
if request.session.get('admin_id'):
    admin = Admin.objects.get(id=request.session['admin_id'], is_active=True)
```

### WebSocket Authentication

For WebSocket connections:
```python
# In WebSocket consumer
session = self.scope.get('session', {})
if session.get('is_authenticated'):
    user_id = session.get('user_id')
    # Validate user
```

## Input Validation

### JSON Validation

For endpoints requiring JSON:
```python
@secure_api_endpoint(
    require_json=True,
    required_fields=['amount', 'currency']
)
def payment_endpoint(request):
    data = request.json  # Validated JSON data
    amount = data['amount']  # Required field guaranteed to exist
```

### Field Validation

Common validation patterns:
```python
# Amount validation
if amount <= 0:
    return JsonResponse({'error': 'Amount must be positive'})

if amount > MAX_AMOUNT:
    return JsonResponse({'error': f'Maximum amount is {MAX_AMOUNT}'})

# Username validation
is_valid, clean_username = InputValidator.validate_username(username)
if not is_valid:
    return JsonResponse({'error': 'Invalid username format'})
```

## Security Headers

### API Response Headers

All API responses include security headers:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
```

### CORS Configuration

Cross-Origin Resource Sharing is configured for security:
```python
CORS_ALLOWED_ORIGINS = [
    "https://yourdomain.com",
    "https://www.yourdomain.com",
]
CORS_ALLOW_CREDENTIALS = True
```

## Error Handling

### Security Error Responses

Standardized error responses for security violations:

#### Authentication Errors
```json
{
    "error": "Authentication required",
    "message": "Please log in to access this endpoint",
    "code": 401
}
```

#### Authorization Errors
```json
{
    "error": "Insufficient permissions",
    "message": "Admin access required",
    "code": 403
}
```

#### Rate Limit Errors
```json
{
    "error": "Rate limit exceeded",
    "message": "Too many requests per minute",
    "retry_after": 60,
    "code": 429
}
```

#### Validation Errors
```json
{
    "error": "Validation failed",
    "message": "Required fields: amount, currency",
    "code": 400
}
```

## Logging and Monitoring

### Security Event Logging

All security events are logged:
```python
SecurityAuditLogger.log_security_event(
    'api_access',
    user_id=user.id,
    ip_address=client_ip,
    details={
        'endpoint': request.path,
        'method': request.method,
        'success': True
    }
)
```

### API Access Logging

Every API call is logged with:
- Timestamp
- User/Admin ID
- IP address
- Endpoint
- HTTP method
- Response status
- Response time

### Rate Limit Monitoring

Rate limit violations are tracked:
- IP address
- Endpoint
- Violation count
- Time of violation
- User agent

## WebSocket Security

### Connection Security

WebSocket connections are secured with:
```python
# Authentication check
if not session.get('is_authenticated'):
    await self.close(code=4001)  # Unauthorized
    return

# Rate limiting
if await self._is_rate_limited(client_ip):
    await self.close(code=4029)  # Rate limited
    return

# Origin validation
if not await self._validate_origin(scope):
    await self.close(code=4003)  # Forbidden origin
    return
```

### Message Validation

All WebSocket messages are validated:
```python
try:
    data = json.loads(text_data)
    message_type = data.get('type')
    
    if message_type not in ALLOWED_MESSAGE_TYPES:
        await self.send_error('Invalid message type')
        return
        
except json.JSONDecodeError:
    await self.send_error('Invalid JSON format')
    return
```

## Production Security Checklist

### Environment Configuration
- [ ] SECRET_KEY set to secure random value
- [ ] DEBUG set to False
- [ ] ALLOWED_HOSTS configured properly
- [ ] Database credentials secured
- [ ] Redis credentials secured

### SSL/TLS Configuration
- [ ] HTTPS enabled
- [ ] SSL certificates valid
- [ ] HSTS headers configured
- [ ] Secure cookies enabled

### Security Headers
- [ ] CSP headers configured
- [ ] XSS protection enabled
- [ ] Content type sniffing disabled
- [ ] Frame options set to DENY

### Monitoring
- [ ] Security event logging enabled
- [ ] Rate limit monitoring active
- [ ] Error tracking configured
- [ ] Performance monitoring setup

### Regular Maintenance
- [ ] Security updates applied
- [ ] Dependencies updated
- [ ] Logs reviewed regularly
- [ ] Security audits performed
