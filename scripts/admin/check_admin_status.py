#!/usr/bin/env python3
"""
Check admin status and troubleshoot login issues
"""

import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Admin
from django.contrib.auth.hashers import check_password

def check_admin_status():
    """Check the status of admin users"""
    
    print("🔍 Checking Admin Status")
    print("=" * 50)
    
    # List all admins
    admins = Admin.objects.all()
    
    if not admins:
        print("❌ No admin users found in database!")
        print("\nTo create an admin user, run:")
        print("python scripts/admin/admin_helper.py")
        return
    
    print(f"📊 Found {admins.count()} admin user(s):")
    print()
    
    for admin in admins:
        print(f"👤 Admin: {admin.username}")
        print(f"   ID: {admin.id}")
        print(f"   Active: {'✅ Yes' if admin.is_active else '❌ No'}")
        print(f"   Created: {admin.created_at}")
        print(f"   Last Login: {admin.last_login if admin.last_login else 'Never'}")
        print(f"   Password Hash: {admin.password_hash[:20]}..." if admin.password_hash else "   Password Hash: None")
        print(f"   Balance: ${admin.balance}")
        print()
    
    # Check specific admin
    target_admin = input("Enter specific admin username to check (or press Enter to skip): ").strip()
    if not target_admin:
        print("⏭️ Skipping specific admin check")
        return
    
    try:
        admin = Admin.objects.get(username=target_admin)
        print(f"🎯 Checking specific admin: {target_admin}")
        print(f"   Status: {'✅ Active' if admin.is_active else '❌ Inactive'}")
        print(f"   Has Password: {'✅ Yes' if admin.password_hash else '❌ No'}")
        
        # Test password if provided
        test_password = input(f"\nEnter password to test for '{target_admin}' (or press Enter to skip): ").strip()
        if test_password:
            if admin.check_password(test_password):
                print("✅ Password is correct!")
            else:
                print("❌ Password is incorrect!")
                
    except Admin.DoesNotExist:
        print(f"❌ Admin '{target_admin}' not found!")
        print("\nTo create this admin, run:")
        print("python scripts/admin/admin_helper.py")

def create_admin_if_needed():
    """Create the durgesh_admin if it doesn't exist"""
    
    username = input("Enter specific admin username to check (or press Enter to skip): ").strip()
    if not username:
        print("⏭️ Skipping specific admin check")
        return
    
    if Admin.objects.filter(username=username).exists():
        print(f"✅ Admin '{username}' already exists!")
        return
    
    print(f"🆕 Creating admin user: {username}")
    
    password = input("Enter password for new admin: ").strip()
    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        return
    
    try:
        admin = Admin.objects.create(username=username, is_active=True)
        admin.set_password(password)
        admin.save()
        print(f"✅ Admin user '{username}' created successfully!")
        print(f"   Username: {username}")
        print(f"   Password: {password}")
        print(f"   Status: Active")
        
    except Exception as e:
        print(f"❌ Error creating admin: {e}")

def main():
    """Main function"""
    print("🔧 Admin Troubleshooting Tool")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. Check admin status")
        print("2. Create durgesh_admin")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            check_admin_status()
        elif choice == "2":
            create_admin_if_needed()
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice! Please enter 1, 2, or 3.")

if __name__ == "__main__":
    main()
