#!/usr/bin/env python
"""
Script to update notification settings to use email only for OTP and password reset
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import NotificationType, UserNotificationPreference

def update_notification_settings():
    """
    Update notification types to use email only for OTP and password reset
    """
    print("🔄 Updating notification settings...")
    
    # Define which notification types should use email
    email_notification_types = [
        'password_changed',      # Password reset/change
        'security_alert',        # Security alerts
        'login_alert',           # New login alerts
        'email_verified'         # Email verification
    ]
    
    # Update all notification types
    all_types = NotificationType.objects.all()
    
    for nt in all_types:
        old_setting = nt.email_enabled
        
        # Set email_enabled based on whether it's in the allowed list
        nt.email_enabled = nt.name in email_notification_types
        nt.save()
        
        status = "✅" if nt.email_enabled else "❌"
        change = "unchanged" if old_setting == nt.email_enabled else "changed"
        print(f"{status} {nt.name}: Email {status} ({change})")
    
    # Update user preferences to match new settings
    update_user_preferences()
    
    print("\n📊 Summary:")
    print(f"  Total notification types: {all_types.count()}")
    print(f"  Email enabled types: {NotificationType.objects.filter(email_enabled=True).count()}")
    print(f"  Email disabled types: {NotificationType.objects.filter(email_enabled=False).count()}")

def update_user_preferences():
    """
    Update user preferences to match new notification type settings
    """
    print("\n🔄 Updating user preferences...")
    
    # Get all notification types
    notification_types = NotificationType.objects.all()
    
    # For each notification type
    for nt in notification_types:
        # Get all user preferences for this notification type
        preferences = UserNotificationPreference.objects.filter(notification_type=nt)
        
        # If email is disabled for this notification type, update preferences
        if not nt.email_enabled:
            for pref in preferences:
                if pref.delivery_method == 'email':
                    pref.delivery_method = 'in_app'
                    pref.save()
                    print(f"  Updated {pref.user.username}'s preference for {nt.name}: email → in_app")
                elif pref.delivery_method == 'both':
                    pref.delivery_method = 'in_app'
                    pref.save()
                    print(f"  Updated {pref.user.username}'s preference for {nt.name}: both → in_app")

def display_current_settings():
    """
    Display current notification settings
    """
    print("\n📋 Current Notification Settings:")
    
    # Display all notification types by category
    for category, label in NotificationType.CATEGORY_CHOICES:
        types = NotificationType.objects.filter(category=category, is_active=True)
        if types.exists():
            print(f"\n{label}:")
            for nt in types:
                status = "✅" if nt.default_enabled else "⚪"
                email = "📧" if nt.email_enabled else "❌"
                app = "📱" if nt.in_app_enabled else "❌"
                print(f"  {status} {nt.name} - {email} {app}")

if __name__ == "__main__":
    print("🚀 Updating notification settings to use email only for OTP and password reset...")
    update_notification_settings()
    display_current_settings()
    print("\n✅ Done!")
