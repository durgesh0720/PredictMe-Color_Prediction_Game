#!/usr/bin/env python
"""
Test script for admin login functionality
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Admin

def test_admin_login():
    print("Testing Admin Login System")
    print("=" * 40)
    
    # Check if admin user exists
    try:
        admin = Admin.objects.get(username='admin')
        print(f"✓ Admin user found: {admin.username}")
        print(f"  Active: {admin.is_active}")
        print(f"  Created: {admin.created_at}")
        print(f"  Last Login: {admin.last_login}")
        
        # Test password check
        if admin.check_password('admin123'):
            print("✓ Default password 'admin123' works")
        else:
            print("✗ Default password 'admin123' doesn't work")
            print("  Try creating a new admin with: python create_admin.py")
            
    except Admin.DoesNotExist:
        print("✗ No admin user found")
        print("  Create an admin user with: python create_admin.py")
        return
    
    print("\n" + "=" * 40)
    print("Admin Login Test Complete!")
    print("\nTo test the login page:")
    print("1. Go to: http://127.0.0.1:8000/control-panel/")
    print("2. Username: admin")
    print("3. Password: admin123")

if __name__ == '__main__':
    test_admin_login()
