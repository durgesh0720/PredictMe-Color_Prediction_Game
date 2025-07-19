#!/usr/bin/env python
"""
Comprehensive file management script for the color prediction game
"""

import os
import sys
import shutil
import glob
import django
from pathlib import Path

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.core.management import execute_from_command_line
from django.db import connection

def check_project_structure():
    """Check and display current project structure"""
    print("📁 Current project structure:")
    
    important_dirs = [
        'polling',
        'polling/migrations',
        'polling/templates',
        'polling/templates/admin',
        'polling/templates/auth',
        'static',
        'static/css',
        'static/js',
        'templates',
        'templates/payment',
    ]
    
    for dir_path in important_dirs:
        if os.path.exists(dir_path):
            file_count = len([f for f in os.listdir(dir_path) if os.path.isfile(os.path.join(dir_path, f))])
            print(f"  ✅ {dir_path} ({file_count} files)")
        else:
            print(f"  ❌ {dir_path} (missing)")

def clean_cache_files():
    """Remove all Python cache files"""
    print("\n🧹 Cleaning cache files...")
    
    cache_patterns = [
        '**/__pycache__',
        '**/*.pyc',
        '**/*.pyo',
        '**/*.pyd',
        '**/.pytest_cache',
    ]
    
    for pattern in cache_patterns:
        for path in glob.glob(pattern, recursive=True):
            if os.path.isdir(path):
                shutil.rmtree(path)
                print(f"🗑️  Removed directory: {path}")
            else:
                os.remove(path)
                print(f"🗑️  Removed file: {path}")

def check_migration_state():
    """Check current migration state"""
    print("\n📋 Checking migration state...")
    
    # Check migration files
    migration_files = glob.glob('polling/migrations/0*.py')
    print(f"Migration files found: {len(migration_files)}")
    for file_path in sorted(migration_files):
        print(f"  📄 {os.path.basename(file_path)}")
    
    # Check database migration records
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM django_migrations WHERE app='polling' ORDER BY name;")
            db_migrations = cursor.fetchall()
            print(f"Database migration records: {len(db_migrations)}")
            for migration in db_migrations:
                print(f"  📝 {migration[0]}")
    except Exception as e:
        print(f"❌ Could not check database migrations: {e}")

def check_database_tables():
    """Check what tables exist in the database"""
    print("\n🗄️  Checking database tables...")
    
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = cursor.fetchall()
            
            print(f"Total tables: {len(tables)}")
            
            # Categorize tables
            django_tables = [t[0] for t in tables if t[0].startswith('django_') or t[0].startswith('auth_')]
            polling_tables = [t[0] for t in tables if t[0].startswith('polling_') or t[0] in ['wallet_transactions', 'withdrawal_requests', 'master_wallet', 'master_wallet_transactions']]
            other_tables = [t[0] for t in tables if t[0] not in django_tables and t[0] not in polling_tables]
            
            print(f"\n📊 Django system tables ({len(django_tables)}):")
            for table in django_tables:
                print(f"  ✅ {table}")
            
            print(f"\n🎮 Polling app tables ({len(polling_tables)}):")
            for table in polling_tables:
                print(f"  ✅ {table}")
            
            if other_tables:
                print(f"\n❓ Other tables ({len(other_tables)}):")
                for table in other_tables:
                    print(f"  ❓ {table}")
                    
    except Exception as e:
        print(f"❌ Could not check database tables: {e}")

def check_important_files():
    """Check if important files exist"""
    print("\n📄 Checking important files...")
    
    important_files = [
        ('manage.py', 'Django management script'),
        ('server/settings.py', 'Django settings'),
        ('polling/models.py', 'Database models'),
        ('polling/views.py', 'View functions'),
        ('polling/urls.py', 'URL routing'),
        ('polling/admin_views.py', 'Admin views'),
        ('polling/payment_views.py', 'Payment views'),
        ('polling/payment_service.py', 'Payment service'),
        ('polling/fraud_detection.py', 'Fraud detection'),
        ('polling/payment_validation.py', 'Payment validation'),
        ('static/css/main.css', 'Main CSS file'),
        ('static/js/main.js', 'Main JavaScript file'),
        ('polling/templates/admin/modern_withdrawal_management.html', 'Withdrawal admin template'),
        ('polling/templates/auth/wallet.html', 'Wallet template'),
        ('templates/payment/dashboard.html', 'Payment dashboard'),
    ]
    
    for file_path, description in important_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  ✅ {file_path} ({size} bytes) - {description}")
        else:
            print(f"  ❌ {file_path} (missing) - {description}")

