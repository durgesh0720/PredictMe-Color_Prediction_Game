import os
from pathlib import Path
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-change-this-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Chrome localhost compatibility settings
if DEBUG:
    # Disable some security features that cause Chrome localhost issues
    SECURE_SSL_REDIRECT = False
    SECURE_HSTS_SECONDS = 0
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

# Parse ALLOWED_HOSTS from environment variable - Chrome localhost fix
ALLOWED_HOSTS = [host.strip() for host in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1,0.0.0.0').split(',')] + ['testserver']

# Parse CSRF_TRUSTED_ORIGINS from environment variable - Chrome localhost fix
csrf_origins = os.getenv('CSRF_TRUSTED_ORIGINS', 'http://localhost:8000,http://127.0.0.1:8000')
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in csrf_origins.split(',') if origin.strip()]

# Redis Configuration for Production Scalability
REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Production Gaming Configuration
GAMING_CONFIG = {
    'MAX_CONCURRENT_PLAYERS_PER_ROOM': 1000,
    'MAX_ROOMS': 10,
    'ROUND_DURATION_SECONDS': 50,
    'BETTING_PHASE_SECONDS': 40,
    'RESULT_PHASE_SECONDS': 10,
    'AUTO_CLEANUP_EMPTY_ROOMS': True,
    'ENABLE_HORIZONTAL_SCALING': True,
    'REDIS_BACKED_STATE': True
}

# WebSocket Configuration
WS_ALLOWED_ORIGINS = []
for host in ALLOWED_HOSTS:
    if host not in ['testserver']:
        WS_ALLOWED_ORIGINS.extend([
            f'http://{host}',
            f'https://{host}',
        ])

# Add ngrok domains for development
if DEBUG:
    WS_ALLOWED_ORIGINS.extend([
        'https://*.ngrok-free.app',
        'https://*.ngrok.io',
        'http://localhost:8000',
        'https://localhost:8000',
    ])


# Application definition

INSTALLED_APPS = [
    'daphne',
    'channels',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'polling',
]

# Temporarily disable some Django middleware for Chrome debugging
MIDDLEWARE = [
    # 'django.middleware.security.SecurityMiddleware',  # Disabled for Chrome debugging
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'polling.middleware.CSRFExemptionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'polling.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',  # Disabled for Chrome debugging
    'polling.middleware.SecurityHeadersMiddleware',  # Our custom middleware
    'polling.middleware.RateLimitMiddleware',
    'polling.middleware.APISecurityMiddleware',
]

ROOT_URLCONF = 'server.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

ASGI_APPLICATION = 'server.asgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', BASE_DIR / 'db.sqlite3'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
        'OPTIONS': {
            'timeout': 20,
        } if os.getenv('DB_ENGINE', '').endswith('sqlite3') else {},
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Additional locations of static files
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files (User uploads)
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.getenv('REDIS_HOST', '127.0.0.1'), int(os.getenv('REDIS_PORT', 6379)))],
            # WebSocket connection settings for better stability
            "capacity": 1500,  # Maximum number of messages to store
            "expiry": 60,      # Message expiry time in seconds
        },
    },
}

# Session settings for security
SESSION_COOKIE_AGE = int(os.getenv('SESSION_COOKIE_AGE', 3600))  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_SECURE = os.getenv('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Admin session timeout (30 minutes)
ADMIN_SESSION_TIMEOUT = int(os.getenv('ADMIN_SESSION_TIMEOUT', 1800))

# Email Configuration (Brevo SMTP)
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp-relay.brevo.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '587'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_USE_SSL = False  # Use TLS for Brevo SMTP
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')

# Brevo Configuration
BREVO_API_KEY = os.getenv('BREVO_API_KEY', '')
BREVO_SMTP_KEY = os.getenv('BREVO_SMTP_KEY', '')

DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'noreply@codeforge.code')

