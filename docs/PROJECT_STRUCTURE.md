# Project Structure

## Root Directory
```
WebSocket_Test/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── db.sqlite3               # SQLite database
├── README.md                # Project documentation
└── .env                     # Environment variables (not in git)
```

## Core Application
```
polling/                     # Main Django app
├── models.py               # Database models
├── views.py                # Main views
├── urls.py                 # URL routing
├── consumers.py            # WebSocket consumers
├── admin_views.py          # Admin panel views
├── auth_views.py           # Authentication views
├── payment_views.py        # Payment system views
├── notification_views.py   # Notification system views
├── services/               # Business logic services
│   ├── payment_service.py
│   ├── notification_service.py
│   └── fraud_detection.py
├── templates/              # HTML templates
├── migrations/             # Database migrations
└── management/             # Custom Django commands
```

## Configuration
```
server/                     # Django project settings
├── settings.py            # Main settings
├── urls.py               # Root URL configuration
├── asgi.py               # ASGI configuration for WebSockets
└── wsgi.py               # WSGI configuration
```

## Testing
```
tests/                     # Comprehensive test suite organized by functionality
├── admin/                # Admin panel tests
├── email/                # Email system tests
├── integration/          # Integration tests
├── misc/                 # Miscellaneous tests (settings, runner, etc.)
├── notification/         # Notification tests
├── notifications/        # Notification system tests
├── payment/              # Payment system tests
├── performance/          # Performance tests
├── timing/               # Timing synchronization tests
├── unit/                 # Unit tests (models, views, auth, etc.)
└── wallet/               # Wallet system tests
```

## Scripts & Utilities
```
scripts/                   # Organized utility scripts
├── admin/                # Admin management scripts
├── data/                 # Data operations and test data creation
├── deployment/           # Deployment utilities
├── development/          # Development tools (test runners, etc.)
├── maintenance/          # System maintenance and fixes
├── monitoring/           # Health checks and monitoring
├── setup/                # Initial setup and configuration
└── utilities/            # General utility scripts
```

## Static Files & Media
```
static/                   # Static files (CSS, JS, images)
├── css/
├── js/
└── images/

media/                    # User uploaded files
└── avatars/             # User profile pictures

templates/               # Global templates
├── base.html
├── includes/
└── payment/
```

## Deployment
```
deployment/              # Deployment configurations
├── Dockerfile.production
├── docker-compose.production.yml
├── deploy.sh
└── production_settings.py
```

## Documentation
```
docs/                    # Comprehensive project documentation
├── admin/              # Admin panel documentation
├── api/                # API documentation
├── email/              # Email setup and configuration guides
├── project/            # Project management and organization
├── solutions/          # Problem solutions and fixes
├── system/             # Technical system documentation
└── user/               # End-user guides and documentation
```

## Logs
```
logs/                   # Application logs
├── django.log
├── admin.log
└── websocket.log
```

## Key Features Implemented

### 🎮 Game System
- Color prediction game with real-time betting
- WebSocket-based live updates
- Admin game control with color selection
- Round management and result calculation

### 💳 Payment System
- Razorpay integration for deposits
- Real money wallet system
- Admin withdrawal approval
- Master wallet for money management
- Fraud detection and validation

### 👥 User Management
- User registration and authentication
- Email verification with OTP
- Profile management with avatars
- Betting history and statistics

### 🔔 Notification System
- Real-time notifications via WebSocket
- Email notifications for important events
- Admin notification management
- Signal-based automatic notifications

### 🛡️ Security Features
- CSRF protection
- Rate limiting
- Fraud detection
- Input validation
- Secure payment processing

### 📊 Admin Panel
- Custom admin interface
- Game control and monitoring
- User management
- Payment approval system
- Real-time statistics

## Technology Stack
- **Backend**: Django 5.2.4, Django Channels
- **Database**: SQLite (development), PostgreSQL (production)
- **WebSockets**: Django Channels with Redis
- **Payment**: Razorpay integration
- **Frontend**: HTML, CSS, JavaScript
- **Deployment**: Docker, Docker Compose
