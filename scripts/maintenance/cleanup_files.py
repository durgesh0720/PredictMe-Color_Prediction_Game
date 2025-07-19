#!/usr/bin/env python
"""
Simple file cleanup script
"""

import os
import shutil
import glob

def clean_migrations():
    """Clean migration files except __init__.py"""
    print("🧹 Cleaning migration files...")
    
    migration_files = glob.glob('polling/migrations/0*.py')
    for file_path in migration_files:
        os.remove(file_path)
        print(f"🗑️  Removed: {file_path}")
    
    # Clean migration cache
    cache_dir = 'polling/migrations/__pycache__'
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print(f"🗑️  Removed: {cache_dir}")

def clean_all_cache():
    """Clean all Python cache files"""
    print("🧹 Cleaning all cache files...")
    
    # Remove __pycache__ directories
    for root, dirs, files in os.walk('.'):
        for dir_name in dirs:
            if dir_name == '__pycache__':
                cache_path = os.path.join(root, dir_name)
                shutil.rmtree(cache_path)
                print(f"🗑️  Removed: {cache_path}")
    
    # Remove .pyc files
    for root, dirs, files in os.walk('.'):
        for file_name in files:
            if file_name.endswith(('.pyc', '.pyo')):
                file_path = os.path.join(root, file_name)
                os.remove(file_path)
                print(f"🗑️  Removed: {file_path}")

def backup_database():
    """Backup database"""
    if os.path.exists('db.sqlite3'):
        shutil.copy2('db.sqlite3', 'db_backup.sqlite3')
        print("📦 Database backed up to db_backup.sqlite3")
    else:
        print("ℹ️  No database file found")

def remove_database():
    """Remove database file"""
    if os.path.exists('db.sqlite3'):
        os.remove('db.sqlite3')
        print("🗑️  Database removed")
    else:
        print("ℹ️  No database file found")

def main():
    """Main cleanup function"""
    print("🧹 File Cleanup Options")
    print("=" * 30)
    print("1. Clean migration files only")
    print("2. Clean all cache files")
    print("3. Backup database")
    print("4. Remove database")
    print("5. Full cleanup (migrations + cache + backup + remove db)")
    print("6. Exit")
    
    choice = input("\nSelect option (1-6): ")
    
    if choice == '1':
        clean_migrations()
    elif choice == '2':
        clean_all_cache()
    elif choice == '3':
        backup_database()
    elif choice == '4':
        confirm = input("⚠️  This will delete the database. Continue? (y/n): ")
        if confirm.lower() in ['y', 'yes']:
            remove_database()
    elif choice == '5':
        confirm = input("⚠️  This will delete migrations and database. Continue? (y/n): ")
        if confirm.lower() in ['y', 'yes']:
            backup_database()
            clean_migrations()
            clean_all_cache()
            remove_database()
            print("\n✅ Full cleanup completed!")
            print("Now run:")
            print("  python manage.py makemigrations")
            print("  python manage.py migrate")
    elif choice == '6':
        print("👋 Goodbye!")
        return
    else:
        print("❌ Invalid choice")
    
    print("\n✅ Cleanup completed!")

if __name__ == "__main__":
    main()
