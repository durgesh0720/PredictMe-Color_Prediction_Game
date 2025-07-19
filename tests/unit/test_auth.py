#!/usr/bin/env python
"""
Test script for the authentication system
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player
from django.contrib.auth.hashers import check_password

def test_authentication():
    print("Testing User Authentication System")
    print("=" * 50)
    
    # Test 1: Create a new user
    print("\n1. Testing User Registration...")
    try:
        # Check if test user already exists
        if Player.objects.filter(username='testauth').exists():
            Player.objects.filter(username='testauth').delete()
            print("   Removed existing test user")
        
        # Create new user
        user = Player(
            username='testauth',
            email='testauth@example.com',
            first_name='Test',
            last_name='User',
            phone_number='+1234567890'
        )
        user.set_password('testpassword123')
        user.save()
        print("   ✓ User created successfully")
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Full Name: {user.full_name}")
        print(f"   Display Name: {user.display_name}")
        print(f"   Balance: ${user.balance}")
        
    except Exception as e:
        print(f"   ✗ Error creating user: {e}")
        return
    
    # Test 2: Test password authentication
    print("\n2. Testing Password Authentication...")
    try:
        # Test correct password
        if user.check_password('testpassword123'):
            print("   ✓ Correct password authentication works")
        else:
            print("   ✗ Correct password authentication failed")
        
        # Test incorrect password
        if not user.check_password('wrongpassword'):
            print("   ✓ Incorrect password rejection works")
        else:
            print("   ✗ Incorrect password was accepted")
            
    except Exception as e:
        print(f"   ✗ Error testing password: {e}")
    
    # Test 3: Test user lookup
    print("\n3. Testing User Lookup...")
    try:
        # Lookup by username
        found_user = Player.objects.get(username='testauth')
        print(f"   ✓ Found user by username: {found_user.username}")
        
        # Lookup by email
        found_user = Player.objects.get(email='testauth@example.com')
        print(f"   ✓ Found user by email: {found_user.email}")
        
    except Exception as e:
        print(f"   ✗ Error looking up user: {e}")
    
    # Test 4: Test profile updates
    print("\n4. Testing Profile Updates...")
    try:
        user.bio = "This is a test user for authentication testing"
        user.save()
        print("   ✓ Profile bio updated successfully")
        
        # Test last login update
        user.update_last_login()
        print("   ✓ Last login timestamp updated")
        
    except Exception as e:
        print(f"   ✗ Error updating profile: {e}")
    
    # Test 5: Display user stats
    print("\n5. User Statistics...")
    try:
        print(f"   Username: {user.username}")
        print(f"   Email: {user.email}")
        print(f"   Full Name: {user.full_name}")
        print(f"   Display Name: {user.display_name}")
        print(f"   Balance: ${user.balance}")
        print(f"   Score: {user.score}")
        print(f"   Total Bets: {user.total_bets}")
        print(f"   Total Wins: {user.total_wins}")
        print(f"   Win Rate: {user.win_rate}%")
        print(f"   Active: {user.is_active}")
        print(f"   Email Verified: {user.email_verified}")
        print(f"   Phone Verified: {user.phone_verified}")
        print(f"   Created: {user.created_at}")
        print(f"   Last Login: {user.last_login}")
        
    except Exception as e:
        print(f"   ✗ Error displaying stats: {e}")
    
    print("\n" + "=" * 50)
    print("Authentication System Test Complete!")
    
    # Cleanup
    try:
        user.delete()
        print("✓ Test user cleaned up")
    except:
        pass

if __name__ == '__main__':
    test_authentication()
