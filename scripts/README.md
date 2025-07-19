# Scripts

This directory contains utility scripts for managing the Color Prediction Game project, organized by purpose and functionality.

## Directory Structure

### 📁 **admin/** - Admin Management Scripts
- `admin_helper.py` - Helper functions for admin operations
- `check_admin_status.py` - Verify admin user status and permissions
- `create_admin.py` - Create new admin users

### 📁 **data/** - Data Management Scripts
- `create_test_data.py` - Generate test data for development
- `create_test_rounds.py` - Create test game rounds

### 📁 **development/** - Development Tools
- `run_tests.py` - Comprehensive test runner script
- `test_all.sh` - Shell script to run all tests
- `test_db.py` - Database testing utilities

### 📁 **maintenance/** - System Maintenance Scripts
- `cleanup_files.py` - Clean up temporary and unnecessary files
- `create_migrations.py` - Generate Django migrations
- `diagnose_red_error.py` - Diagnose and fix red color errors
- `fix_migrations_completely.py` - Complete migration fixes
- `fix_stuck_rounds.py` - Fix stuck game rounds
- `fix_withdrawal_database.py` - Fix withdrawal database issues
- `flush_and_clean_db.py` - Clean database and reset state
- `force_fix_migrations.py` - Force migration fixes
- `quick_clean.py` - Quick cleanup operations
- `run_migration_fix.py` - Run migration fixes

### 📁 **monitoring/** - System Monitoring
- `payment_system_monitor.py` - Monitor payment system health

### 📁 **setup/** - Initial Setup Scripts
- `initialize_master_wallet.py` - Set up master wallet
- `populate_notification_types.py` - Initialize notification types
- `reset_all_wallets_to_zero.py` - Reset all user wallets
- `update_notification_settings.py` - Update notification configurations

### 📁 **utilities/** - General Utilities
- `cleanup_project.py` - Project-wide cleanup operations
- `fix_payment_credits.py` - Fix payment credit issues
- `fix_websocket_issues.py` - Resolve WebSocket problems
- `manage_files.py` - File management utilities

## Usage Guidelines

### Running Scripts
```bash
# From project root
cd /path/to/WebSocket_Test
python scripts/category/script_name.py
```

### Safety Notes
- Always backup your database before running maintenance scripts
- Test scripts in development environment first
- Review script contents before execution
- Some scripts may require environment variables or configuration

### Script Categories

**🔧 Maintenance**: Use when system needs repair or cleanup
**📊 Data**: Use for managing test data and database content
**👤 Admin**: Use for admin user management
**🚀 Setup**: Use during initial system setup
**🔍 Monitoring**: Use for system health checks
**🛠️ Utilities**: Use for general project maintenance

## Directory Structure

### `/admin/`
Scripts for administrative tasks:
- `create_admin.py` - Create admin user accounts
- `admin_helper.py` - Admin utility functions

### `/data/`
Scripts for data management:
- `create_test_data.py` - Generate test data for development
- `create_test_rounds.py` - Create test game rounds

### `/maintenance/`
Scripts for system maintenance:
- `fix_stuck_rounds.py` - Fix stuck or incomplete game rounds
- `diagnose_red_error.py` - Diagnose red color betting errors

## Script Usage

### Admin Scripts

#### Create Admin User
```bash
python scripts/admin/create_admin.py
```
Creates a new admin user with full privileges.

#### Admin Helper
```bash
python scripts/admin/admin_helper.py
```
Provides various admin utility functions.

### Data Scripts

#### Create Test Data
```bash
python scripts/data/create_test_data.py
```
Generates sample users, wallets, and betting data for testing.

#### Create Test Rounds
```bash
python scripts/data/create_test_rounds.py
```
Creates test game rounds with various states for testing.

### Maintenance Scripts

#### Fix Stuck Rounds
```bash
python scripts/maintenance/fix_stuck_rounds.py
```
Identifies and fixes game rounds that are stuck in incomplete states.

#### Diagnose Red Error
```bash
python scripts/maintenance/diagnose_red_error.py
```
Diagnoses issues with red color betting functionality.

## Running Scripts

### From Project Root
```bash
# Make sure you're in the project root directory
cd /path/to/WebSocket_Test

# Activate virtual environment
source env/bin/activate

# Run scripts
python scripts/admin/create_admin.py
python scripts/data/create_test_data.py
```

### Script Requirements
- All scripts should be run from the project root directory
- Virtual environment should be activated
- Django settings should be properly configured

## Creating New Scripts

### Script Template
```python
#!/usr/bin/env python
"""
Script description here.
"""
import os
import sys
import django

# Add project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

# Your script code here
from polling.models import User, Wallet

def main():
    """Main script function."""
    print("Script starting...")
    # Your logic here
    print("Script completed.")

if __name__ == '__main__':
    main()
```

### Script Guidelines
1. Include proper Django setup
2. Add descriptive docstrings
3. Handle errors gracefully
4. Provide clear output messages
5. Use logging for important operations

### Script Categories

#### Admin Scripts
- User management
- Permission management
- System configuration

#### Data Scripts
- Test data generation
- Data migration
- Data cleanup

#### Maintenance Scripts
- System diagnostics
- Error fixing
- Performance optimization
- Database maintenance

## Best Practices

1. **Error Handling**: Always include proper error handling
2. **Logging**: Use Django's logging system for important operations
3. **Transactions**: Use database transactions for data modifications
4. **Validation**: Validate input parameters
5. **Documentation**: Include clear usage instructions

## Security Considerations

- Scripts that modify data should include confirmation prompts
- Admin scripts should verify user permissions
- Sensitive operations should be logged
- Production scripts should have additional safety checks
