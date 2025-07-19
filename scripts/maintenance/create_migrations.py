#!/usr/bin/env python
"""
Script to safely create migrations for the withdrawal system
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def main():
    """Main function to create migrations safely"""
    
    print("🚀 Creating migrations for withdrawal system...")
    
    # Step 1: Check current migration status
    print("\n📋 Checking current migration status...")
    run_command("python manage.py showmigrations polling", "Checking migrations")
    
    # Step 2: Create migrations with automatic defaults
    print("\n🔄 Creating new migrations...")
    
    # Set environment variable to automatically provide defaults
    os.environ['DJANGO_SETTINGS_MODULE'] = 'server.settings'
    
    # Try to create migrations
    if run_command("python manage.py makemigrations polling --empty", "Creating empty migration"):
        print("✅ Empty migration created successfully")
        
        # Now try to create the actual migrations
        if run_command("python manage.py makemigrations polling", "Creating model migrations"):
            print("✅ Model migrations created successfully")
            
            # Apply migrations
            if run_command("python manage.py migrate", "Applying migrations"):
                print("\n🎉 All migrations completed successfully!")
                return True
            else:
                print("\n❌ Migration application failed")
                return False
        else:
            print("\n❌ Model migration creation failed")
            return False
    else:
        print("\n❌ Empty migration creation failed")
        return False

if __name__ == "__main__":
    if main():
        print("\n🎉 Migration creation completed successfully!")
        print("\n📋 Next steps:")
        print("1. Test withdrawal functionality")
        print("2. Check admin panel at /control-panel/withdrawals/")
        print("3. Verify all features are working")
    else:
        print("\n❌ Migration creation failed.")
        print("\nTry running manually:")
        print("python manage.py makemigrations polling")
        print("python manage.py migrate")
