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

# Run test shell script
bash scripts/development/test_all.sh
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
- **[File Management Guidelines](docs/project/FILE_MANAGEMENT_GUIDELINES.md)** - Organization standards
- **[Admin Panel Guide](docs/admin/)** - Admin interface documentation
- **[API Reference](docs/api/)** - API documentation
- **[System Documentation](docs/system/)** - Technical guides
- **[User Guides](docs/user/)** - End-user documentation

### 🔧 **Development Resources**
- **Scripts**: Use `scripts/` for common development tasks
- **Tests**: Comprehensive test suite in `tests/`
- **Deployment**: Production configs in `deployment/`

## File Organization

This project follows strict file organization guidelines:
- **Root directory**: Only essential project files
- **Scripts**: Organized by purpose in `scripts/` subdirectories
- **Documentation**: Categorized in `docs/` subdirectories
- **Tests**: Structured by functionality in `tests/`

See `docs/project/FILE_MANAGEMENT_GUIDELINES.md` for detailed organization rules.

## Contributing

1. Follow the established file organization structure
2. Place new files in appropriate directories
3. Write tests for new features
4. Update documentation as needed
5. Use existing scripts in `scripts/` for common tasks
6. Follow naming conventions outlined in the guidelines

## License

This project is proprietary software.
