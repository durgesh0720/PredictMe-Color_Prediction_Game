#!/usr/bin/env python
"""
Complete database flush and clean script
This will reset everything to a fresh state
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
from django.contrib.auth.models import User
from django.utils import timezone

def backup_database():
    """Create a backup of the current database"""
    print("📦 Creating database backup...")
    try:
        if os.path.exists('db.sqlite3'):
            backup_name = f"db_backup_{timezone.now().strftime('%Y%m%d_%H%M%S')}.sqlite3"
            shutil.copy2('db.sqlite3', backup_name)
            print(f"✅ Database backed up to: {backup_name}")
            return backup_name
        else:
            print("ℹ️  No existing database found")
            return None
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return None

def clean_migration_files():
    """Remove all migration files except __init__.py"""
    print("🧹 Cleaning migration files...")
    
    migration_dirs = [
        'polling/migrations',
        # Add other app migration directories if needed
    ]
    
    for migration_dir in migration_dirs:
        if os.path.exists(migration_dir):
            # Remove all .py files except __init__.py
            for file_path in glob.glob(f"{migration_dir}/*.py"):
                if not file_path.endswith('__init__.py'):
                    os.remove(file_path)
                    print(f"🗑️  Removed: {file_path}")
            
            # Remove __pycache__ directory
            pycache_dir = os.path.join(migration_dir, '__pycache__')
            if os.path.exists(pycache_dir):
                shutil.rmtree(pycache_dir)
                print(f"🗑️  Removed: {pycache_dir}")

def clean_database():
    """Remove the database file"""
    print("🗑️  Removing database file...")
    if os.path.exists('db.sqlite3'):
        os.remove('db.sqlite3')
        print("✅ Database file removed")
    else:
        print("ℹ️  No database file found")

def clean_cache_files():
    """Remove Python cache files"""
    print("🧹 Cleaning Python cache files...")
    
    # Remove __pycache__ directories
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                pycache_path = os.path.join(root, dir_name)
                shutil.rmtree(pycache_path)
                print(f"🗑️  Removed: {pycache_path}")
    
    # Remove .pyc files
    for root, dirs, files in os.walk('.'):
        for file_name in files:
            if file_name.endswith('.pyc'):
                pyc_path = os.path.join(root, file_name)
                os.remove(pyc_path)
                print(f"🗑️  Removed: {pyc_path}")

def create_fresh_migrations():
    """Create fresh migrations"""
    print("🔧 Creating fresh migrations...")
    try:
        execute_from_command_line(['manage.py', 'makemigrations'])
        print("✅ Fresh migrations created")
        return True
    except Exception as e:
        print(f"❌ Migration creation failed: {e}")
        return False

def apply_migrations():
    """Apply all migrations"""
    print("🔧 Applying migrations...")
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Migrations applied successfully")
        return True
    except Exception as e:
        print(f"❌ Migration application failed: {e}")
        return False

def create_superuser():
    """Create a default superuser"""
    print("👤 Creating default superuser...")
    try:
        from django.contrib.auth.models import User
        
        # Check if superuser already exists
        if User.objects.filter(is_superuser=True).exists():
            print("ℹ️  Superuser already exists")
            return True
        
        # Create superuser
        User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
        print("✅ Superuser created:")
        print("   Username: admin")
        print("   Password: admin123")
        print("   Email: admin@example.com")
        return True
    except Exception as e:
        print(f"❌ Superuser creation failed: {e}")
        return False

def create_default_admin():
    """Create default admin for the polling app"""
    print("👤 Creating default polling admin...")
    try:
        from polling.models import Admin
        
        # Check if admin already exists
        if Admin.objects.filter(username='admin').exists():
            print("ℹ️  Polling admin already exists")
            return True
        
        # Create admin
        admin = Admin.objects.create(
            username='admin',
            email='admin@example.com',
            is_active=True
        )
        admin.set_password('admin123')
        admin.save()
        
        print("✅ Polling admin created:")
        print("   Username: admin")
        print("   Password: admin123")
        return True
    except Exception as e:
        print(f"❌ Polling admin creation failed: {e}")
        return False

def create_default_master_wallet():
    """Create default master wallet"""
    print("💰 Creating default master wallet...")
    try:
        from polling.models import MasterWallet
        
        # Check if master wallet exists
        if MasterWallet.objects.exists():
            print("ℹ️  Master wallet already exists")
            return True
        
        # Create master wallet
        MasterWallet.objects.create(
            total_balance=0,
            available_balance=0,
            reserved_balance=0,
            total_deposits_received=0,
            total_withdrawals_paid=0
        )
        print("✅ Default master wallet created")
        return True
    except Exception as e:
        print(f"❌ Master wallet creation failed: {e}")
        return False

def create_test_player():
    """Create a test player for testing"""
    print("👤 Creating test player...")
    try:
        from polling.models import Player
        
        # Check if test player exists
        if Player.objects.filter(username='testuser').exists():
            print("ℹ️  Test player already exists")
            return True
        
        # Create test player
        player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000,  # Give some initial balance for testing
            is_active=True
        )
        player.set_password('test123')
        player.save()
        
        print("✅ Test player created:")
        print("   Username: testuser")
        print("   Password: test123")
        print("   Balance: ₹1000")
        return True
    except Exception as e:
        print(f"❌ Test player creation failed: {e}")
        return False

def verify_system():
    """Verify that everything is working"""
    print("🧪 Verifying system...")
    try:
        from polling.models import Player, Admin, MasterWallet, WalletTransaction, WithdrawalRequest
        
        # Test model queries
        player_count = Player.objects.count()
        admin_count = Admin.objects.count()
        master_wallet_count = MasterWallet.objects.count()
        wallet_transaction_count = WalletTransaction.objects.count()
        withdrawal_count = WithdrawalRequest.objects.count()
        
        print(f"✅ Players: {player_count}")
        print(f"✅ Admins: {admin_count}")
        print(f"✅ Master wallets: {master_wallet_count}")
        print(f"✅ Wallet transactions: {wallet_transaction_count}")
        print(f"✅ Withdrawal requests: {withdrawal_count}")
        
        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table';")
            table_count = cursor.fetchone()[0]
            print(f"✅ Database tables: {table_count}")
        
        print("✅ System verification completed successfully!")
        return True
    except Exception as e:
        print(f"❌ System verification failed: {e}")
        return False

def main():
    """Main function to orchestrate the cleanup"""
    print("🚀 Starting complete database flush and clean...")
    print("=" * 60)
    
    # Ask for confirmation
    response = input("⚠️  This will DELETE ALL DATA. Continue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("❌ Operation cancelled")
        return False
    
    # Step 1: Backup database
    backup_file = backup_database()
    
    # Step 2: Clean cache files
    clean_cache_files()
    
    # Step 3: Clean migration files
    clean_migration_files()
    
    # Step 4: Remove database
    clean_database()
    
    # Step 5: Create fresh migrations
    if not create_fresh_migrations():
        print("❌ Failed to create migrations")
        return False
    
    # Step 6: Apply migrations
    if not apply_migrations():
        print("❌ Failed to apply migrations")
        return False
    
    # Step 7: Create default users
    create_superuser()
    create_default_admin()
    
    # Step 8: Create default data
    create_default_master_wallet()
    create_test_player()
    
    # Step 9: Verify system
    if not verify_system():
        print("❌ System verification failed")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Database flush and clean completed successfully!")
    print("\n📋 Default accounts created:")
    print("   Django Admin: admin / admin123")
    print("   Polling Admin: admin / admin123")
    print("   Test Player: testuser / test123 (₹1000 balance)")
    print("\n🔗 Access URLs:")
    print("   Django Admin: http://localhost:8000/admin/")
    print("   Polling Admin: http://localhost:8000/control-panel/")
    print("   User Interface: http://localhost:8000/")
    print("   Withdrawal Test: http://localhost:8000/wallet/")
    print("\n💡 Test withdrawal with:")
    print("   Account: 123456789012")
    print("   IFSC: SBIN0001234")
    print("   Name: Test User")
    print("   Bank: State Bank of India")
    
    if backup_file:
        print(f"\n📦 Database backup saved as: {backup_file}")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
