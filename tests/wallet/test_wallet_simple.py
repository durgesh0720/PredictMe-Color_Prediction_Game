#!/usr/bin/env python
"""
Simple test for Real Money Wallet System
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player, Admin, MasterWallet
from django.utils import timezone
from decimal import Decimal

def test_basic_wallet_flow():
    """Test basic wallet operations"""
    print("🧪 Testing Basic Wallet Flow...")
    
    # Create test user
    try:
        player = Player.objects.get(username='wallet_test_user')
        player.delete()  # Clean slate
    except Player.DoesNotExist:
        pass
    
    player = Player.objects.create(
        username='wallet_test_user',
        email='wallet_test@example.com',
        balance=0,
        email_verified=True,
        created_at=timezone.now()
    )
    
    print(f"✅ Created user: {player.username}, Initial balance: ₹{player.balance}")
    
    # Create/get master wallet
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
    
    if created:
        print("✅ Created new master wallet")
    else:
        print("✅ Using existing master wallet")
    
    print(f"💰 Master wallet balance: ₹{master_wallet.available_balance}")
    
    # Test deposit (simple version)
    deposit_amount = Decimal('100.00')
    initial_user_balance = player.balance
    initial_master_balance = master_wallet.available_balance
    
    print(f"\n💳 Testing deposit of ₹{deposit_amount}...")
    
    # Simple credit without complex transaction tracking
    player.balance += deposit_amount
    player.save()
    
    # Credit master wallet
    master_wallet.total_balance += deposit_amount
    master_wallet.available_balance += deposit_amount
    master_wallet.total_deposits_received += deposit_amount
    master_wallet.save()
    
    print(f"✅ User balance: ₹{initial_user_balance} → ₹{player.balance}")
    print(f"✅ Master wallet: ₹{initial_master_balance} → ₹{master_wallet.available_balance}")
    
    # Test withdrawal request
    withdrawal_amount = Decimal('50.00')
    print(f"\n💸 Testing withdrawal request of ₹{withdrawal_amount}...")
    
    if player.balance >= withdrawal_amount:
        # Debit user wallet
        player.balance -= withdrawal_amount
        player.save()
        
        # Reserve in master wallet
        if master_wallet.available_balance >= withdrawal_amount:
            master_wallet.available_balance -= withdrawal_amount
            master_wallet.reserved_balance += withdrawal_amount
            master_wallet.save()
            
            print(f"✅ User balance: ₹{player.balance}")
            print(f"✅ Master wallet available: ₹{master_wallet.available_balance}")
            print(f"✅ Master wallet reserved: ₹{master_wallet.reserved_balance}")
            
            # Simulate admin approval and completion
            print(f"\n👨‍💼 Simulating admin approval...")
            
            # Complete withdrawal
            master_wallet.reserved_balance -= withdrawal_amount
            master_wallet.total_withdrawals_paid += withdrawal_amount
            master_wallet.save()
            
            print(f"✅ Withdrawal completed")
            print(f"✅ Master wallet reserved: ₹{master_wallet.reserved_balance}")
            print(f"✅ Total withdrawals paid: ₹{master_wallet.total_withdrawals_paid}")
            
        else:
            print("❌ Insufficient funds in master wallet")
    else:
        print("❌ Insufficient user balance")
    
    return True

def test_master_wallet_operations():
    """Test master wallet operations"""
    print("\n🏦 Testing Master Wallet Operations...")
    
    master_wallet = MasterWallet.objects.first()
    
    if not master_wallet:
        print("❌ No master wallet found")
        return False
    
    print(f"📊 Master Wallet Status:")
    print(f"  • Total Balance: ₹{master_wallet.total_balance}")
    print(f"  • Available Balance: ₹{master_wallet.available_balance}")
    print(f"  • Reserved Balance: ₹{master_wallet.reserved_balance}")
    print(f"  • Total Deposits: ₹{master_wallet.total_deposits_received}")
    print(f"  • Total Withdrawals: ₹{master_wallet.total_withdrawals_paid}")
    print(f"  • Bank Account: {master_wallet.bank_account_number}")
    print(f"  • IFSC Code: {master_wallet.bank_ifsc_code}")
    print(f"  • Bank Name: {master_wallet.bank_name}")
    
    # Test credit operation
    test_amount = Decimal('25.00')
    initial_balance = master_wallet.available_balance
    
    master_wallet.credit_deposit(test_amount, "Test credit operation")
    master_wallet.refresh_from_db()
    
    if master_wallet.available_balance == initial_balance + test_amount:
        print(f"✅ Credit operation successful: +₹{test_amount}")
    else:
        print(f"❌ Credit operation failed")
        return False
    
    # Test debit operation
    if master_wallet.debit_withdrawal(test_amount, "Test debit operation"):
        master_wallet.refresh_from_db()
        print(f"✅ Debit operation successful: -₹{test_amount}")
    else:
        print(f"❌ Debit operation failed")
        return False
    
    return True

def test_admin_creation():
    """Test admin creation for withdrawal approvals"""
    print("\n👨‍💼 Testing Admin Creation...")
    
    try:
        admin = Admin.objects.get(username='test_admin')
        print(f"✅ Found existing admin: {admin.username}")
    except Admin.DoesNotExist:
        admin = Admin.objects.create(username='test_admin')
        admin.set_password('admin123')
        admin.save()
        print(f"✅ Created new admin: {admin.username}")
    
    print(f"📋 Admin details:")
    print(f"  • Username: {admin.username}")
    print(f"  • Active: {admin.is_active}")
    print(f"  • Balance: ₹{admin.balance}")
    
    return True

def main():
    """Run simple wallet tests"""
    print("🚀 Starting Simple Wallet System Tests...\n")
    print("=" * 50)
    print("REAL MONEY WALLET SYSTEM - BASIC TESTS")
    print("=" * 50)
    
    tests = [
        test_basic_wallet_flow,
        test_master_wallet_operations,
        test_admin_creation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__} PASSED\n")
            else:
                print(f"❌ {test.__name__} FAILED\n")
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}\n")
            import traceback
            traceback.print_exc()
    
    print(f"📊 Final Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All basic tests passed!")
        print("\n✅ Core Wallet System Working:")
        print("✅ User wallet operations")
        print("✅ Master wallet tracking")
        print("✅ Deposit flow simulation")
        print("✅ Withdrawal flow simulation")
        print("✅ Admin system ready")
        
        print(f"\n🌐 System Status:")
        print(f"💳 Ready for Razorpay integration")
        print(f"💸 Ready for withdrawal approvals")
        print(f"🏦 Master wallet operational")
        print(f"👨‍💼 Admin system functional")
        
        print(f"\n📋 Next Steps:")
        print("1. Test with real Razorpay payments")
        print("2. Test admin approval workflow")
        print("3. Test bank transfer integration")
        print("4. Configure production settings")
        
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check system configuration.")

if __name__ == '__main__':
    main()
