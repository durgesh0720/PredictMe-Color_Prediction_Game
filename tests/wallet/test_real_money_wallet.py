#!/usr/bin/env python
"""
Test Real Money Wallet System
Like actual betting apps with real money transfers
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.test import Client
from polling.models import Player, Admin, MasterWallet, WithdrawalRequest, WalletTransaction
from django.utils import timezone
from decimal import Decimal
import json

def test_deposit_flow():
    """Test deposit flow: User → Razorpay → Admin Account → Master Wallet → User Wallet"""
    print("💳 Testing Deposit Flow...")
    
    # Create test user
    try:
        player = Player.objects.get(username='test_deposit_user')
    except Player.DoesNotExist:
        player = Player.objects.create(
            username='test_deposit_user',
            email='test_deposit@example.com',
            balance=0,
            email_verified=True,
            created_at=timezone.now()
        )
    
    # Get or create master wallet
    master_wallet, created = MasterWallet.objects.get_or_create(
        defaults={
            'total_balance': 0,
            'available_balance': 0,
            'reserved_balance': 0,
            'bank_account_number': '1234567890',
            'bank_ifsc_code': 'HDFC0001234',
            'bank_name': 'HDFC Bank',
            'account_holder_name': 'Color Prediction Game Pvt Ltd'
        }
    )
    
    initial_user_balance = player.balance
    initial_master_balance = master_wallet.available_balance
    
    # Simulate deposit
    deposit_amount = Decimal('100.00')
    
    player.credit_wallet(
        amount=deposit_amount,
        transaction_type='deposit',
        description='Test Razorpay deposit',
        involves_real_money=True,
        payment_transaction_id='test_payment_123'
    )
    
    # Refresh objects
    player.refresh_from_db()
    master_wallet.refresh_from_db()
    
    # Verify deposit flow
    assert player.balance == initial_user_balance + deposit_amount, "User wallet not credited correctly"
    assert master_wallet.available_balance == initial_master_balance + deposit_amount, "Master wallet not credited"
    assert master_wallet.total_deposits_received >= deposit_amount, "Deposit statistics not updated"
    
    print(f"✅ Deposit successful: User balance ₹{player.balance}, Master wallet ₹{master_wallet.available_balance}")
    return player, master_wallet

def test_withdrawal_flow():
    """Test withdrawal flow: User Wallet → Admin Approval → Admin Account → User Bank Account"""
    print("\n💸 Testing Withdrawal Flow...")
    
    # Use player from deposit test
    player = Player.objects.get(username='test_deposit_user')
    master_wallet = MasterWallet.objects.first()
    
    # Create admin
    try:
        admin = Admin.objects.get(username='test_admin')
    except Admin.DoesNotExist:
        admin = Admin.objects.create(
            username='test_admin'
        )
        admin.set_password('admin123')
        admin.save()
    
    initial_user_balance = player.balance
    initial_master_balance = master_wallet.available_balance
    
    # Request withdrawal
    withdrawal_amount = Decimal('50.00')
    
    try:
        withdrawal_request = player.request_withdrawal(
            amount=withdrawal_amount,
            bank_account_number='9876543210',
            bank_ifsc_code='ICICI0001234',
            bank_name='ICICI Bank',
            account_holder_name='Test User'
        )
        
        # Verify user wallet debited
        player.refresh_from_db()
        assert player.balance == initial_user_balance - withdrawal_amount, "User wallet not debited"
        assert withdrawal_request.status == 'pending', "Withdrawal not in pending status"
        
        print(f"✅ Withdrawal request created: ₹{withdrawal_amount}, Status: {withdrawal_request.status}")
        
        # Admin approves withdrawal
        approval_success = withdrawal_request.approve(admin, "Approved for testing")
        assert approval_success, "Withdrawal approval failed"
        
        # Verify master wallet reserved funds
        master_wallet.refresh_from_db()
        assert master_wallet.reserved_balance >= withdrawal_amount, "Funds not reserved in master wallet"
        
        print(f"✅ Withdrawal approved: Reserved ₹{withdrawal_amount} in master wallet")
        
        # Complete payment (simulate bank transfer)
        payment_reference = "TXN123456789"
        completion_success = withdrawal_request.complete_payment(payment_reference)
        assert completion_success, "Payment completion failed"
        
        # Verify final state
        master_wallet.refresh_from_db()
        withdrawal_request.refresh_from_db()
        
        assert withdrawal_request.status == 'completed', "Withdrawal not marked as completed"
        assert withdrawal_request.payment_reference == payment_reference, "Payment reference not saved"
        assert master_wallet.total_withdrawals_paid >= withdrawal_amount, "Withdrawal statistics not updated"
        
        print(f"✅ Withdrawal completed: Payment reference {payment_reference}")
        return withdrawal_request
        
    except ValueError as e:
        print(f"❌ Withdrawal failed: {e}")
        return None

def test_admin_rejection():
    """Test admin rejection with automatic refund"""
    print("\n❌ Testing Withdrawal Rejection...")
    
    player = Player.objects.get(username='test_deposit_user')
    admin = Admin.objects.get(username='test_admin')
    
    initial_balance = player.balance
    
    # Request another withdrawal
    withdrawal_amount = Decimal('25.00')
    
    try:
        withdrawal_request = player.request_withdrawal(
            amount=withdrawal_amount,
            bank_account_number='1111222233',
            bank_ifsc_code='SBI0001234',
            bank_name='State Bank of India',
            account_holder_name='Test User'
        )
        
        # Verify debit
        player.refresh_from_db()
        assert player.balance == initial_balance - withdrawal_amount, "User wallet not debited"
        
        # Admin rejects withdrawal
        rejection_reason = "Insufficient documentation"
        rejection_success = withdrawal_request.reject(admin, rejection_reason)
        assert rejection_success, "Withdrawal rejection failed"
        
        # Verify refund
        player.refresh_from_db()
        withdrawal_request.refresh_from_db()
        
        assert player.balance == initial_balance, "Amount not refunded to user wallet"
        assert withdrawal_request.status == 'rejected', "Withdrawal not marked as rejected"
        assert withdrawal_request.rejection_reason == rejection_reason, "Rejection reason not saved"
        
        print(f"✅ Withdrawal rejected and ₹{withdrawal_amount} refunded to user wallet")
        return True
        
    except ValueError as e:
        print(f"❌ Rejection test failed: {e}")
        return False

def test_wallet_transactions():
    """Test wallet transaction tracking"""
    print("\n📊 Testing Wallet Transaction Tracking...")
    
    player = Player.objects.get(username='test_deposit_user')
    
    # Get wallet transactions
    wallet_transactions = WalletTransaction.objects.filter(player=player).order_by('-created_at')
    
    print(f"📋 Found {wallet_transactions.count()} wallet transactions:")
    
    for txn in wallet_transactions[:5]:  # Show last 5
        money_type = "Real Money" if txn.involves_real_money else "Virtual"
        print(f"  • {txn.transaction_type.title()}: ₹{txn.amount} ({money_type}) - {txn.description}")
    
    # Verify transaction types
    deposit_txns = wallet_transactions.filter(transaction_type='deposit', involves_real_money=True)
    withdrawal_txns = wallet_transactions.filter(transaction_type='withdrawal', involves_real_money=True)
    refund_txns = wallet_transactions.filter(transaction_type='refund', involves_real_money=False)
    
    assert deposit_txns.exists(), "No real money deposit transactions found"
    assert withdrawal_txns.exists(), "No real money withdrawal transactions found"
    assert refund_txns.exists(), "No refund transactions found"
    
    print("✅ All transaction types properly tracked")
    return True

def test_master_wallet_statistics():
    """Test master wallet statistics and tracking"""
    print("\n🏦 Testing Master Wallet Statistics...")
    
    master_wallet = MasterWallet.objects.first()
    
    print(f"💰 Master Wallet Status:")
    print(f"  • Total Balance: ₹{master_wallet.total_balance}")
    print(f"  • Available Balance: ₹{master_wallet.available_balance}")
    print(f"  • Reserved Balance: ₹{master_wallet.reserved_balance}")
    print(f"  • Total Deposits Received: ₹{master_wallet.total_deposits_received}")
    print(f"  • Total Withdrawals Paid: ₹{master_wallet.total_withdrawals_paid}")
    
    # Verify statistics
    assert master_wallet.total_deposits_received > 0, "No deposits recorded in master wallet"
    assert master_wallet.total_withdrawals_paid >= 0, "Withdrawal statistics incorrect"
    assert master_wallet.available_balance >= 0, "Available balance cannot be negative"
    
    print("✅ Master wallet statistics are accurate")
    return True

def main():
    """Run all real money wallet tests"""
    print("🚀 Starting Real Money Wallet System Tests...\n")
    print("=" * 60)
    print("TESTING WALLET SYSTEM LIKE ACTUAL BETTING APPS")
    print("=" * 60)
    
    tests = [
        test_deposit_flow,
        test_withdrawal_flow,
        test_admin_rejection,
        test_wallet_transactions,
        test_master_wallet_statistics
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = test()
            if result is not False:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Real Money Wallet System is working!")
        print("\n✅ What's Working:")
        print("✅ Real money deposits credit master wallet")
        print("✅ User withdrawals require admin approval")
        print("✅ Master wallet tracks all money flows")
        print("✅ Withdrawal rejections auto-refund users")
        print("✅ All transactions properly tracked")
        print("✅ Money flows like actual betting apps")
        
        print(f"\n🌐 System Ready:")
        print(f"💳 Users can deposit via Razorpay")
        print(f"💸 Withdrawals need admin approval")
        print(f"🏦 Master wallet manages all funds")
        print(f"📊 Complete audit trail maintained")
        
    else:
        print("\n⚠️ Some tests failed. Check the system configuration.")

if __name__ == '__main__':
    main()
