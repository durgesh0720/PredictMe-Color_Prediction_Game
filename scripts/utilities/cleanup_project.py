#!/usr/bin/env python
"""
Project Cleanup Script
Organize and remove unnecessary files
"""
import os
import shutil
from pathlib import Path

def cleanup_project():
    """Clean up and organize project files"""
    print("🧹 Starting Project Cleanup...\n")
    
    # Files to move to tests directory
    test_files = [
        'debug_payment_issue.py',
        'test_csp_fix.py',
        'test_email.py',
        'test_email_verification_and_profile.py',
        'test_integrated_notifications.py',
        'test_notification_signals.py',
        'test_notification_system.py',
        'test_one_bet_per_round.py',
        'test_payment_basic.py',
        'test_payment_dashboard.py',
        'test_razorpay_complete.py',
        'test_razorpay_integration.py',
        'test_razorpay_live.py',
        'test_real_money_wallet.py',
        'test_timer_fixes.py',
        'test_wallet_simple.py'
    ]
    
    # Temporary/utility files to move to scripts
    script_files = [
        'fix_websocket_issues.py',
        'initialize_master_wallet.py',
        'populate_notification_types.py',
        'script1.py'
    ]
    
    # Files to remove (temporary/unnecessary)
    files_to_remove = [
        'test_verification_reminder.html',
        'static/test_razorpay_simple.html'
    ]
    
    # Create directories if they don't exist
    os.makedirs('tests/payment', exist_ok=True)
    os.makedirs('tests/wallet', exist_ok=True)
    os.makedirs('tests/notifications', exist_ok=True)
    os.makedirs('tests/misc', exist_ok=True)
    os.makedirs('scripts/setup', exist_ok=True)
    os.makedirs('scripts/utilities', exist_ok=True)
    
    moved_count = 0
    removed_count = 0
    
    # Move test files to appropriate test directories
    print("📁 Moving test files to tests directory...")
    for file in test_files:
        if os.path.exists(file):
            try:
                # Determine subdirectory based on file name
                if 'payment' in file or 'razorpay' in file:
                    dest_dir = 'tests/payment/'
                elif 'wallet' in file:
                    dest_dir = 'tests/wallet/'
                elif 'notification' in file or 'email' in file:
                    dest_dir = 'tests/notifications/'
                else:
                    dest_dir = 'tests/misc/'
                
                dest_path = dest_dir + file
                shutil.move(file, dest_path)
                print(f"  ✅ Moved {file} → {dest_path}")
                moved_count += 1
            except Exception as e:
                print(f"  ❌ Failed to move {file}: {e}")
    
    # Move script files to scripts directory
    print("\n📁 Moving utility scripts...")
    for file in script_files:
        if os.path.exists(file):
            try:
                if 'initialize' in file or 'populate' in file:
                    dest_dir = 'scripts/setup/'
                else:
                    dest_dir = 'scripts/utilities/'
                
                dest_path = dest_dir + file
                shutil.move(file, dest_path)
                print(f"  ✅ Moved {file} → {dest_path}")
                moved_count += 1
            except Exception as e:
                print(f"  ❌ Failed to move {file}: {e}")
    
    # Remove unnecessary files
    print("\n🗑️ Removing unnecessary files...")
    for file in files_to_remove:
        if os.path.exists(file):
            try:
                os.remove(file)
                print(f"  ✅ Removed {file}")
                removed_count += 1
            except Exception as e:
                print(f"  ❌ Failed to remove {file}: {e}")
    
    # Clean up empty __pycache__ directories
    print("\n🧹 Cleaning up __pycache__ directories...")
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                pycache_path = os.path.join(root, dir_name)
                try:
                    shutil.rmtree(pycache_path)
                    print(f"  ✅ Removed {pycache_path}")
                    removed_count += 1
                except Exception as e:
                    print(f"  ❌ Failed to remove {pycache_path}: {e}")
    
    return moved_count, removed_count

def create_project_structure_doc():
    """Create documentation for the project structure"""
    structure_doc = """# Project Structure

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
tests/                     # All test files organized by category
├── payment/              # Payment system tests
├── wallet/               # Wallet system tests
├── notifications/        # Notification system tests
├── integration/          # Integration tests
├── unit/                 # Unit tests
└── misc/                 # Miscellaneous tests
```

## Scripts & Utilities
```
scripts/                   # Utility scripts
├── setup/                # Setup and initialization scripts
├── utilities/            # General utility scripts
├── maintenance/          # Maintenance scripts
├── admin/               # Admin utility scripts
└── data/                # Data management scripts
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
docs/                    # Project documentation
├── admin/              # Admin documentation
├── user/               # User documentation
└── system/             # System documentation
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
"""
    
    with open('docs/PROJECT_STRUCTURE.md', 'w') as f:
        f.write(structure_doc)
    
    print("📚 Created PROJECT_STRUCTURE.md documentation")

def main():
    """Main cleanup function"""
    print("🚀 Project Cleanup and Organization\n")
    print("=" * 50)
    
    moved_count, removed_count = cleanup_project()
    
    print(f"\n📊 Cleanup Summary:")
    print(f"  📁 Files moved: {moved_count}")
    print(f"  🗑️ Files removed: {removed_count}")
    
    # Create project structure documentation
    create_project_structure_doc()
    
    print(f"\n✅ Project cleanup completed!")
    print(f"\n📋 Organized Structure:")
    print(f"  📁 tests/ - All test files organized by category")
    print(f"  📁 scripts/ - Utility and setup scripts")
    print(f"  📁 docs/ - Project documentation")
    print(f"  🧹 Removed temporary and cache files")
    
    print(f"\n🎯 Next Steps:")
    print(f"  1. Review the organized file structure")
    print(f"  2. Update any import paths if needed")
    print(f"  3. Check docs/PROJECT_STRUCTURE.md for overview")
    print(f"  4. Run tests to ensure everything works")

if __name__ == '__main__':
    main()
