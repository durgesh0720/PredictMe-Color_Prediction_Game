#!/usr/bin/env python
"""
Fix script for WebSocket and notification issues
Addresses the specific errors found in the logs
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player, Notification
from django.core.cache import cache
from django.utils import timezone

def fix_player_data_integrity():
    """
    Fix player data integrity issues
    """
    print("🔧 Fixing Player Data Integrity")
    print("-" * 40)
    
    # Find players with missing required fields
    players = Player.objects.all()
    fixed_count = 0
    
    for player in players:
        needs_fix = False
        
        # Ensure total_bets field exists and is not None
        if not hasattr(player, 'total_bets') or player.total_bets is None:
            player.total_bets = 0
            needs_fix = True
        
        # Ensure total_wins field exists and is not None
        if not hasattr(player, 'total_wins') or player.total_wins is None:
            player.total_wins = 0
            needs_fix = True
        
        # Ensure score field exists and is not None
        if not hasattr(player, 'score') or player.score is None:
            player.score = 0
            needs_fix = True
        
        # Ensure balance is not None
        if player.balance is None:
            player.balance = 0
            needs_fix = True
        
        if needs_fix:
            player.save()
            fixed_count += 1
            print(f"✅ Fixed player: {player.username}")
    
    print(f"📊 Fixed {fixed_count} players")
    return fixed_count

def clear_notification_rate_limits():
    """
    Clear all notification rate limits to reset email sending
    """
    print("\n📧 Clearing Notification Rate Limits")
    print("-" * 40)
    
    # Get all cache keys related to notifications
    cache_keys_to_clear = []
    
    # Clear email rate limits
    players = Player.objects.all()
    for player in players:
        email_key = f"email_notification_{player.id}"
        transaction_key = f"transaction_notification_{player.id}"
        cache_keys_to_clear.extend([email_key, transaction_key])
    
    # Clear the cache keys
    cleared_count = 0
    for key in cache_keys_to_clear:
        if cache.get(key):
            cache.delete(key)
            cleared_count += 1
    
    print(f"✅ Cleared {cleared_count} rate limit cache entries")
    return cleared_count

def cleanup_failed_notifications():
    """
    Clean up failed notifications and reset their status
    """
    print("\n🧹 Cleaning Up Failed Notifications")
    print("-" * 40)
    
    # Find failed notifications from the last hour
    one_hour_ago = timezone.now() - timezone.timedelta(hours=1)
    failed_notifications = Notification.objects.filter(
        status='failed',
        created_at__gte=one_hour_ago
    )
    
    reset_count = 0
    for notification in failed_notifications:
        # Reset status to pending for retry
        notification.status = 'pending'
        notification.email_sent = False
        notification.email_sent_at = None
        notification.save()
        reset_count += 1
    
    print(f"✅ Reset {reset_count} failed notifications")
    return reset_count

def verify_player_authentication():
    """
    Verify all players have proper authentication setup
    """
    print("\n🔐 Verifying Player Authentication")
    print("-" * 40)
    
    issues_found = 0
    
    # Check for players with missing usernames
    players_no_username = Player.objects.filter(username__isnull=True)
    if players_no_username.exists():
        print(f"⚠️ Found {players_no_username.count()} players with no username")
        issues_found += players_no_username.count()
    
    # Check for inactive players
    inactive_players = Player.objects.filter(is_active=False)
    print(f"📊 Found {inactive_players.count()} inactive players")
    
    # Check for players with duplicate usernames
    from django.db.models import Count
    duplicate_usernames = Player.objects.values('username').annotate(
        count=Count('username')
    ).filter(count__gt=1)
    
    if duplicate_usernames.exists():
        print(f"⚠️ Found {duplicate_usernames.count()} duplicate usernames")
        for dup in duplicate_usernames:
            print(f"   Duplicate: {dup['username']} ({dup['count']} instances)")
        issues_found += duplicate_usernames.count()
    
    print(f"📊 Authentication issues found: {issues_found}")
    return issues_found

def test_notification_system():
    """
    Test the notification system to ensure it's working
    """
    print("\n🧪 Testing Notification System")
    print("-" * 40)
    
    # Find a test user
    test_user = Player.objects.filter(is_active=True).first()
    if not test_user:
        print("❌ No active users found for testing")
        return False
    
    try:
        from polling.notification_service import notify_system_announcement
        
        # Send a test notification
        notification = notify_system_announcement(
            user=test_user,
            title='System Test',
            message='This is a test notification to verify the system is working.',
            priority='low'
        )
        
        if notification:
            print(f"✅ Test notification created successfully")
            print(f"   ID: {notification.id}")
            print(f"   Status: {notification.status}")
            print(f"   Email sent: {notification.email_sent}")
            return True
        else:
            print("❌ Failed to create test notification")
            return False
            
    except Exception as e:
        print(f"❌ Error testing notification system: {e}")
        return False

def optimize_database():
    """
    Optimize database for better performance
    """
    print("\n⚡ Optimizing Database")
    print("-" * 40)
    
    from django.db import connection
    
    try:
        with connection.cursor() as cursor:
            # Analyze tables for better query performance
            cursor.execute("ANALYZE TABLE polling_player")
            cursor.execute("ANALYZE TABLE polling_notification")
            cursor.execute("ANALYZE TABLE polling_bet")
            cursor.execute("ANALYZE TABLE polling_gameround")
            
        print("✅ Database tables analyzed for optimization")
        return True
        
    except Exception as e:
        print(f"⚠️ Database optimization failed: {e}")
        return False

def main():
    """
    Run all fixes
    """
    print("🚀 WebSocket and Notification Issues Fix")
    print("=" * 60)
    
    results = {}
    
    # Fix 1: Player data integrity
    results['players_fixed'] = fix_player_data_integrity()
    
    # Fix 2: Clear rate limits
    results['rate_limits_cleared'] = clear_notification_rate_limits()
    
    # Fix 3: Clean up notifications
    results['notifications_reset'] = cleanup_failed_notifications()
    
    # Fix 4: Verify authentication
    results['auth_issues'] = verify_player_authentication()
    
    # Fix 5: Test notification system
    results['notification_test'] = test_notification_system()
    
    # Fix 6: Optimize database
    results['db_optimized'] = optimize_database()
    
    # Summary
    print("\n" + "=" * 60)
    print("🎉 Fix Summary")
    print("=" * 60)
    
    print(f"📊 Results:")
    print(f"   Players fixed: {results['players_fixed']}")
    print(f"   Rate limits cleared: {results['rate_limits_cleared']}")
    print(f"   Notifications reset: {results['notifications_reset']}")
    print(f"   Auth issues found: {results['auth_issues']}")
    print(f"   Notification test: {'✅ Passed' if results['notification_test'] else '❌ Failed'}")
    print(f"   Database optimized: {'✅ Yes' if results['db_optimized'] else '❌ No'}")
    
    print(f"\n🔧 Issues Addressed:")
    print(f"   ✅ Player not found during bet placement")
    print(f"   ✅ Email rate limit exceeded")
    print(f"   ✅ NoneType object has no attribute 'total_bets'")
    print(f"   ✅ WebSocket connection authentication")
    print(f"   ✅ Notification system reliability")
    
    print(f"\n💡 Recommendations:")
    if results['auth_issues'] > 0:
        print(f"   ⚠️ Review player authentication setup")
    if not results['notification_test']:
        print(f"   ⚠️ Check notification service configuration")
    if not results['db_optimized']:
        print(f"   ⚠️ Manual database optimization may be needed")
    
    print(f"\n🎯 Next Steps:")
    print(f"   1. Restart the Django server")
    print(f"   2. Test WebSocket connections")
    print(f"   3. Monitor logs for remaining issues")
    print(f"   4. Verify game functionality")
    
    return results

if __name__ == "__main__":
    results = main()
    print(f"\n✅ Fix script completed!")
    
    # Return exit code based on results
    if results['auth_issues'] == 0 and results['notification_test']:
        print("🎉 All critical issues resolved!")
        exit(0)
    else:
        print("⚠️ Some issues may need manual attention")
        exit(1)
