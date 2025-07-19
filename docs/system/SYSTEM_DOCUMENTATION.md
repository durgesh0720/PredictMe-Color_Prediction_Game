# Color Prediction Game - System Documentation

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Installation & Setup](#installation--setup)
5. [Configuration](#configuration)
6. [API Documentation](#api-documentation)
7. [Database Schema](#database-schema)
8. [Security](#security)
9. [Performance](#performance)
10. [Testing](#testing)
11. [Deployment](#deployment)
12. [Troubleshooting](#troubleshooting)

## 🎯 System Overview

The Color Prediction Game is a real-time web application where users can predict colors and place bets. The system features:

- **Real-time gameplay** using WebSockets
- **User authentication** and profile management
- **Admin panel** for game control and monitoring
- **Secure betting system** with virtual currency
- **Performance optimization** with caching and query optimization
- **Comprehensive security** measures

### Technology Stack

- **Backend**: Django 5.2.4 with Django Channels
- **Database**: SQLite (development) / PostgreSQL (production)
- **Cache**: Redis
- **WebSockets**: Django Channels with Redis channel layer
- **Frontend**: HTML5, CSS3, JavaScript (ES6+)
- **Authentication**: Custom session-based authentication

## 🏗️ Architecture

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Browser)     │◄──►│   (Django)      │◄──►│   (SQLite/PG)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         └─────────────►│   WebSocket     │              │
                        │   (Channels)    │              │
                        └─────────────────┘              │
                                 │                       │
                        ┌─────────────────┐              │
                        │   Redis Cache   │◄─────────────┘
                        │   & Channels    │
                        └─────────────────┘
```

### Directory Structure

```
WebSocket_Test/
├── polling/                    # Main Django app
│   ├── models.py              # Database models
│   ├── views.py               # HTTP views
│   ├── auth_views.py          # Authentication views
│   ├── admin_views.py         # Admin panel views
│   ├── consumers.py           # WebSocket consumers
│   ├── admin_consumers.py     # Admin WebSocket consumers
│   ├── security.py            # Security utilities
│   ├── performance.py         # Performance optimization
│   ├── routing.py             # WebSocket routing
│   ├── urls.py                # URL patterns
│   └── templates/             # HTML templates
├── server/                    # Django project settings
│   ├── settings.py            # Main settings
│   ├── urls.py                # Root URL config
│   └── asgi.py                # ASGI configuration
├── static/                    # Static files
│   ├── css/                   # Stylesheets
│   ├── js/                    # JavaScript files
│   └── images/                # Images
└── media/                     # User uploads
```

## ✨ Features

### User Features

1. **Authentication System**
   - User registration with email verification
   - Secure login with session management
   - Password strength validation
   - Profile management with avatar upload

2. **Game Mechanics**
   - Real-time color prediction game
   - 45-second rounds (40s betting + 5s results)
   - Multiple bet types: Color and Number
   - Virtual currency system

3. **Wallet Management**
   - Add money to account
   - Transaction history
   - Balance tracking

4. **User Dashboard**
   - Betting history
   - Win/loss statistics
   - Profile customization

### Admin Features

1. **Game Control**
   - Live game monitoring
   - Manual color selection
   - Auto-selection with minimum bets
   - Emergency stop functionality

2. **User Management**
   - View all users
   - User details and statistics
   - Account management

3. **Financial Management**
   - Revenue tracking
   - Transaction monitoring
   - Profit/loss analysis

4. **System Monitoring**
   - Real-time dashboard
   - Performance metrics
   - System alerts
   - Audit logs

## 🚀 Installation & Setup

### Prerequisites

- Python 3.8+
- Redis server
- Git

### Installation Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd WebSocket_Test
   ```

2. **Create virtual environment**
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install django channels channels-redis pillow
   ```

4. **Configure database**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Create admin user**
   ```bash
   python create_admin.py
   ```

6. **Start Redis server**
   ```bash
   redis-server
   ```

7. **Run development server**
   ```bash
   python manage.py runserver
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=sqlite:///db.sqlite3
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1
```

### Settings Configuration

Key settings in `server/settings.py`:

```python
# Security
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
ADMIN_SESSION_TIMEOUT = 1800  # 30 minutes

# Channels
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
        },
    },
}

# Game Settings
ROUND_DURATION = 45  # seconds
BETTING_DURATION = 40  # seconds
```

## 📡 API Documentation

### Authentication Endpoints

- `POST /register/` - User registration
- `POST /login/` - User login
- `POST /logout/` - User logout

### Game Endpoints

- `GET /room/<room_name>/` - Join game room
- `GET /history/` - Game history
- `GET /api/player/<username>/` - Player statistics
- `GET /api/player/<username>/history/` - Player betting history (API)

### Admin Endpoints

- `POST /control-panel/` - Admin login
- `GET /control-panel/dashboard/` - Admin dashboard
- `POST /control-panel/api/select-color/` - Manual color selection

### WebSocket Endpoints

- `ws://localhost:8000/ws/game/<room_name>/` - Game WebSocket
- `ws://localhost:8000/ws/control-panel/game-control/` - Admin control WebSocket

## 🗄️ Database Schema

### Core Models

1. **Player**
   - User authentication and profile data
   - Game statistics and balance
   - Timestamps and status flags

2. **GameRound**
   - Game session data
   - Results and timing
   - Room and game type information

3. **Bet**
   - User betting data
   - Bet types and amounts
   - Win/loss tracking

4. **Admin**
   - Admin user management
   - Authentication and permissions

5. **Transaction**
   - Financial transaction tracking
   - Balance changes and audit trail

### Relationships

```
Player (1) ──── (N) Bet (N) ──── (1) GameRound
   │                                    │
   │                                    │
   └── (1) ──── (N) Transaction         │
                                        │
Admin (1) ──── (N) AdminColorSelection ─┘
```

## 🔒 Security

### Authentication Security

- **Password Hashing**: Django's PBKDF2 algorithm
- **Session Management**: Secure session cookies with timeout
- **CSRF Protection**: Built-in Django CSRF middleware
- **Rate Limiting**: Custom rate limiting for login attempts

### Input Validation

- **Username**: Alphanumeric with underscores/hyphens
- **Email**: RFC-compliant email validation
- **Password**: Strength requirements with complexity rules
- **Sanitization**: HTML/script tag removal

### WebSocket Security

- **Authentication**: Session-based authentication for WebSocket connections
- **Origin Validation**: CORS and origin checking
- **Message Validation**: JSON schema validation for WebSocket messages

### Security Headers

```python
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Content-Security-Policy: default-src 'self'
```

## ⚡ Performance

### Caching Strategy

1. **Player Statistics**: 5-minute cache
2. **Game History**: 10-minute cache
3. **Leaderboards**: 15-minute cache
4. **Admin Stats**: 1-minute cache

### Database Optimization

- **Indexes**: Strategic indexing on frequently queried fields
- **Query Optimization**: select_related and prefetch_related usage
- **Bulk Operations**: Batch processing for large datasets

### WebSocket Optimization

- **Connection Pooling**: Efficient connection management
- **Message Queuing**: Reliable message delivery
- **Heartbeat Monitoring**: Connection health checking

## 🧪 Testing

### Test Coverage

- **Model Tests**: Database model functionality
- **View Tests**: HTTP endpoint testing
- **WebSocket Tests**: Real-time functionality
- **Security Tests**: Authentication and validation
- **Integration Tests**: End-to-end workflows

### Running Tests

```bash
# Run all tests
python manage.py test

# Run specific test module
python manage.py test polling.test_models

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

### Test Data

Use the provided test data creation scripts:

```bash
python create_test_data.py
python create_test_rounds.py
```

## 🚀 Deployment

### Production Checklist

1. **Environment Setup**
   - Set `DEBUG=False`
   - Configure production database
   - Set up Redis cluster
   - Configure static file serving

2. **Security Configuration**
   - Generate new SECRET_KEY
   - Configure HTTPS
   - Set secure cookie flags
   - Enable security headers

3. **Performance Optimization**
   - Enable database connection pooling
   - Configure caching
   - Set up CDN for static files
   - Enable gzip compression

### Docker Deployment

```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 🔧 Troubleshooting

### Common Issues

1. **WebSocket Connection Failed**
   - Check Redis server status
   - Verify CHANNEL_LAYERS configuration
   - Check firewall settings

2. **Database Migration Errors**
   - Reset migrations: `python manage.py migrate --fake-initial`
   - Check database permissions
   - Verify model changes

3. **Static Files Not Loading**
   - Run `python manage.py collectstatic`
   - Check STATIC_URL and STATIC_ROOT settings
   - Verify web server configuration

4. **Performance Issues**
   - Check database query performance
   - Monitor Redis memory usage
   - Review cache hit rates
   - Analyze slow query logs

### Logging

Check application logs in:
- `logs/django.log` - General application logs
- `logs/websocket.log` - WebSocket-specific logs
- `logs/admin.log` - Admin panel logs

### Monitoring

Key metrics to monitor:
- Active WebSocket connections
- Database query performance
- Cache hit rates
- Memory usage
- Response times

## 📞 Support

For technical support or questions:
- Check the troubleshooting section
- Review application logs
- Contact the development team

---

*Last updated: 2024-07-12*
