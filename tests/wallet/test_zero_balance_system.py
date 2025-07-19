#!/usr/bin/env python
"""
Test Zero Balance System
Verify that users must deposit before betting
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player, GameRound
from polling.wallet_utils import validate_bet_amount, place_bet_with_wallet
from django.utils import timezone

def test_new_user_zero_balance():
    """Test that new users start with zero balance"""
    print("🧪 Testing new user zero balance...")
    
    # Create a new user
    test_username = f"zero_balance_test_{int(timezone.now().timestamp())}"
    
    player = Player.objects.create(
        username=test_username,
        email=f"{test_username}@example.com",
        email_verified=True
    )
    
    print(f"✅ Created user: {player.username}")
    print(f"💰 Initial balance: ₹{player.balance}")
    
    # Verify balance is zero
    assert player.balance == 0, f"Expected balance 0, got {player.balance}"
    print("✅ New user has zero balance")
    
    return player

def test_betting_validation_with_zero_balance():
    """Test that betting is blocked with zero balance"""
    print("\n🚫 Testing betting validation with zero balance...")
    
    player = test_new_user_zero_balance()
    
    # Test validation function
    is_valid, error_message = validate_bet_amount(100, player.balance)
    
    print(f"📋 Validation result: {is_valid}")
    print(f"📋 Error message: {error_message}")
    
    # Should be invalid
    assert not is_valid, "Betting should be blocked with zero balance"
    assert "deposit money" in error_message.lower(), "Error message should mention depositing money"
    
    print("✅ Betting correctly blocked with zero balance")
    return True

def test_betting_after_deposit():
    """Test that betting works after deposit"""
    print("\n💳 Testing betting after deposit...")
    
    player = test_new_user_zero_balance()
    
    # Simulate deposit
    deposit_amount = 100
    player.balance = deposit_amount
    player.save()
    
    print(f"💰 After deposit: ₹{player.balance}")
    
    # Test validation function
    is_valid, error_message = validate_bet_amount(50, player.balance)
    
    print(f"📋 Validation result: {is_valid}")
    print(f"📋 Error message: {error_message}")
    
    # Should be valid now
    assert is_valid, f"Betting should be allowed after deposit: {error_message}"
    
    print("✅ Betting correctly allowed after deposit")
    return True

def test_place_bet_with_zero_balance():
    """Test actual bet placement with zero balance"""
    print("\n🎲 Testing actual bet placement with zero balance...")
    
    player = test_new_user_zero_balance()
    
    # Create a test game round
    game_round = GameRound.objects.create(
        period_id=f"test_{int(timezone.now().timestamp())}",
        start_time=timezone.now(),
        end_time=timezone.now() + timezone.timedelta(seconds=50)
    )
    
    # Try to place bet with zero balance
    success, bet, error_message = place_bet_with_wallet(
        player=player,
        game_round=game_round,
        bet_type='color',
        color='red',
        number=None,
        amount=10
    )
    
    print(f"📋 Bet placement result: {success}")
    print(f"📋 Error message: {error_message}")
    
    # Should fail
    assert not success, "Bet placement should fail with zero balance"
    assert "insufficient balance" in error_message.lower(), "Error should mention insufficient balance"
    
    print("✅ Bet placement correctly blocked with zero balance")
    return True

def test_place_bet_after_deposit():
    """Test actual bet placement after deposit"""
    print("\n💰 Testing actual bet placement after deposit...")
    
    player = test_new_user_zero_balance()
    
    # Simulate deposit
    player.balance = 100
    player.save()
    
    # Create a test game round
    game_round = GameRound.objects.create(
        period_id=f"test_deposit_{int(timezone.now().timestamp())}",
        start_time=timezone.now(),
        end_time=timezone.now() + timezone.timedelta(seconds=50)
    )
    
    # Try to place bet after deposit
    success, bet, error_message = place_bet_with_wallet(
        player=player,
        game_round=game_round,
        bet_type='color',
        color='green',
        number=None,
        amount=25
    )
    
    print(f"📋 Bet placement result: {success}")
    if not success:
        print(f"📋 Error message: {error_message}")
    else:
        print(f"📋 Bet created: {bet.id}")
        print(f"💰 Player balance after bet: ₹{player.balance}")
    
    # Should succeed
    assert success, f"Bet placement should succeed after deposit: {error_message}"
    assert player.balance == 75, f"Balance should be 75 after 25 bet, got {player.balance}"
    
    print("✅ Bet placement correctly allowed after deposit")
    return True

def main():
    """Run all zero balance system tests"""
    print("🚀 Testing Zero Balance System")
    print("=" * 50)
    print("ENSURING USERS MUST DEPOSIT BEFORE BETTING")
    print("=" * 50)
    
    tests = [
        test_new_user_zero_balance,
        test_betting_validation_with_zero_balance,
        test_betting_after_deposit,
        test_place_bet_with_zero_balance,
        test_place_bet_after_deposit
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            result = test()
            if result is not False:
                passed += 1
                print(f"✅ {test.__name__} PASSED\n")
            else:
                print(f"❌ {test.__name__} FAILED\n")
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}\n")
            import traceback
            traceback.print_exc()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! Zero Balance System is working!")
        print("\n✅ What's Working:")
        print("✅ New users start with ₹0 balance")
        print("✅ Betting blocked with zero balance")
        print("✅ Clear error messages guide users to deposit")
        print("✅ Betting allowed after deposit")
        print("✅ Wallet properly debited for bets")
        
        print(f"\n🎯 System Status:")
        print(f"🟢 ZERO BALANCE SYSTEM ACTIVE")
        print(f"💰 All users must deposit to bet")
        print(f"🔒 No free money in the system")
        print(f"💳 Real money deposits required")
        
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check the system configuration.")

if __name__ == '__main__':
    main()
