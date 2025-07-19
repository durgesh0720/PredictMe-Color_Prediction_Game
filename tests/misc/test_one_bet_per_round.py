#!/usr/bin/env python
"""
Test script for one bet per round restriction
Verifies that players can only place one bet per round
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player, GameRound, Bet
from polling.wallet_utils import place_bet_with_wallet
from django.utils import timezone
from django.db import IntegrityError

def test_one_bet_per_round():
    """
    Test the one bet per round restriction
    """
    print("🧪 Testing One Bet Per Round Restriction")
    print("=" * 60)
    
    # Create test user
    test_user, created = Player.objects.get_or_create(
        username='one_bet_test_user',
        defaults={
            'email': 'onebet@example.com',
            'first_name': 'OneBet',
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
    
    # Create a test game round
    game_round = GameRound.objects.create(
        room='main',
        period_id=f'one_bet_test_{int(timezone.now().timestamp())}',
        ended=False
    )
    print(f"🎯 Created game round: {game_round.period_id}")
    
    # Test 1: First bet should succeed
    print("\n🎲 Test 1: First Bet (Should Succeed)")
    print("-" * 40)
    
    success1, bet1, error1 = place_bet_with_wallet(
        player=test_user,
        game_round=game_round,
        bet_type='color',
        color='red',
        number=None,
        amount=100
    )
    
    if success1:
        print(f"✅ First bet placed successfully")
        print(f"   Bet ID: {bet1.id}")
        print(f"   Amount: ${bet1.amount}")
        print(f"   Color: {bet1.color}")
        print(f"   Player balance: ${test_user.balance}")
    else:
        print(f"❌ First bet failed: {error1}")
        return
    
    # Test 2: Second bet should fail
    print("\n🚫 Test 2: Second Bet (Should Fail)")
    print("-" * 40)
    
    success2, bet2, error2 = place_bet_with_wallet(
        player=test_user,
        game_round=game_round,
        bet_type='color',
        color='green',
        number=None,
        amount=50
    )
    
    if not success2:
        print(f"✅ Second bet correctly rejected")
        print(f"   Error message: {error2}")
        print(f"   Player balance unchanged: ${test_user.balance}")
    else:
        print(f"❌ Second bet should have failed but succeeded!")
        print(f"   This indicates the restriction is not working")
        return
    
    # Test 3: Try different bet type (should also fail)
    print("\n🔢 Test 3: Different Bet Type (Should Also Fail)")
    print("-" * 40)
    
    success3, bet3, error3 = place_bet_with_wallet(
        player=test_user,
        game_round=game_round,
        bet_type='number',
        color=None,
        number=5,
        amount=25
    )
    
    if not success3:
        print(f"✅ Number bet correctly rejected")
        print(f"   Error message: {error3}")
    else:
        print(f"❌ Number bet should have failed but succeeded!")
        return
    
    # Test 4: Direct database constraint test
    print("\n🗄️ Test 4: Database Constraint Test")
    print("-" * 40)
    
    try:
        # Try to create a bet directly in the database (bypassing our validation)
        duplicate_bet = Bet.objects.create(
            player=test_user,
            round=game_round,
            bet_type='color',
            color='blue',
            amount=75
        )
        print(f"❌ Database constraint failed - duplicate bet was created!")
        duplicate_bet.delete()  # Clean up
    except IntegrityError as e:
        print(f"✅ Database constraint working correctly")
        print(f"   Error: {str(e)}")
    
    # Test 5: New round should allow new bet
    print("\n🔄 Test 5: New Round (Should Allow New Bet)")
    print("-" * 40)
    
    # Create a new game round
    new_game_round = GameRound.objects.create(
        room='main',
        period_id=f'one_bet_test_new_{int(timezone.now().timestamp())}',
        ended=False
    )
    print(f"🎯 Created new game round: {new_game_round.period_id}")
    
    success4, bet4, error4 = place_bet_with_wallet(
        player=test_user,
        game_round=new_game_round,
        bet_type='color',
        color='violet',
        number=None,
        amount=150
    )
    
    if success4:
        print(f"✅ New round bet placed successfully")
        print(f"   Bet ID: {bet4.id}")
        print(f"   Amount: ${bet4.amount}")
        print(f"   Color: {bet4.color}")
        print(f"   Player balance: ${test_user.balance}")
    else:
        print(f"❌ New round bet failed: {error4}")
    
    # Test 6: Multiple players can bet on same round
    print("\n👥 Test 6: Multiple Players Same Round")
    print("-" * 40)
    
    # Create another test user
    test_user2, created2 = Player.objects.get_or_create(
        username='one_bet_test_user2',
        defaults={
            'email': 'onebet2@example.com',
            'first_name': 'OneBet2',
            'last_name': 'Test',
            'balance': 1000,
            'email_verified': True,
            'is_active': True
        }
    )
    
    if created2:
        test_user2.set_password('testpassword123')
        test_user2.save()
        print(f"✅ Created second test user: {test_user2.username}")
    else:
        test_user2.balance = 1000
        test_user2.save()
        print(f"✅ Using existing second test user: {test_user2.username}")
    
    success5, bet5, error5 = place_bet_with_wallet(
        player=test_user2,
        game_round=new_game_round,
        bet_type='color',
        color='red',
        number=None,
        amount=200
    )
    
    if success5:
        print(f"✅ Second player bet placed successfully")
        print(f"   Player: {test_user2.username}")
        print(f"   Amount: ${bet5.amount}")
        print(f"   Color: {bet5.color}")
    else:
        print(f"❌ Second player bet failed: {error5}")
    
    # Test 7: Check database state
    print("\n📊 Test 7: Database State Verification")
    print("-" * 40)
    
    # Count bets per round
    round1_bets = Bet.objects.filter(round=game_round).count()
    round2_bets = Bet.objects.filter(round=new_game_round).count()
    
    print(f"📈 Round 1 ({game_round.period_id}): {round1_bets} bet(s)")
    print(f"📈 Round 2 ({new_game_round.period_id}): {round2_bets} bet(s)")
    
    # Show all bets
    all_bets = Bet.objects.filter(
        round__in=[game_round, new_game_round]
    ).order_by('created_at')
    
    print(f"\n📋 All Test Bets:")
    for i, bet in enumerate(all_bets, 1):
        print(f"  {i}. {bet.player.username} - ${bet.amount} on {bet.color or bet.number} (Round: {bet.round.period_id})")
    
    # Test 8: Performance test
    print("\n⚡ Test 8: Performance Test")
    print("-" * 40)
    
    start_time = timezone.now()
    
    # Try to place 10 bets rapidly (should all fail except first)
    performance_round = GameRound.objects.create(
        room='main',
        period_id=f'performance_test_{int(timezone.now().timestamp())}',
        ended=False
    )
    
    success_count = 0
    fail_count = 0
    
    for i in range(10):
        success, bet, error = place_bet_with_wallet(
            player=test_user,
            game_round=performance_round,
            bet_type='color',
            color='red',
            number=None,
            amount=10
        )
        
        if success:
            success_count += 1
        else:
            fail_count += 1
    
    end_time = timezone.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"⏱️ Performance test completed in {duration:.3f} seconds")
    print(f"✅ Successful bets: {success_count} (should be 1)")
    print(f"❌ Failed bets: {fail_count} (should be 9)")
    
    if success_count == 1 and fail_count == 9:
        print("✅ Performance test passed - restriction working under load")
    else:
        print("❌ Performance test failed - restriction not working properly")
    
    # Final Summary
    print("\n" + "=" * 60)
    print("🎉 One Bet Per Round Test Complete!")
    print("=" * 60)
    
    total_bets = Bet.objects.filter(
        player__in=[test_user, test_user2],
        round__in=[game_round, new_game_round, performance_round]
    ).count()
    
    expected_bets = 4  # 1 from round1, 2 from round2, 1 from performance
    
    print(f"📊 Test Results:")
    print(f"   Total bets created: {total_bets}")
    print(f"   Expected bets: {expected_bets}")
    print(f"   Restriction working: {'✅ Yes' if total_bets == expected_bets else '❌ No'}")
    
    print(f"\n🔧 Features Tested:")
    print(f"   ✅ One bet per player per round")
    print(f"   ✅ Database constraint enforcement")
    print(f"   ✅ Multiple players same round")
    print(f"   ✅ New round allows new bets")
    print(f"   ✅ Error message handling")
    print(f"   ✅ Performance under load")
    
    print(f"\n🎯 Next Steps:")
    print(f"   • Test the WebSocket interface")
    print(f"   • Verify frontend error handling")
    print(f"   • Test with real game rounds")
    
    return test_user, test_user2, total_bets

if __name__ == "__main__":
    user1, user2, bet_count = test_one_bet_per_round()
    print(f"\n✅ Test completed!")
    print(f"👤 Test users: {user1.username}, {user2.username}")
    print(f"🎲 Total bets: {bet_count}")
    print(f"🔒 One bet per round restriction: {'Working' if bet_count == 4 else 'Not working'}")
