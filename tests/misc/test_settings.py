"""
Test-specific Django settings for the Color Prediction Game test suite.
These settings optimize the test environment for speed and isolation.
"""

from server.settings import *
import tempfile
import os

# Test Database Configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'OPTIONS': {
            'timeout': 20,
        }
    }
}

# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True
    
    def __getitem__(self, item):
        return None

MIGRATION_MODULES = DisableMigrations()

# Test-specific settings
DEBUG = False
SECRET_KEY = 'test-secret-key-for-testing-only'
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Disable HTTPS redirects for testing
SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Cache configuration for testing
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Session configuration for testing
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# Disable rate limiting for tests
API_RATE_LIMIT_PER_MINUTE = 10000
API_RATE_LIMIT_PER_HOUR = 100000
ADMIN_PANEL_RATE_LIMIT = 10000

# Test media and static files
MEDIA_ROOT = tempfile.mkdtemp()
STATIC_ROOT = tempfile.mkdtemp()

# Logging configuration for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'WARNING',
        },
        'polling': {
            'handlers': ['console'],
            'level': 'INFO',
        },
    },
}

# Test-specific payment settings
RAZORPAY_KEY_ID = 'test_key_id'
RAZORPAY_KEY_SECRET = 'test_key_secret'
RAZORPAY_WEBHOOK_SECRET = 'test_webhook_secret'

# Disable fraud detection for tests
FRAUD_DETECTION_ENABLED = False
PAYMENT_VERIFICATION_REQUIRED = False

# Test WebSocket settings
WS_ALLOWED_ORIGINS = ['http://testserver', 'http://localhost:8000']

# Disable external services for tests
BREVO_API_KEY = 'test_brevo_key'
BREVO_SMTP_KEY = 'test_smtp_key'

# Test notification settings
NOTIFICATION_EMAIL_ENABLED = False

# Password hashers for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Disable whitenoise for tests
USE_WHITENOISE = False

# Test-specific middleware (remove some for speed)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'polling.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
]

# Channels configuration for testing
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Test file upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # 1MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 1024 * 1024  # 1MB

# Disable CSRF for API tests
CSRF_TRUSTED_ORIGINS = ['http://testserver', 'http://localhost:8000']

# Test timezone
USE_TZ = True
TIME_ZONE = 'UTC'

# Test internationalization
USE_I18N = False
USE_L10N = False

# Test game configuration
ROUND_DURATION = 10  # Shorter for tests
BETTING_DURATION = 8  # Shorter for tests
RESULT_DISPLAY_DURATION = 2  # Shorter for tests

# Test wallet configuration
MIN_BET_AMOUNT = 1
MAX_BET_AMOUNT = 1000
MIN_WALLET_BALANCE = 0
DEFAULT_BALANCE = 1000

# Test payment limits
MIN_DEPOSIT_AMOUNT = 1
MAX_DEPOSIT_AMOUNT = 1000
MIN_WITHDRAWAL_AMOUNT = 1
MAX_WITHDRAWAL_AMOUNT = 500

# Test security settings
MAX_DAILY_DEPOSIT_LIMIT = 10000
MAX_DAILY_WITHDRAWAL_LIMIT = 5000

# Test admin settings
ADMIN_SESSION_TIMEOUT = 3600  # 1 hour for tests

# Disable backup for tests
BACKUP_ENABLED = False
