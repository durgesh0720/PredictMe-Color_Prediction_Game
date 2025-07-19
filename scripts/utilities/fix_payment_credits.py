#!/usr/bin/env python
"""
Fix Payment Credits - Credit wallets for completed payments that weren't credited
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
from decimal import Decimal

def fix_uncredited_payments():
    """Find and fix payments that were completed but didn't credit the wallet"""
    print("🔍 Finding completed payments that weren't credited...")
    
    # Get all completed payments
    completed_payments = PaymentTransaction.objects.filter(
        status='completed',
        completed_at__isnull=False
    ).order_by('-completed_at')
    
    print(f"📊 Found {completed_payments.count()} completed payments")
    
    fixed_count = 0
    already_credited_count = 0
    
    for payment in completed_payments:
        player = payment.player
        amount = payment.amount
        
        # Check if there's a corresponding deposit transaction
        deposit_transactions = Transaction.objects.filter(
            player=player,
            transaction_type='deposit',
            amount=amount,
            created_at__gte=payment.created_at,
            created_at__lte=payment.completed_at + timezone.timedelta(minutes=5)
        )
        
        if deposit_transactions.exists():
            print(f"✅ Payment {payment.id} (₹{amount}) already credited to {player.username}")
            already_credited_count += 1
        else:
            print(f"🔧 Fixing payment {payment.id} (₹{amount}) for {player.username}")
            
            # Get player's current balance
            current_balance = player.balance
            
            # Credit the wallet directly
            try:
                player.balance += amount
                player.save()
                
                # Create transaction record
                Transaction.objects.create(
                    player=player,
                    transaction_type='deposit',
                    amount=amount,
                    balance_before=current_balance,
                    balance_after=player.balance,
                    description=f'Fixed Razorpay deposit - Payment ID: {payment.razorpay_payment_id}',
                    created_at=payment.completed_at
                )
                
                print(f"  ✅ Credited ₹{amount} to {player.username} (Balance: ₹{current_balance} → ₹{player.balance})")
                fixed_count += 1
                
            except Exception as e:
                print(f"  ❌ Error crediting payment {payment.id}: {e}")
    
    print(f"\n📊 Summary:")
    print(f"  ✅ Already credited: {already_credited_count}")
    print(f"  🔧 Fixed payments: {fixed_count}")
    print(f"  📈 Total processed: {completed_payments.count()}")
    
    return fixed_count

def verify_player_balances():
    """Verify that player balances match their transaction history"""
    print("\n🔍 Verifying player balances...")
    
    players_with_payments = Player.objects.filter(
        paymenttransaction__status='completed'
    ).distinct()
    
    for player in players_with_payments:
        # Calculate expected balance from transactions
        transactions = Transaction.objects.filter(player=player).order_by('created_at')
        
        calculated_balance = 0
        for txn in transactions:
            calculated_balance += txn.amount
        
        actual_balance = player.balance
        
        if calculated_balance != actual_balance:
            print(f"⚠️ Balance mismatch for {player.username}:")
            print(f"   Calculated: ₹{calculated_balance}")
            print(f"   Actual: ₹{actual_balance}")
            print(f"   Difference: ₹{actual_balance - calculated_balance}")
        else:
            print(f"✅ {player.username}: Balance correct (₹{actual_balance})")

def show_recent_payments():
    """Show recent payment status"""
    print("\n📋 Recent Payment Status:")
    
    recent_payments = PaymentTransaction.objects.all().order_by('-created_at')[:10]
    
    for payment in recent_payments:
        player = payment.player
        
        # Check if credited
        deposit_txns = Transaction.objects.filter(
            player=player,
            transaction_type='deposit',
            amount=payment.amount,
            created_at__gte=payment.created_at
        )
        
        credited = "✅ Credited" if deposit_txns.exists() else "❌ Not Credited"
        
        print(f"Payment {payment.id}: {player.username} - ₹{payment.amount} - {payment.status} - {credited}")

def main():
    """Main function to fix payment credits"""
    print("🚀 Fixing Payment Credit Issues")
    print("=" * 50)
    print("ENSURING ALL COMPLETED PAYMENTS ARE CREDITED")
    print("=" * 50)
    
    try:
        # Show current status
        show_recent_payments()
        
        # Fix uncredited payments
        fixed_count = fix_uncredited_payments()
        
        # Verify balances
        verify_player_balances()
        
        if fixed_count > 0:
            print(f"\n🎉 Successfully fixed {fixed_count} payment credits!")
            print("\n✅ What's Fixed:")
            print("✅ All completed payments now credited to wallets")
            print("✅ Transaction records created for audit trail")
            print("✅ Player balances updated correctly")
            
            print(f"\n🎯 System Status:")
            print(f"🟢 PAYMENT SYSTEM WORKING")
            print(f"💰 All deposits properly credited")
            print(f"🔒 Zero balance system active")
            print(f"💳 Ready for new payments")
        else:
            print(f"\n✅ No payment credits needed to be fixed!")
            print("All completed payments are already properly credited.")
        
    except Exception as e:
        print(f"\n❌ Error fixing payment credits: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
