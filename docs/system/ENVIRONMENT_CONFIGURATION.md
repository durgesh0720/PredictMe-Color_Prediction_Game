# Environment Configuration Guide

## Overview

This guide explains how to configure environment variables for secure deployment of the Color Prediction Game. All sensitive credentials and configuration options are now managed through environment variables.

## Environment Files

### .env (Development)
```bash
# Django Configuration
SECRET_KEY=django-insecure-j(nip4pj54n+gp6@gpk^aq28pnf_@de!&tz39_zjgwkoha3_rz
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost,testserver

# Database Configuration
DB_ENGINE=django.db.backends.sqlite3
DB_NAME=db.sqlite3
DB_USER=
DB_PASSWORD=
DB_HOST=
DB_PORT=

# Redis Configuration
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# Security Settings
CSRF_TRUSTED_ORIGINS=http://localhost:8000
SESSION_COOKIE_SECURE=False
SESSION_COOKIE_AGE=3600
ADMIN_SESSION_TIMEOUT=1800
```

### .env.production (Production)
```bash
# Django Configuration
SECRET_KEY=your-super-secure-secret-key-here-change-this
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# Database Configuration (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=colorprediction_prod
DB_USER=colorprediction_user
DB_PASSWORD=your-secure-database-password
DB_HOST=localhost
DB_PORT=5432

# Redis Configuration
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=your-secure-redis-password
REDIS_DB=0

# Security Settings
CSRF_TRUSTED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_AGE=3600
ADMIN_SESSION_TIMEOUT=1800

# Email Configuration (Brevo SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-brevo-email@domain.com
EMAIL_HOST_PASSWORD=your-brevo-smtp-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Brevo Configuration
BREVO_API_KEY=your-brevo-api-key
BREVO_SMTP_KEY=your-brevo-smtp-key
```

## Required Environment Variables

### Core Django Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | None | Django secret key for cryptographic signing |
| `DEBUG` | No | False | Enable/disable debug mode |
| `ALLOWED_HOSTS` | Yes | localhost | Comma-separated list of allowed hosts |
| `CSRF_TRUSTED_ORIGINS` | No | None | Comma-separated list of trusted origins for CSRF |

### Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_ENGINE` | No | sqlite3 | Database engine (sqlite3/postgresql/mysql) |
| `DB_NAME` | No | db.sqlite3 | Database name or file path |
| `DB_USER` | No | Empty | Database username |
| `DB_PASSWORD` | No | Empty | Database password |
| `DB_HOST` | No | Empty | Database host |
| `DB_PORT` | No | Empty | Database port |

### Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_HOST` | No | 127.0.0.1 | Redis server host |
| `REDIS_PORT` | No | 6379 | Redis server port |
| `REDIS_PASSWORD` | No | None | Redis authentication password |
| `REDIS_DB` | No | 0 | Redis database number |

### Security Settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SESSION_COOKIE_SECURE` | No | False | Use secure cookies (HTTPS only) |
| `SESSION_COOKIE_AGE` | No | 3600 | Session timeout in seconds |
| `ADMIN_SESSION_TIMEOUT` | No | 1800 | Admin session timeout in seconds |

### API Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `API_RATE_LIMIT_PER_MINUTE` | No | 60 | API rate limit per minute |
| `API_RATE_LIMIT_PER_HOUR` | No | 1000 | API rate limit per hour |

### Game Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ROUND_DURATION` | No | 50 | Game round duration in seconds |
| `BETTING_DURATION` | No | 40 | Betting window duration in seconds |
| `RESULT_DISPLAY_DURATION` | No | 10 | Result display duration in seconds |

### Wallet Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `MIN_BET_AMOUNT` | No | 1 | Minimum bet amount |
| `MAX_BET_AMOUNT` | No | 10000 | Maximum bet amount |
| `MIN_WALLET_BALANCE` | No | 0 | Minimum wallet balance |

## Setting Up Environment Variables

### Development Setup

1. **Copy the example file:**
   ```bash
   cp .env.example .env
   ```

2. **Edit the .env file:**
   ```bash
   nano .env
   ```

3. **Generate a secure secret key:**
   ```python
   from django.core.management.utils import get_random_secret_key
   print(get_random_secret_key())
   ```

### Production Setup

1. **Create production environment file:**
   ```bash
   cp .env.example .env.production
   ```

