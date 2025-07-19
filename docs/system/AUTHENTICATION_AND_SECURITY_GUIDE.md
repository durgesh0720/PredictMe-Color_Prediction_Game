# Authentication and Security Guide

## Overview

This document describes the comprehensive authentication and security system implemented for the Color Prediction Game. The system provides multi-layered security with proper authentication, authorization, rate limiting, and monitoring.

## Security Architecture

### 1. Environment-Based Configuration

All sensitive credentials are now stored in environment variables:

```bash
# .env file structure
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
DB_PASSWORD=your-database-password
REDIS_PASSWORD=your-redis-password
EMAIL_HOST_PASSWORD=your-email-password
```

### 2. Multi-Layer Middleware Security

The application uses a comprehensive middleware stack:

1. **SecurityHeadersMiddleware** - Adds security headers
2. **CSRFExemptionMiddleware** - Handles CSRF exemptions
3. **AuthenticationMiddleware** - Custom authentication
4. **RateLimitMiddleware** - API rate limiting
5. **APISecurityMiddleware** - API-specific security

### 3. Authentication System

#### User Authentication
- Session-based authentication for web interface
- Secure password hashing with Django's built-in system
- Session timeout and validation
- IP address and user agent tracking

#### Admin Authentication
- Separate admin authentication system
- Session timeout (configurable, default 30 minutes)
- Activity logging and monitoring
- IP address tracking for security

#### WebSocket Authentication
- Custom WebSocket authentication middleware
- Session validation for WebSocket connections
- Rate limiting for WebSocket connections
- Origin validation

## API Security

### 1. Secure API Endpoint Decorator

All API endpoints use the `@secure_api_endpoint` decorator:

```python
@secure_api_endpoint(
    authentication_required=True,
    admin_required=False,
    rate_limit_per_minute=60,
    rate_limit_per_hour=1000,
    require_json=False,
    required_fields=None,
    allowed_methods=['GET', 'POST']
)
def my_api_endpoint(request):
    # Your API logic here
    pass
```

### 2. Rate Limiting

Different rate limits for different endpoint types:

- **Public APIs**: 60 requests/minute, 1000 requests/hour
- **User APIs**: 30 requests/minute, 500 requests/hour
- **Admin APIs**: 120 requests/minute, 2000 requests/hour
- **Wallet APIs**: 10 requests/minute, 50 requests/hour

### 3. Input Validation

- JSON schema validation for API requests
- Required field validation
- Content-type validation
- Input sanitization

## WebSocket Security

### 1. Authentication Middleware

WebSocket connections are secured with:

```python
# Custom WebSocket middleware stack
WebSocketSecurityMiddleware(
    WebSocketRateLimitMiddleware(
        WebSocketAuthMiddleware(
            AuthMiddlewareStack(URLRouter)
        )
    )
)
```

### 2. Connection Validation

- Origin header validation
- User agent validation
- Rate limiting (max connections per IP)
- Session validation

### 3. Message Security

- JSON validation for all messages
- Command validation
- User authorization for actions

## Security Headers

### Production Security Headers

```python
# HTTPS Settings
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS Settings
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Cookie Security
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

### Custom Security Headers

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Referrer-Policy: strict-origin-when-cross-origin`
- Content Security Policy (CSP)

## Monitoring and Logging

### 1. Security Event Logging

All security events are logged:

```python
SecurityAuditLogger.log_security_event(
    'login_attempt',
    user_id=user.id,
    ip_address=client_ip,
    details={'success': True}
)
```

### 2. API Access Logging

All API calls are logged with:
- Timestamp
- User information
- IP address
- Endpoint accessed
- Response time
- Success/failure status

### 3. Rate Limit Monitoring

Rate limit violations are logged and monitored:
- IP address tracking
- Endpoint-specific limits
- Automatic blocking for repeated violations

## Authentication Decorators

### 1. User Authentication

```python
@auth_required
def protected_view(request):
    # request.user is automatically available
    pass

@api_authentication_required
def api_endpoint(request):
    # request.player is automatically available
    pass
```

### 2. Admin Authentication

```python
@admin_required
def admin_view(request):
    # request.admin is automatically available
    pass

@admin_api_required
def admin_api_endpoint(request):
    # request.admin is automatically available
    pass
```

## Wallet and Financial Security

### 1. Transaction Security

- All wallet operations require authentication
- Transaction logging and audit trails
- Balance validation before operations
- Atomic database transactions

### 2. Betting Security

- Bet amount validation
- Balance verification
- Duplicate bet prevention
- Real-time balance updates

### 3. Admin Financial Controls

- Admin approval for large transactions
- Transaction history and monitoring
- Master wallet balance tracking
- Financial reporting and auditing

## Production Deployment Security

### 1. Environment Variables

Required environment variables for production:

```bash
SECRET_KEY=your-production-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com
CSRF_TRUSTED_ORIGINS=https://yourdomain.com
DB_PASSWORD=secure-database-password
REDIS_PASSWORD=secure-redis-password
```

### 2. Database Security

- SSL connections required
- Connection pooling
- Query optimization
- Regular backups

### 3. Redis Security

- Password authentication
- Connection encryption
- Memory optimization
- Cache invalidation

## Security Best Practices

### 1. Password Security

- Minimum password requirements
- Password hashing with Django's PBKDF2
- Session invalidation on password change
- Account lockout after failed attempts

### 2. Session Security

- Secure session cookies
- Session timeout
- Session invalidation on logout
- Cross-site request forgery protection

### 3. Input Validation

- All user inputs validated
- SQL injection prevention
- XSS protection
- File upload security

## Monitoring and Alerts

### 1. Security Monitoring

- Failed login attempts
- Rate limit violations
- Suspicious activity patterns
- Unusual API usage

### 2. Performance Monitoring

- Response times
- Database query performance
- Memory usage
- Connection counts

### 3. Error Monitoring

- Application errors
- Security violations
- System failures
- User experience issues

## Maintenance and Updates

### 1. Regular Security Updates

- Django security updates
- Dependency updates
- Security patch management
- Vulnerability scanning

### 2. Security Audits

- Regular code reviews
- Penetration testing
- Security assessments
- Compliance checks

### 3. Backup and Recovery

- Regular database backups
- Configuration backups
- Disaster recovery procedures
- Data integrity checks
