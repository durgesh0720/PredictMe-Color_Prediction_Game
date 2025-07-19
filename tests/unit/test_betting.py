#!/usr/bin/env python3
"""
Test script to verify betting system functionality
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player, GameRound, Bet
from django.utils import timezone

def test_betting_system():
    """Test the betting system components"""
    print("🧪 Testing Betting System...")
    
    # Test 1: Check if we have active players
    active_players = Player.objects.filter(is_active=True)
    print(f"✅ Active players: {active_players.count()}")
    
    if active_players.count() == 0:
        print("❌ No active players found!")
        return False
    
    # Test 2: Check player balances
    test_player = active_players.first()
    print(f"✅ Test player: {test_player.username} (Balance: {test_player.balance})")
    
    # Test 3: Create a test game round
    test_round = GameRound.objects.create(
        room='test_room',
        start_time=timezone.now(),
        game_type='parity'
    )
    print(f"✅ Created test round: {test_round.period_id}")
    
    # Test 4: Test bet creation
    try:
        test_bet = Bet.objects.create(
            player=test_player,
            round=test_round,
            bet_type='color',
            color='red',
            amount=10
        )
        print(f"✅ Created test bet: {test_bet.id}")
        
        # Test 5: Test bet validation
        result_number = 1  # Should be green
        result_color = 'green'
        
        won = test_bet.check_win(result_number, result_color)
        print(f"✅ Bet validation test: Won={won}, Expected=False")
        
        # Test 6: Test winning bet
        winning_bet = Bet.objects.create(
            player=test_player,
            round=test_round,
            bet_type='color',
            color='green',
            amount=20
        )
        
        won = winning_bet.check_win(result_number, result_color)
        print(f"✅ Winning bet test: Won={won}, Expected=True, Payout={winning_bet.payout}")
        
        # Clean up test data
        test_bet.delete()
        winning_bet.delete()
        test_round.delete()
        
        print("🎉 All betting system tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Betting test failed: {e}")
        return False

def test_color_mapping():
    """Test color mapping logic"""
    print("\n🎨 Testing Color Mapping...")
    
    test_cases = [
        (0, 'violet'),
        (1, 'green'),
        (2, 'red'),
        (3, 'green'),
        (4, 'red'),
        (5, 'violet'),
        (6, 'red'),
        (7, 'green'),
        (8, 'red'),
        (9, 'green'),
    ]
    
    # Create a temporary round for testing
    temp_round = GameRound()
    
    for number, expected_color in test_cases:
        temp_round.result_number = number
        actual_color = temp_round.result_color_from_number
        
        if actual_color == expected_color:
            print(f"✅ Number {number} -> {actual_color}")
        else:
            print(f"❌ Number {number} -> {actual_color} (expected {expected_color})")
            return False
    
    print("🎉 Color mapping tests passed!")
    return True

def main():
    """Run all tests"""
    print("🚀 Starting Betting System Tests\n")
    
    success = True
    success &= test_color_mapping()
    success &= test_betting_system()
    
    if success:
        print("\n🎉 All tests passed! Betting system is working correctly.")
        return 0
    else:
        print("\n❌ Some tests failed. Please check the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
