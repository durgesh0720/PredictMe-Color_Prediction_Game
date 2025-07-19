#!/usr/bin/env python
"""
Script to populate notification types in the database
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import NotificationType

def populate_notification_types():
    """
    Create default notification types
    """
    notification_types = [
        # Game Events
        {
            'name': 'game_result',
            'category': 'game',
            'description': 'Notifications about game results (wins/losses)',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        {
            'name': 'game_round_start',
            'category': 'game',
            'description': 'Notifications when new game rounds start',
            'is_active': True,
            'default_enabled': False,  # Disabled by default to avoid spam
            'email_enabled': False,
            'in_app_enabled': True,
        },
        {
            'name': 'big_win',
            'category': 'game',
            'description': 'Notifications for significant wins',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        
        # Wallet & Transactions
        {
            'name': 'wallet_transaction',
            'category': 'wallet',
            'description': 'Notifications for wallet deposits and withdrawals',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        {
            'name': 'low_balance',
            'category': 'wallet',
            'description': 'Notifications when wallet balance is low',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': False,
            'in_app_enabled': True,
        },
        {
            'name': 'payment_failed',
            'category': 'wallet',
            'description': 'Notifications for failed payment attempts',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        
        # Account Activities
        {
            'name': 'account_activity',
            'category': 'account',
            'description': 'Notifications for account-related activities',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        {
            'name': 'profile_updated',
            'category': 'account',
            'description': 'Notifications when profile is updated',
            'is_active': True,
            'default_enabled': False,
            'email_enabled': False,
            'in_app_enabled': True,
        },
        {
            'name': 'email_verified',
            'category': 'account',
            'description': 'Notifications when email is verified',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        
        # System Announcements
        {
            'name': 'system_announcement',
            'category': 'system',
            'description': 'Important system announcements and updates',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        {
            'name': 'maintenance_notice',
            'category': 'system',
            'description': 'Notifications about scheduled maintenance',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        {
            'name': 'new_features',
            'category': 'system',
            'description': 'Notifications about new features and updates',
            'is_active': True,
            'default_enabled': False,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        
        # Security Alerts
        {
            'name': 'security_alert',
            'category': 'security',
            'description': 'Security-related alerts and warnings',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        {
            'name': 'login_alert',
            'category': 'security',
            'description': 'Notifications for new device logins',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
        {
            'name': 'password_changed',
            'category': 'security',
            'description': 'Notifications when password is changed',
            'is_active': True,
            'default_enabled': True,
            'email_enabled': True,
            'in_app_enabled': True,
        },
    ]
    
    created_count = 0
    updated_count = 0
    
    for nt_data in notification_types:
        notification_type, created = NotificationType.objects.get_or_create(
            name=nt_data['name'],
            defaults=nt_data
        )
        
        if created:
            created_count += 1
            print(f"✅ Created notification type: {notification_type.name}")
        else:
            # Update existing notification type
            for key, value in nt_data.items():
                if key != 'name':  # Don't update the name
                    setattr(notification_type, key, value)
            notification_type.save()
            updated_count += 1
            print(f"🔄 Updated notification type: {notification_type.name}")
    
    print(f"\n📊 Summary:")
    print(f"   Created: {created_count} notification types")
    print(f"   Updated: {updated_count} notification types")
    print(f"   Total: {NotificationType.objects.count()} notification types in database")
    
    # Display all notification types by category
    print(f"\n📋 All Notification Types:")
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
    print("🚀 Populating notification types...")
    populate_notification_types()
    print("✅ Done!")
