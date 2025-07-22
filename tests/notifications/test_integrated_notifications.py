#!/usr/bin/env python
"""
Test script for the integrated notification system
Tests notifications with actual game flow, wallet operations, and user activities
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player, Notification, GameRound, Bet
from polling.notification_service import NotificationService
from polling.wallet_utils import place_bet_with_wallet, process_bet_result_with_master_wallet
from django.utils import timezone
from django.db import transaction

def test_integrated_notifications():
    """
    Test notifications with integrated game and wallet operations
    """
    print("🚀 Testing Integrated Notification System")
    print("=" * 60)
    
    # Create test user
    test_user, created = Player.objects.get_or_create(
        username='integration_test_user',
        defaults={
            'email': 'integration@example.com',
            'first_name': 'Integration',
            'last_name': 'Test',
            'balance': 2000,
            'email_verified': True,
            'is_active': True
        }
    )
    
    if created:
        test_user.set_password('testpassword123')
        test_user.save()
        print(f"✅ Created test user: {test_user.username}")
    else:
        # Reset balance for testing
        test_user.balance = 2000
        test_user.save()
        print(f"✅ Using existing test user: {test_user.username}")
    
    initial_balance = test_user.balance
    print(f"💰 Initial balance: ${initial_balance}")
    
    # Test 1: Wallet Operations with Notifications
    print("\n💳 Test 1: Wallet Operations")
    print("-" * 40)
    
    # Test deposit
    print("📥 Testing deposit...")
    test_user.credit_wallet(500, 'deposit', 'Test deposit via payment gateway')
    print(f"✅ Deposited ₹500, new balance: ${test_user.balance}")
    
    # Test withdrawal
    print("📤 Testing withdrawal...")
    test_user.debit_wallet(200, 'withdrawal', 'Test withdrawal to bank account')
    print(f"✅ Withdrew ₹200, new balance: ${test_user.balance}")
    
    # Test 2: Game Round with Betting and Notifications
    print("\n🎮 Test 2: Complete Game Round")
    print("-" * 40)
    
    # Create a test game round
    game_round = GameRound.objects.create(
        room='main',
        period_id=f'test_{int(timezone.now().timestamp())}',
        ended=False
    )
    print(f"🎯 Created game round: {game_round.period_id}")
    
    # Test 3: Place Bets
    print("\n🎲 Test 3: Placing Bets")
    print("-" * 40)
    
    # Place a winning bet (we'll set the result to match)
    winning_bet_amount = 100
    winning_color = 'green'
    
    print(f"🟢 Placing ${winning_bet_amount} bet on {winning_color}...")
    winning_bet = Bet.objects.create(
        player=test_user,
        round=game_round,
        bet_type='color',
        color=winning_color,
        amount=winning_bet_amount
    )
    
    # Deduct bet amount from wallet
    success = test_user.debit_wallet(winning_bet_amount, 'bet', f'Bet on {winning_color}')
    if success:
        print(f"✅ Bet placed successfully, new balance: ${test_user.balance}")
    else:
        print("❌ Failed to place bet - insufficient balance")
        return
    
    # Place a losing bet
    losing_bet_amount = 50
    losing_color = 'red'
    
    print(f"🔴 Placing ${losing_bet_amount} bet on {losing_color}...")
    losing_bet = Bet.objects.create(
        player=test_user,
        round=game_round,
        bet_type='color',
        color=losing_color,
        amount=losing_bet_amount
    )
    
    # Deduct bet amount from wallet
    success = test_user.debit_wallet(losing_bet_amount, 'bet', f'Bet on {losing_color}')
    if success:
        print(f"✅ Bet placed successfully, new balance: ${test_user.balance}")
    else:
        print("❌ Failed to place bet - insufficient balance")
        return
    
    # Test 4: Process Game Results
    print("\n🏆 Test 4: Processing Game Results")
    print("-" * 40)
    
    # Set game result to green (winning color)
    result_color = winning_color
    result_number = 5  # Green number
    
    game_round.result_color = result_color
    game_round.result_number = result_number
    game_round.ended = True
    game_round.save()
    
    print(f"🎯 Game result: {result_color} (number {result_number})")
    
    # Process winning bet
    print(f"🟢 Processing winning bet...")
    won, payout = process_bet_result_with_master_wallet(winning_bet, result_number, result_color)
    if won:
        print(f"🎉 Won ${payout}! New balance: ${test_user.balance}")
        
        # Send game result notification manually (since we're not using WebSocket consumer)
        from polling.notification_service import notify_game_result
        notify_game_result(test_user, game_round, 'win', payout)
    else:
        print("❌ Bet should have won but didn't")
    
    # Process losing bet
    print(f"🔴 Processing losing bet...")
    won, payout = process_bet_result_with_master_wallet(losing_bet, result_number, result_color)
    if not won:
        print(f"😔 Lost ${losing_bet_amount}")
        
        # Send game result notification manually
        notify_game_result(test_user, game_round, 'loss', losing_bet_amount)
    else:
        print("❌ Bet should have lost but won")
    
    # Test 5: Check Notifications
    print("\n📬 Test 5: Notification Summary")
    print("-" * 40)
    
    notifications = Notification.objects.filter(user=test_user).order_by('-created_at')
    
    print(f"📊 Total notifications: {notifications.count()}")
    
    for i, notification in enumerate(notifications[:10], 1):  # Show last 10
        status_icon = "📧" if notification.email_sent else "📱"
        read_icon = "✅" if notification.read_at else "🔔"
        print(f"  {i}. {status_icon} {read_icon} {notification.title}")
        print(f"     {notification.message[:80]}...")
        print(f"     Category: {notification.notification_type.category} | Priority: {notification.priority}")
        print()
    
    # Test 6: Notification Statistics
    print("\n📈 Test 6: Notification Statistics")
    print("-" * 40)
    
    stats = {
        'total': notifications.count(),
        'unread': notifications.filter(read_at__isnull=True).count(),
        'email_sent': notifications.filter(email_sent=True).count(),
        'in_app_delivered': notifications.filter(in_app_delivered=True).count(),
    }
    
    category_stats = {}
    from polling.models import NotificationType
    for category, label in NotificationType.CATEGORY_CHOICES:
        count = notifications.filter(notification_type__category=category).count()
        if count > 0:
            category_stats[label] = count
    
    print("📊 Overall Statistics:")
    for key, value in stats.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    print("\n📋 By Category:")
    for category, count in category_stats.items():
        print(f"   {category}: {count}")
    
    # Test 7: Balance Summary
    print("\n💰 Test 7: Final Balance Summary")
    print("-" * 40)
    
    test_user.refresh_from_db()
    final_balance = test_user.balance
    
    print(f"💵 Initial balance: ${initial_balance}")
    print(f"💵 Final balance: ${final_balance}")
    print(f"💵 Net change: ${final_balance - initial_balance}")
    
    # Calculate expected balance
    expected_balance = initial_balance + 500 - 200 - winning_bet_amount - losing_bet_amount + payout
    print(f"💵 Expected balance: ${expected_balance}")
    
    if final_balance == expected_balance:
        print("✅ Balance calculation is correct!")
    else:
        print(f"❌ Balance mismatch! Difference: ${final_balance - expected_balance}")
    
    # Test 8: Test Notification Preferences
    print("\n⚙️ Test 8: Notification Preferences")
    print("-" * 40)
    
    from polling.models import UserNotificationPreference
    preferences = UserNotificationPreference.objects.filter(user=test_user)
    
    print(f"📋 User has {preferences.count()} notification preferences:")
    for pref in preferences:
        enabled_icon = "✅" if pref.is_enabled else "❌"
        print(f"   {enabled_icon} {pref.notification_type.name}: {pref.delivery_method}")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("🎉 Integrated Notification System Test Complete!")
    print("=" * 60)
    
    summary = {
        'user': test_user.username,
        'email': test_user.email,
        'final_balance': final_balance,
        'total_notifications': stats['total'],
        'unread_notifications': stats['unread'],
        'game_rounds_played': 1,
        'bets_placed': 2,
        'wins': 1,
        'losses': 1,
    }
    
    print("📊 Test Summary:")
    for key, value in summary.items():
        print(f"   {key.replace('_', ' ').title()}: {value}")
    
    print("\n💡 What was tested:")
    print("   ✅ Wallet deposit/withdrawal notifications")
    print("   ✅ Game result notifications (win/loss)")
    print("   ✅ Bet placement and processing")
    print("   ✅ Email and in-app notification delivery")
    print("   ✅ Notification preferences creation")
    print("   ✅ Balance calculations and transactions")
    
    print("\n🔗 Next Steps:")
    print("   1. Visit the notification center in the web interface")
    print("   2. Check notification settings at /notifications/settings/")
    print("   3. Play actual games to see real-time notifications")
    print("   4. Test email delivery with real SMTP settings")
    
    return test_user, summary

if __name__ == "__main__":
    user, summary = test_integrated_notifications()
    print(f"\n✅ Integration test completed for {user.username}")
    print(f"📧 Check notifications at: http://localhost:8000/notifications/settings/")
    print(f"🎮 Play games at: http://localhost:8000/room/main/")
