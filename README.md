# Color Prediction Game

A real-time color prediction betting game built with Django, WebSockets, and modern web technologies.

## Features

- **Real-time Betting**: Live color prediction game with WebSocket support
- **User Authentication**: Secure user registration and login system
- **Wallet System**: Complete wallet functionality for deposits, withdrawals, and betting
- **Admin Panel**: Custom admin interface for game management
- **Betting History**: Comprehensive betting history and statistics
- **Mobile Responsive**: Works seamlessly on desktop and mobile devices

## Game Mechanics

- **Round Duration**: 50 seconds total (40 seconds betting + 10 seconds result)
- **Colors**: Red, Green, Violet (with additional colors planned)
- **Betting**: Users can place bets during the 40-second betting window
- **Results**: Game results appear within 5 seconds with loading animations

## Project Structure

```
WebSocket_Test/
├── 📁 Core Application
│   ├── polling/               # Main Django app
│   ├── server/               # Django project settings
│   ├── templates/            # HTML templates
│   ├── static/              # CSS, JS, images
│   └── media/               # User uploaded files
│
├── 📁 Infrastructure
│   ├── deployment/          # Docker, production configs
│   ├── logs/               # Application logs
│   ├── logs_archive/       # Archived logs
│   └── env/                # Virtual environment
│
├── 📁 Development
│   ├── tests/              # Comprehensive test suite
│   │   ├── unit/           # Unit tests
│   │   ├── integration/    # Integration tests
│   │   ├── payment/        # Payment system tests
│   │   ├── wallet/         # Wallet system tests
│   │   └── admin/          # Admin panel tests
│   ├── scripts/            # Organized utility scripts
│   │   ├── admin/          # Admin management
│   │   ├── data/           # Data operations
│   │   ├── development/    # Development tools
│   │   ├── maintenance/    # System maintenance
│   │   ├── monitoring/     # Health checks
│   │   ├── setup/          # Initial setup
│   │   └── utilities/      # General utilities
│   ├── docs/               # Comprehensive documentation
│   │   ├── admin/          # Admin documentation
│   │   ├── api/            # API documentation
│   │   ├── email/          # Email setup guides
│   │   ├── project/        # Project management
│   │   ├── solutions/      # Problem solutions
│   │   ├── system/         # Technical documentation
│   │   └── user/           # User guides
│   └── data/               # Data management
│       ├── backups/        # Database backups
│       └── fixtures/       # Test data
│
├── 📁 Root Level (Essential Files Only)
│   ├── manage.py           # Django management
│   ├── requirements.txt    # Dependencies
│   ├── requirements-test.txt # Test dependencies
│   ├── pytest.ini         # Test configuration
│   ├── db.sqlite3         # Development database
│   └── README.md           # This file
```

## Quick Start

1. **Setup Environment**:
   ```bash
   python -m venv env
   source env/bin/activate  # On Windows: env\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Database Setup**:
   ```bash
   python manage.py migrate
   python scripts/admin/create_admin.py  # Create admin user
   ```

3. **Run Development Server**:
   ```bash
   python manage.py runserver
   ```

4. **Access the Application**:
   - Game: http://localhost:8000/
   - Admin Panel: http://localhost:8000/admin-panel/

## 🧹 **Recently Organized Structure**

This project has been recently reorganized for better maintainability:

- **📄 Documentation**: All `.md` files moved to `docs/` with proper categorization
- **🔧 Scripts**: All utility scripts organized in `scripts/` subdirectories
- **🧪 Tests**: All test files properly categorized in `tests/`
- **🐳 Docker**: Duplicate configuration files removed
- **📁 Root**: Only essential project files remain in root directory

## Testing

Run comprehensive tests using:
```bash
# All tests
python scripts/development/run_tests.py

# Specific test categories
python -m pytest tests/unit/          # Unit tests
python -m pytest tests/integration/   # Integration tests
python -m pytest tests/payment/       # Payment system tests
python -m pytest tests/wallet/        # Wallet system tests
python -m pytest tests/admin/         # Admin panel tests

# Run test shell script
bash scripts/development/test_all.sh

# Development and debugging
python scripts/development/debug_timer.py        # Timer debugging
python scripts/monitoring/diagnose_websocket_stability.py  # WebSocket diagnostics
```

## Deployment

See `deployment/` directory for production deployment files:
- `Dockerfile.production`
- `docker-compose.production.yml`
- `deploy.sh`

## Documentation

Comprehensive documentation is organized in the `docs/` directory:

### 📚 **Quick Access**
- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Complete project overview
- **[File Organization Standards](docs/project/FILE_ORGANIZATION_STANDARDS.md)** - Organization standards
- **[File Management Guidelines](docs/project/FILE_MANAGEMENT_GUIDELINES.md)** - Management procedures
- **[Admin Panel Guide](docs/admin/)** - Admin interface documentation
- **[API Reference](docs/api/)** - API documentation
- **[System Documentation](docs/system/)** - Technical guides
- **[User Guides](docs/user/)** - End-user documentation
- **[Solutions Database](docs/solutions/)** - Problem fixes and solutions

### 🔧 **Development Resources**
- **Scripts**: Use `scripts/` for common development tasks
- **Tests**: Comprehensive test suite in `tests/`
- **Deployment**: Production configs in `deployment/`

## File Organization

This project follows strict file organization guidelines:
- **Root directory**: Only essential project files (manage.py, requirements.txt, README.md, etc.)
- **Scripts**: Organized by purpose in `scripts/` subdirectories
- **Documentation**: Categorized in `docs/` subdirectories with proper structure
- **Tests**: Structured by functionality in `tests/`
- **No clutter**: All utility scripts, documentation, and test files properly organized

See `docs/project/FILE_ORGANIZATION_STANDARDS.md` for detailed organization rules and `docs/project/FILE_MANAGEMENT_GUIDELINES.md` for management procedures.

## 🛠️ **Utility Scripts**

Common development tasks are organized in the `scripts/` directory:

```bash
# Development and debugging
scripts/development/debug_timer.py           # Timer system debugging
scripts/development/run_tests.py             # Comprehensive test runner

# Maintenance and fixes
scripts/maintenance/fix_timer.py             # Timer system fixes
scripts/maintenance/emergency_websocket_reset.py  # WebSocket emergency reset

# Utilities and tools
scripts/utilities/fix_balance_precision.py   # Balance precision fixes
scripts/utilities/fix_all_currency.py        # Currency conversion fixes
scripts/utilities/verify_currency_conversion.py  # Currency verification

# Monitoring and diagnostics
scripts/monitoring/diagnose_websocket_stability.py  # WebSocket diagnostics
scripts/monitoring/payment_system_monitor.py        # Payment monitoring

# Admin tools
scripts/admin/create_admin.py                # Create admin user
scripts/admin/check_admin_status.py          # Admin status check
```

## Contributing

1. Follow the established file organization structure
2. Place new files in appropriate directories
3. Write tests for new features
4. Update documentation as needed
5. Use existing scripts in `scripts/` for common tasks
6. Follow naming conventions outlined in the guidelines

## License

This project is proprietary software.