# Additional email security settings
EMAIL_TIMEOUT = 30  # 30 seconds timeout
EMAIL_SSL_CERTFILE = None
EMAIL_SSL_KEYFILE = None

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'class': 'logging.FileHandler',
            'filename': os.getenv('LOG_FILE_PATH', 'logs/django.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console', 'file'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': os.getenv('LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
        'polling': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# API Security Settings
API_RATE_LIMIT_PER_MINUTE = int(os.getenv('API_RATE_LIMIT_PER_MINUTE', 60))
API_RATE_LIMIT_PER_HOUR = int(os.getenv('API_RATE_LIMIT_PER_HOUR', 1000))
# Admin users should have unlimited access (as per user preference)
ADMIN_PANEL_RATE_LIMIT = int(os.getenv('ADMIN_PANEL_RATE_LIMIT', 999999))

# Game Configuration
ROUND_DURATION = int(os.getenv('ROUND_DURATION', 50))
BETTING_DURATION = int(os.getenv('BETTING_DURATION', 40))
RESULT_DISPLAY_DURATION = int(os.getenv('RESULT_DISPLAY_DURATION', 10))

# Wallet Configuration
MIN_BET_AMOUNT = int(os.getenv('MIN_BET_AMOUNT', 1))
MAX_BET_AMOUNT = int(os.getenv('MAX_BET_AMOUNT', 10000))
MIN_WALLET_BALANCE = int(os.getenv('MIN_WALLET_BALANCE', 0))
DEFAULT_BALANCE = int(os.getenv('DEFAULT_BALANCE', 0))  # No starting balance for real money system

# Payment Gateway Configuration (Razorpay)
RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID', '')
RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET', '')
RAZORPAY_WEBHOOK_SECRET = os.getenv('RAZORPAY_WEBHOOK_SECRET', '')
RAZORPAY_ACCOUNT_NUMBER = os.getenv('RAZORPAY_ACCOUNT_NUMBER', '')  # Your business account number for payouts

# Payment Limits
MIN_DEPOSIT_AMOUNT = int(os.getenv('MIN_DEPOSIT_AMOUNT', 10))  # ₹10 minimum deposit
MAX_DEPOSIT_AMOUNT = int(os.getenv('MAX_DEPOSIT_AMOUNT', 10000))  # ₹10,000 maximum deposit
MIN_WITHDRAWAL_AMOUNT = int(os.getenv('MIN_WITHDRAWAL_AMOUNT', 20))  # ₹20 minimum withdrawal
MAX_WITHDRAWAL_AMOUNT = int(os.getenv('MAX_WITHDRAWAL_AMOUNT', 5000))  # ₹5,000 maximum withdrawal

# Responsible Gambling Configuration
RG_DAILY_LOSS_LIMIT = int(os.getenv('RG_DAILY_LOSS_LIMIT', 10000))  # Default ₹100
RG_DAILY_BET_LIMIT = int(os.getenv('RG_DAILY_BET_LIMIT', 50000))   # Default ₹500
RG_SESSION_LOSS_LIMIT = int(os.getenv('RG_SESSION_LOSS_LIMIT', 5000)) # Default ₹50
RG_SESSION_TIME_LIMIT = int(os.getenv('RG_SESSION_TIME_LIMIT', 7200)) # Default 2 hours in seconds
RG_MAX_BET_AMOUNT = int(os.getenv('RG_MAX_BET_AMOUNT', 2000))     # Default ₹20 per bet
RG_MIN_BET_AMOUNT = int(os.getenv('RG_MIN_BET_AMOUNT', 100))      # Default ₹1 per bet
RG_COOLING_OFF_PERIOD = int(os.getenv('RG_COOLING_OFF_PERIOD', 86400)) # 24 hours in seconds

# Security Settings for Production - Environment Variable Driven
# HTTPS Settings
SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'False').lower() == 'true'
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS Settings
SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '0'))
SECURE_HSTS_INCLUDE_SUBDOMAINS = os.getenv('SECURE_HSTS_INCLUDE_SUBDOMAINS', 'False').lower() == 'true'
SECURE_HSTS_PRELOAD = os.getenv('SECURE_HSTS_PRELOAD', 'False').lower() == 'true'

# Content Security
SECURE_CONTENT_TYPE_NOSNIFF = os.getenv('SECURE_CONTENT_TYPE_NOSNIFF', 'False').lower() == 'true'
SECURE_BROWSER_XSS_FILTER = os.getenv('SECURE_BROWSER_XSS_FILTER', 'False').lower() == 'true'
X_FRAME_OPTIONS = os.getenv('X_FRAME_OPTIONS', 'SAMEORIGIN')

# Referrer Policy
SECURE_REFERRER_POLICY = os.getenv('SECURE_REFERRER_POLICY', 'strict-origin-when-cross-origin')

# Additional Security Headers
SECURE_CROSS_ORIGIN_OPENER_POLICY = 'same-origin'

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f"redis://{os.getenv('REDIS_HOST', '127.0.0.1')}:{os.getenv('REDIS_PORT', 6379)}/1",
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'PASSWORD': os.getenv('REDIS_PASSWORD', None),
        },
        'KEY_PREFIX': 'colorprediction',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Session Configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# CSRF Configuration
CSRF_COOKIE_NAME = 'csrftoken'
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'
CSRF_COOKIE_AGE = 31449600  # 1 year
CSRF_COOKIE_SECURE = os.getenv('CSRF_COOKIE_SECURE', 'False').lower() == 'true'
CSRF_COOKIE_HTTPONLY = os.getenv('CSRF_COOKIE_HTTPONLY', 'False').lower() == 'true'
CSRF_COOKIE_SAMESITE = 'Lax'

# File Upload Security
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
FILE_UPLOAD_PERMISSIONS = 0o644

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Duplicate logging configuration removed - using the one defined earlier at line 191