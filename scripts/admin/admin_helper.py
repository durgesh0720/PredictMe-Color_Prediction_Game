#!/usr/bin/env python3
"""
Admin Helper Script - Manage admin users and passwords
"""
import os
import django
import sys
import getpass

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Admin

def list_admins():
    """List all admin users"""
    print("🔍 Admin Users:")
    admins = Admin.objects.all()
    
    if not admins:
        print("❌ No admin users found!")
        return False
    
    for admin in admins:
        status = "✅ Active" if admin.is_active else "❌ Inactive"
        last_login = admin.last_login.strftime('%Y-%m-%d %H:%M:%S') if admin.last_login else "Never"
        print(f"  - {admin.username} | {status} | Last login: {last_login}")
    
    return True

def create_admin():
    """Create a new admin user"""
    print("\n🆕 Create New Admin User")
    
    username = input("Enter username: ").strip()
    if not username:
        print("❌ Username cannot be empty!")
        return False
    
    if Admin.objects.filter(username=username).exists():
        print(f"❌ Admin user '{username}' already exists!")
        return False
    
    password = getpass.getpass("Enter password: ")
    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        return False
    
    try:
        admin = Admin.objects.create(username=username, is_active=True)
        admin.set_password(password)
        admin.save()
        print(f"✅ Admin user '{username}' created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating admin: {e}")
        return False

def reset_password():
    """Reset admin password"""
    print("\n🔑 Reset Admin Password")
    
    username = input("Enter admin username: ").strip()
    if not username:
        print("❌ Username cannot be empty!")
        return False
    
    try:
        admin = Admin.objects.get(username=username)
    except Admin.DoesNotExist:
        print(f"❌ Admin user '{username}' not found!")
        return False
    
    password = getpass.getpass("Enter new password: ")
    if len(password) < 6:
        print("❌ Password must be at least 6 characters!")
        return False
    
    try:
        admin.set_password(password)
        admin.is_active = True
        admin.save()
        print(f"✅ Password reset for '{username}' successfully!")
        return True
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        return False

def main():
    """Main menu"""
    print("🛠️  Admin Helper Tool")
    print("=" * 50)
    
    while True:
        print("\nOptions:")
        print("1. List admin users")
        print("2. Create new admin")
        print("3. Reset admin password")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == '1':
            list_admins()
        elif choice == '2':
            create_admin()
        elif choice == '3':
            reset_password()
        elif choice == '4':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice! Please enter 1-4.")

if __name__ == '__main__':
    main()
