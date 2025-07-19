#!/usr/bin/env python
"""
Test script for the comprehensive notification system
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player, Notification, NotificationType, UserNotificationPreference
from polling.notification_service import (
    NotificationService, notify_game_result, notify_wallet_transaction, 
    notify_account_activity, notify_system_announcement, notify_security_alert
)
from django.utils import timezone

def test_notification_system():
    """
    Test the complete notification system
    """
    print("🧪 Testing Comprehensive Notification System")
    print("=" * 60)
    
    # Get or create a test user
    test_user, created = Player.objects.get_or_create(
        username='notification_test_user',
        defaults={
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'balance': 1000,
            'email_verified': True,
            'is_active': True
        }
    )
    
    if created:
        test_user.set_password('testpassword123')
        test_user.save()
        print(f"✅ Created test user: {test_user.username}")
    else:
        print(f"✅ Using existing test user: {test_user.username}")
    
    # Test 1: Basic notification creation
    print("\n📝 Test 1: Basic Notification Creation")
    print("-" * 40)
    
    service = NotificationService()
    notification = service.create_notification(
        user=test_user,
        notification_type_name='game_result',
        title='Test Game Result',
        message='This is a test notification for game results.',
        priority='normal'
    )
    
    if notification:
        print(f"✅ Created notification: {notification.title}")
        print(f"   ID: {notification.id}")
        print(f"   Status: {notification.status}")
        print(f"   Email sent: {notification.email_sent}")
        print(f"   In-app delivered: {notification.in_app_delivered}")
    else:
        print("❌ Failed to create notification")
    
    # Test 2: Game result notifications
    print("\n🎮 Test 2: Game Result Notifications")
    print("-" * 40)
    
    # Create a mock game round object
    class MockGameRound:
        def __init__(self):
            self.id = 12345
            self.result_color = 'green'
    
    game_round = MockGameRound()
    
    # Test win notification
    win_notification = notify_game_result(test_user, game_round, 'win', 500)
    if win_notification:
        print(f"✅ Win notification: {win_notification.title}")
    
    # Test loss notification
    loss_notification = notify_game_result(test_user, game_round, 'loss', 100)
    if loss_notification:
        print(f"✅ Loss notification: {loss_notification.title}")
    
    # Test 3: Wallet transaction notifications
    print("\n💰 Test 3: Wallet Transaction Notifications")
    print("-" * 40)
    
    deposit_notification = notify_wallet_transaction(test_user, 'deposit', 250, 1250)
    if deposit_notification:
        print(f"✅ Deposit notification: {deposit_notification.title}")
    
    withdrawal_notification = notify_wallet_transaction(test_user, 'withdrawal', 100, 1150)
    if withdrawal_notification:
        print(f"✅ Withdrawal notification: {withdrawal_notification.title}")
    
    # Test 4: Account activity notifications
    print("\n👤 Test 4: Account Activity Notifications")
    print("-" * 40)
    
    login_notification = notify_account_activity(
        test_user, 
        'login', 
        'You logged in from a new device on Chrome browser.'
    )
    if login_notification:
        print(f"✅ Login notification: {login_notification.title}")
    
    email_verified_notification = notify_account_activity(
        test_user,
        'email_verified',
        'Your email address has been successfully verified.'
    )
    if email_verified_notification:
        print(f"✅ Email verified notification: {email_verified_notification.title}")
    
    # Test 5: System announcements
    print("\n📢 Test 5: System Announcements")
    print("-" * 40)
    
    announcement_notification = notify_system_announcement(
        test_user,
        'New Color Added!',
        'We\'ve added a new color option - Blue! Try your luck with the new betting option.',
        'normal'
    )
    if announcement_notification:
        print(f"✅ Announcement notification: {announcement_notification.title}")
    
    # Test 6: Security alerts
    print("\n🔒 Test 6: Security Alerts")
    print("-" * 40)
    
    security_notification = notify_security_alert(
        test_user,
        'suspicious_login',
        'We detected a login attempt from an unusual location. If this wasn\'t you, please change your password immediately.'
    )
    if security_notification:
        print(f"✅ Security alert: {security_notification.title}")
    
    # Test 7: User preferences
    print("\n⚙️ Test 7: User Notification Preferences")
    print("-" * 40)
    
    # Check user preferences
    preferences = UserNotificationPreference.objects.filter(user=test_user)
    print(f"📊 User has {preferences.count()} notification preferences")
    
    for pref in preferences[:5]:  # Show first 5
        print(f"   {pref.notification_type.name}: {pref.delivery_method} ({'enabled' if pref.is_enabled else 'disabled'})")
    
    # Test 8: Notification statistics
    print("\n📊 Test 8: Notification Statistics")
    print("-" * 40)
    
    total_notifications = Notification.objects.filter(user=test_user).count()
    unread_notifications = Notification.objects.filter(user=test_user, read_at__isnull=True).count()
    email_sent_count = Notification.objects.filter(user=test_user, email_sent=True).count()
    in_app_delivered_count = Notification.objects.filter(user=test_user, in_app_delivered=True).count()
    
    print(f"📈 Total notifications: {total_notifications}")
    print(f"📬 Unread notifications: {unread_notifications}")
    print(f"📧 Email notifications sent: {email_sent_count}")
    print(f"📱 In-app notifications delivered: {in_app_delivered_count}")
    
    # Test 9: Notification categories breakdown
    print("\n📋 Test 9: Notifications by Category")
    print("-" * 40)
    
    for category, label in NotificationType.CATEGORY_CHOICES:
        count = Notification.objects.filter(
            user=test_user,
            notification_type__category=category
        ).count()
        if count > 0:
            print(f"   {label}: {count} notifications")
    
    # Test 10: Mark notifications as read
    print("\n✅ Test 10: Mark Notifications as Read")
    print("-" * 40)
    
    # Mark first notification as read
    first_notification = Notification.objects.filter(user=test_user, read_at__isnull=True).first()
    if first_notification:
        first_notification.mark_as_read()
        print(f"✅ Marked notification as read: {first_notification.title}")
        print(f"   Read at: {first_notification.read_at}")
    
    # Test 11: Expired notifications
    print("\n⏰ Test 11: Expired Notifications")
    print("-" * 40)
    
    # Create a notification that expires in the past
    expired_notification = service.create_notification(
        user=test_user,
        notification_type_name='system_announcement',
        title='Expired Test Notification',
        message='This notification should be expired.',
        expires_in_hours=-1  # Expired 1 hour ago
    )
    
    if expired_notification:
        print(f"✅ Created expired notification: {expired_notification.title}")
        print(f"   Is expired: {expired_notification.is_expired()}")
        print(f"   Expires at: {expired_notification.expires_at}")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 Notification System Test Complete!")
    print("=" * 60)
    
    final_stats = {
        'total_notifications': Notification.objects.filter(user=test_user).count(),
        'unread_count': Notification.objects.filter(user=test_user, read_at__isnull=True).count(),
        'email_sent': Notification.objects.filter(user=test_user, email_sent=True).count(),
        'in_app_delivered': Notification.objects.filter(user=test_user, in_app_delivered=True).count(),
        'preferences_count': UserNotificationPreference.objects.filter(user=test_user).count(),
    }
    
    print(f"📊 Final Statistics for {test_user.username}:")
    for key, value in final_stats.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    print("\n💡 Next Steps:")
    print("   1. Check the Django admin to see created notifications")
    print("   2. Visit /notifications/settings/ to manage preferences")
    print("   3. Test the in-app notification center")
    print("   4. Check email delivery (if SMTP is configured)")
    
    return test_user, final_stats

if __name__ == "__main__":
    test_user, stats = test_notification_system()
    print(f"\n✅ Test completed for user: {test_user.username}")
    print(f"📧 Email: {test_user.email}")
    print(f"🔔 Total notifications created: {stats['total_notifications']}")
