# Tests

This directory contains all test files for the Color Prediction Game project.

## Directory Structure

### `/unit/`
Unit tests for individual components:
- `test_models.py` - Database model tests
- `test_views.py` - View function tests
- `test_wallet.py` - Wallet functionality tests
- `test_template_filters.py` - Template filter tests
- `tests.py` - General unit tests

### `/integration/`
Integration tests for component interactions:
- End-to-end workflow tests
- API integration tests
- Database integration tests

### `/html/`
HTML test files for frontend testing:
- `admin_login_test.html` - Admin login testing
- `test_admin_js.html` - Admin JavaScript testing
- `test_js_syntax.html` - JavaScript syntax testing
- `test_red_error.html` - Error handling testing

## Running Tests

### Unit Tests
```bash
# Run all unit tests
python manage.py test polling

# Run specific test file
python manage.py test polling.test_models
python manage.py test polling.test_wallet

# Run with verbose output
python manage.py test polling --verbosity=2
```

### Individual Test Files
```bash
# Run specific test files
python tests/unit/test_models.py
python tests/unit/test_wallet.py
python tests/unit/test_views.py
```

### HTML Tests
Open HTML test files in a browser to test frontend functionality:
- `tests/html/admin_login_test.html`
- `tests/html/test_admin_js.html`

## Test Categories

### Model Tests (`test_models.py`)
- User model validation
- Game round model tests
- Bet model functionality
- Wallet model operations

### View Tests (`test_views.py`)
- Authentication views
- Game views
- Admin views
- API endpoints

### Wallet Tests (`test_wallet.py`)
- Wallet creation
- Balance operations
- Transaction handling
- Betting operations

### Template Filter Tests (`test_template_filters.py`)
- Custom template filters
- Data formatting
- Display logic

## Writing New Tests

### Unit Test Guidelines
1. Test one functionality per test method
2. Use descriptive test method names
3. Include setup and teardown methods
4. Mock external dependencies

### Test File Naming
- Unit tests: `test_<component>.py`
- Integration tests: `integration_test_<feature>.py`
- HTML tests: `test_<feature>.html`

### Example Test Structure
```python
from django.test import TestCase
from polling.models import User, Wallet

class WalletTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_wallet_creation(self):
        wallet = Wallet.objects.create(user=self.user)
        self.assertEqual(wallet.balance, 0)
    
    def tearDown(self):
        # Cleanup if needed
        pass
```

## Test Data

Use the scripts in `scripts/data/` to create test data:
- `create_test_data.py` - General test data
- `create_test_rounds.py` - Test game rounds

## Continuous Integration

Tests should be run before:
- Committing code changes
- Deploying to production
- Merging pull requests

## Coverage

To check test coverage:
```bash
pip install coverage
coverage run --source='.' manage.py test polling
coverage report
coverage html  # Generates HTML coverage report
```
