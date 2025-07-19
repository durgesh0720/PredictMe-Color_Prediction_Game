#!/usr/bin/env python
"""
Quick database clean script - removes migrations and database for fresh start
"""

import os
import shutil
import glob

def main():
    print("🧹 Quick database cleanup...")
    
    # 1. Backup database
    if os.path.exists('db.sqlite3'):
        shutil.copy2('db.sqlite3', 'db_backup.sqlite3')
        print("✅ Database backed up to db_backup.sqlite3")
    
    # 2. Remove database
    if os.path.exists('db.sqlite3'):
        os.remove('db.sqlite3')
        print("🗑️  Removed database")
    
    # 3. Clean migration files
    migration_files = glob.glob('polling/migrations/0*.py')
    for file_path in migration_files:
        os.remove(file_path)
        print(f"🗑️  Removed {file_path}")
    
    # 4. Clean cache
    if os.path.exists('polling/migrations/__pycache__'):
        shutil.rmtree('polling/migrations/__pycache__')
        print("🗑️  Removed migration cache")
    
    print("\n✅ Quick cleanup completed!")
    print("Now run:")
    print("  python manage.py makemigrations")
    print("  python manage.py migrate")
    print("  python manage.py createsuperuser")

if __name__ == "__main__":
    main()
