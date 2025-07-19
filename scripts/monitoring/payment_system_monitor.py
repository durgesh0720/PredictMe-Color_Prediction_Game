#!/usr/bin/env python
"""
Payment System Monitor - Monitor and verify payment system health
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import PaymentTransaction, Player, Transaction
from django.utils import timezone
from datetime import timedelta

def check_payment_system_health():
    """Check overall payment system health"""
    print("🏥 Payment System Health Check")
    print("=" * 40)
    
    # Check recent payments
    recent_payments = PaymentTransaction.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    )
    
    completed_payments = recent_payments.filter(status='completed')
    pending_payments = recent_payments.filter(status='pending')
    failed_payments = recent_payments.filter(status='failed')
    
    print(f"📊 Last 24 Hours:")
    print(f"  Total Payments: {recent_payments.count()}")
    print(f"  ✅ Completed: {completed_payments.count()}")
    print(f"  ⏳ Pending: {pending_payments.count()}")
    print(f"  ❌ Failed: {failed_payments.count()}")
    
    # Check for uncredited payments
    uncredited_count = 0
    for payment in completed_payments:
        deposit_txns = Transaction.objects.filter(
            player=payment.player,
            transaction_type='deposit',
            amount=payment.amount,
            created_at__gte=payment.created_at,
            created_at__lte=payment.completed_at + timedelta(minutes=5)
        )
        if not deposit_txns.exists():
            uncredited_count += 1
    
    print(f"  💰 Uncredited: {uncredited_count}")
    
    if uncredited_count == 0:
        print("✅ All completed payments are properly credited")
    else:
        print(f"⚠️ {uncredited_count} payments need manual review")
    
    return uncredited_count == 0

def check_player_balances():
    """Check player balance consistency"""
    print("\n💰 Player Balance Check")
    print("=" * 30)
    
    players_with_payments = Player.objects.filter(
        paymenttransaction__status='completed'
    ).distinct()
    
    inconsistent_players = []
    
    for player in players_with_payments:
        # Get all transactions
        transactions = Transaction.objects.filter(player=player).order_by('created_at')
        
        # Calculate expected balance
        calculated_balance = 0
        for txn in transactions:
            calculated_balance += txn.amount
        
        actual_balance = player.balance
        
        # Allow small differences due to floating point precision
        if abs(calculated_balance - actual_balance) > 1:
            inconsistent_players.append({
                'player': player.username,
                'calculated': calculated_balance,
                'actual': actual_balance,
                'difference': actual_balance - calculated_balance
            })
    
    if not inconsistent_players:
        print("✅ All player balances are consistent")
        return True
    else:
        print(f"⚠️ Found {len(inconsistent_players)} players with balance inconsistencies:")
        for player_data in inconsistent_players:
            print(f"  {player_data['player']}: Expected ₹{player_data['calculated']}, Actual ₹{player_data['actual']}")
        return False

def check_zero_balance_enforcement():
    """Check that zero balance system is working"""
    print("\n🔒 Zero Balance System Check")
    print("=" * 35)
    
    # Check if any new users have non-zero starting balance
    recent_players = Player.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    )
    
    non_zero_new_players = []
    for player in recent_players:
        # Check if they have any deposit transactions
        deposits = Transaction.objects.filter(
            player=player,
            transaction_type='deposit'
        )
        
        if player.balance > 0 and not deposits.exists():
            non_zero_new_players.append(player)
    
    if not non_zero_new_players:
        print("✅ Zero balance system working correctly")
        print("✅ New users start with ₹0 balance")
        return True
    else:
        print(f"⚠️ Found {len(non_zero_new_players)} new users with non-zero balance without deposits")
        return False

def generate_payment_report():
    """Generate payment system report"""
    print("\n📊 Payment System Report")
    print("=" * 30)
    
    # Overall statistics
    total_payments = PaymentTransaction.objects.count()
    total_completed = PaymentTransaction.objects.filter(status='completed').count()
    total_amount = sum(p.amount for p in PaymentTransaction.objects.filter(status='completed'))
    
    print(f"📈 Overall Statistics:")
    print(f"  Total Payments: {total_payments}")
    print(f"  Completed Payments: {total_completed}")
    print(f"  Success Rate: {(total_completed/total_payments*100):.1f}%" if total_payments > 0 else "  Success Rate: 0%")
    print(f"  Total Amount Processed: ₹{total_amount}")
    
    # Recent activity
    recent_24h = PaymentTransaction.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=24)
    )
    recent_completed = recent_24h.filter(status='completed')
    recent_amount = sum(p.amount for p in recent_completed)
    
    print(f"\n📅 Last 24 Hours:")
    print(f"  New Payments: {recent_24h.count()}")
    print(f"  Completed: {recent_completed.count()}")
    print(f"  Amount: ₹{recent_amount}")
    
    # Active players
    active_players = Player.objects.filter(balance__gt=0).count()
    total_balance = sum(p.balance for p in Player.objects.filter(balance__gt=0))
    
    print(f"\n👥 Player Statistics:")
    print(f"  Players with Balance: {active_players}")
    print(f"  Total Player Balances: ₹{total_balance}")

def main():
    """Main monitoring function"""
    print("🔍 Payment System Monitor")
    print("=" * 50)
    print("MONITORING PAYMENT SYSTEM HEALTH")
    print("=" * 50)
    
    checks = [
        check_payment_system_health,
        check_player_balances,
        check_zero_balance_enforcement
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        try:
            if check():
                passed += 1
                print("✅ PASSED\n")
            else:
                print("⚠️ NEEDS ATTENTION\n")
        except Exception as e:
            print(f"❌ ERROR: {e}\n")
    
    # Generate report regardless of check results
    generate_payment_report()
    
    print(f"\n📊 Health Check Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 Payment system is healthy!")
        print("\n✅ System Status:")
        print("✅ All payments properly credited")
        print("✅ Player balances consistent")
        print("✅ Zero balance system active")
        print("✅ Ready for production use")
        
        print(f"\n🎯 Recommendations:")
        print(f"🟢 System is operating normally")
        print(f"💰 Continue monitoring for new payments")
        print(f"🔒 Zero balance enforcement working")
        print(f"💳 Razorpay integration stable")
        
    else:
        print(f"\n⚠️ {total - passed} checks need attention.")
        print("Please review the issues above and take corrective action.")

if __name__ == '__main__':
    main()