def create_fresh_migrations():
    """Create fresh migrations"""
    print("\n🔧 Creating fresh migrations...")
    try:
        execute_from_command_line(['manage.py', 'makemigrations', 'polling'])
        print("✅ Fresh migrations created")
        return True
    except Exception as e:
        print(f"❌ Migration creation failed: {e}")
        return False

def apply_migrations():
    """Apply migrations"""
    print("\n🔧 Applying migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrations applied")
        return True
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def test_models():
    """Test if models are working"""
    print("\n🧪 Testing models...")
    try:
        from polling.models import Player, Admin, MasterWallet, WalletTransaction, WithdrawalRequest
        
        # Test basic queries
        player_count = Player.objects.count()
        admin_count = Admin.objects.count()
        
        print(f"✅ Player model working (count: {player_count})")
        print(f"✅ Admin model working (count: {admin_count})")
        
        # Test withdrawal system models
        try:
            wallet_count = WalletTransaction.objects.count()
            withdrawal_count = WithdrawalRequest.objects.count()
            master_count = MasterWallet.objects.count()
            
            print(f"✅ WalletTransaction model working (count: {wallet_count})")
            print(f"✅ WithdrawalRequest model working (count: {withdrawal_count})")
            print(f"✅ MasterWallet model working (count: {master_count})")
            
        except Exception as e:
            print(f"⚠️  Withdrawal system models need setup: {e}")
        
        return True
    except Exception as e:
        print(f"❌ Model testing failed: {e}")
        return False

def create_essential_data():
    """Create essential data if missing"""
    print("\n🔧 Creating essential data...")
    
    try:
        from polling.models import MasterWallet
        
        # Create master wallet if missing
        if not MasterWallet.objects.exists():
            MasterWallet.objects.create(
                total_balance=0,
                available_balance=0,
                reserved_balance=0,
                total_deposits_received=0,
                total_withdrawals_paid=0
            )
            print("✅ Created default master wallet")
        else:
            print("✅ Master wallet already exists")
            
    except Exception as e:
        print(f"⚠️  Could not create essential data: {e}")

def show_next_steps():
    """Show what to do next"""
    print("\n📋 Next steps:")
    print("1. If migrations need to be created: python manage.py makemigrations")
    print("2. If migrations need to be applied: python manage.py migrate")
    print("3. Create superuser: python manage.py createsuperuser")
    print("4. Start server: python manage.py runserver")
    print("5. Test withdrawal system at: http://localhost:8000/wallet/")
    print("6. Access admin panel at: http://localhost:8000/control-panel/")

def main():
    """Main function"""
    print("🚀 File Management and System Check")
    print("=" * 50)
    
    # Check project structure
    check_project_structure()
    
    # Clean cache files
    clean_cache_files()
    
    # Check migration state
    check_migration_state()
    
    # Check database
    check_database_tables()
    
    # Check important files
    check_important_files()
    
    # Test models
    models_working = test_models()
    
    if not models_working:
        print("\n⚠️  Models not working. Need to create/apply migrations.")
        
        # Ask if user wants to create migrations
        response = input("\nCreate fresh migrations? (y/n): ")
        if response.lower() in ['y', 'yes']:
            if create_fresh_migrations():
                if apply_migrations():
                    test_models()
                    create_essential_data()
    else:
        create_essential_data()
    
    print("\n" + "=" * 50)
    print("✅ File management completed!")
    
    show_next_steps()

if __name__ == "__main__":
    main()