2. **Set secure values:**
   - Generate a strong SECRET_KEY
   - Set DEBUG=False
   - Configure proper ALLOWED_HOSTS
   - Set up database credentials
   - Configure Redis authentication
   - Set up email credentials

3. **Set file permissions:**
   ```bash
   chmod 600 .env.production
   chown app:app .env.production
   ```

## Security Best Practices

### Secret Key Generation

Generate a cryptographically secure secret key:

```python
# Method 1: Django utility
from django.core.management.utils import get_random_secret_key
secret_key = get_random_secret_key()

# Method 2: Python secrets module
import secrets
import string
alphabet = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
secret_key = ''.join(secrets.choice(alphabet) for i in range(50))
```

### Database Security

For production databases:

```bash
# PostgreSQL example
DB_ENGINE=django.db.backends.postgresql
DB_NAME=colorprediction_prod
DB_USER=colorprediction_user
DB_PASSWORD=$(openssl rand -base64 32)
DB_HOST=localhost
DB_PORT=5432
```

### Redis Security

Secure Redis configuration:

```bash
# Set a strong password
REDIS_PASSWORD=$(openssl rand -base64 32)

# Use a dedicated database
REDIS_DB=1

# Consider using Redis over SSL in production
REDIS_SSL=True
```

## Environment Loading

### Django Settings

The settings.py file loads environment variables:

```python
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Use environment variables
SECRET_KEY = os.getenv('SECRET_KEY')
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', '').split(',')]
```

### Docker Environment

For Docker deployments:

```yaml
# docker-compose.yml
version: '3.8'
services:
  web:
    build: .
    env_file:
      - .env.production
    environment:
      - DJANGO_SETTINGS_MODULE=deployment.production_settings
```

### Systemd Environment

For systemd service deployments:

```ini
# /etc/systemd/system/colorprediction.service
[Unit]
Description=Color Prediction Game
After=network.target

[Service]
Type=exec
User=app
Group=app
WorkingDirectory=/opt/colorprediction
EnvironmentFile=/opt/colorprediction/.env.production
ExecStart=/opt/colorprediction/env/bin/gunicorn server.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

## Validation and Testing

### Environment Validation

Create a validation script:

```python
#!/usr/bin/env python
import os
from dotenv import load_dotenv

def validate_environment():
    load_dotenv()
    
    required_vars = [
        'SECRET_KEY',
        'ALLOWED_HOSTS',
        'DB_NAME',
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Missing required environment variables: {missing_vars}")
        return False
    
    print("Environment validation passed!")
    return True

if __name__ == '__main__':
    validate_environment()
```

### Testing Configuration

Test environment loading:

```python
# Test script
import os
from dotenv import load_dotenv

load_dotenv()

print(f"DEBUG: {os.getenv('DEBUG')}")
print(f"ALLOWED_HOSTS: {os.getenv('ALLOWED_HOSTS')}")
print(f"DB_ENGINE: {os.getenv('DB_ENGINE')}")
print(f"REDIS_HOST: {os.getenv('REDIS_HOST')}")
```

## Deployment Considerations

### Environment File Security

1. **Never commit .env files to version control**
2. **Set proper file permissions (600)**
3. **Use different files for different environments**
4. **Regularly rotate sensitive credentials**

### Backup and Recovery

1. **Backup environment configurations**
2. **Document all environment variables**
3. **Test recovery procedures**
4. **Maintain environment variable inventory**

### Monitoring

1. **Monitor for missing environment variables**
2. **Alert on configuration changes**
3. **Log environment loading errors**
4. **Validate configuration on startup**

## Troubleshooting

### Common Issues

1. **Missing environment variables:**
   ```
   Error: SECRET_KEY environment variable is required
   Solution: Set SECRET_KEY in .env file
   ```

2. **Database connection errors:**
   ```
   Error: FATAL: password authentication failed
   Solution: Check DB_PASSWORD and DB_USER settings
   ```

3. **Redis connection errors:**
   ```
   Error: NOAUTH Authentication required
   Solution: Set REDIS_PASSWORD if Redis requires authentication
   ```

### Debug Commands

```bash
# Check environment loading
python manage.py shell -c "import os; print(os.getenv('SECRET_KEY')[:10] + '...')"

# Validate database connection
python manage.py dbshell

# Test Redis connection
python manage.py shell -c "from django.core.cache import cache; cache.set('test', 'ok'); print(cache.get('test'))"
```
