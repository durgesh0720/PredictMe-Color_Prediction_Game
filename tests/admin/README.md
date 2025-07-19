# Admin Panel Tests

This directory contains tests specifically for admin panel functionality and admin-related features.

## 🧪 Test Files

### Access Control Tests
- **[test_admin_unlimited_access.py](./test_admin_unlimited_access.py)** - Tests for admin unlimited access features

### Admin Panel Functionality
- **test_admin_authentication.py** - Admin login/logout tests
- **test_admin_permissions.py** - Admin permission tests
- **test_admin_dashboard.py** - Dashboard functionality tests
- **test_admin_game_control.py** - Game control tests

## 🎯 Test Categories

### Authentication & Authorization
- Admin login/logout functionality
- Session management
- Permission validation
- Role-based access control

### Game Management
- Game round control
- Color selection
- Betting management
- Result management

### Financial Management
- Wallet operations
- Transaction monitoring
- Payment processing
- Financial reporting

### User Management
- Player account management
- User verification
- Account suspension/activation
- User statistics

### System Administration
- System configuration
- Monitoring and logging
- Backup and restore
- Performance monitoring

## 🔧 Running Admin Tests

### Individual Test Files
```bash
# Run specific admin test
python -m pytest tests/admin/test_admin_unlimited_access.py -v

# Run all admin tests
python -m pytest tests/admin/ -v

# Run with coverage
python -m pytest tests/admin/ --cov=polling.admin_views --cov-report=html
```

### Test Configuration
```python
# Test settings for admin tests
ADMIN_TEST_USER = {
    'username': 'test_admin',
    'password': 'test_password',
    'email': 'admin@test.com'
}

# Test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}
```

## 📊 Test Coverage Goals

### Current Coverage
- ✅ Admin authentication
- ✅ Unlimited access features
- ✅ Session management
- ✅ Basic game control

### Target Coverage
- 📋 Complete admin panel functionality
- 📋 All admin API endpoints
- 📋 Error handling scenarios
- 📋 Security edge cases

## 🔍 Test Data Setup

### Admin User Creation
```python
from polling.models import Admin

def create_test_admin():
    return Admin.objects.create(
        username='test_admin',
        email='admin@test.com',
        password='hashed_password',
        is_active=True
    )
```

### Game Data Setup
```python
from polling.models import GameRound, Player

def create_test_game_data():
    # Create test players
    player = Player.objects.create(
        username='test_player',
        email='player@test.com'
    )
    
    # Create test game round
    game_round = GameRound.objects.create(
        round_number=1,
        status='active'
    )
    
    return player, game_round
```

## 🚨 Test Scenarios

### Security Tests
- Unauthorized access attempts
- Session hijacking prevention
- CSRF protection
- Input validation

### Performance Tests
- Admin panel load times
- API response times
- Database query optimization
- Concurrent admin access

### Integration Tests
- Admin panel with game engine
- Admin actions affecting users
- Real-time updates
- WebSocket connections

## 📋 Test Checklist

### Before Running Tests
- [ ] Test database is clean
- [ ] Required test data is created
- [ ] Environment variables are set
- [ ] Dependencies are installed

### After Running Tests
- [ ] All tests pass
- [ ] Coverage meets requirements
- [ ] No test data pollution
- [ ] Performance benchmarks met

## 📚 Related Documentation

- **[Admin Documentation](../../docs/admin/)** - Admin panel guides
- **[Solutions Documentation](../../docs/solutions/)** - Problem solutions
- **[System Documentation](../../docs/system/)** - System architecture
