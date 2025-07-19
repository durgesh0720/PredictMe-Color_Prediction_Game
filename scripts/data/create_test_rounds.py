#!/usr/bin/env python
"""
Script to create test game rounds for admin control testing.
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import GameRound, Player, Bet
from django.utils import timezone

def create_test_data():
    """Create test game rounds and bets for admin control testing"""
    
    print("Creating test game rounds...")
    
    # Create some test players
    players = []
    for i in range(5):
        player, created = Player.objects.get_or_create(
            username=f"testuser{i+1}",
            defaults={'balance': 1000}
        )
        players.append(player)
        if created:
            print(f"Created test player: {player.username}")
    
    # Create only one active round for main room
    # End any existing active rounds first
    GameRound.objects.filter(ended=False).update(ended=True)

    # Create single active round for main room only
    round_obj = GameRound.objects.create(
        room='main',  # Only main room
        game_type='parity',  # Default game type
        start_time=timezone.now() - timedelta(seconds=35),  # Started 35 seconds ago (in selection window)
        ended=False
    )

    print(f"Created active round for main room: {round_obj.period_id}")

    # Add some test bets to this round
    colors = ['green', 'red', 'violet']
    for i, player in enumerate(players):
        # Each player bets on a different color
        color = colors[i % len(colors)]
        bet = Bet.objects.create(
            player=player,
            round=round_obj,
            bet_type='color',
            color=color,
            amount=50
        )
        print(f"  - {player.username} bet ₹50 on {color}")
    
    print("\n" + "="*50)
    print("🎮 TEST DATA CREATED!")
    print("="*50)
    print("✅ Created active game rounds for all game types")
    print("✅ Created test players with bets")
    print("\n📋 What to test:")
    print("1. Go to Live Control: http://localhost:8000/admin/game-control-live/")
    print("2. You should see active rounds with betting statistics")
    print("3. Click on color buttons to select winning colors")
    print("4. If you don't select, system will auto-select minimum bet color")
    print("5. Watch real-time updates and notifications")
    print("\n🔧 Betting Statistics:")
    
    # Show betting statistics
    for game_type in game_types:
        round_obj = GameRound.objects.filter(game_type=game_type, ended=False).first()
        if round_obj:
            bets = Bet.objects.filter(round=round_obj, bet_type='color')
            color_counts = {'green': 0, 'red': 0, 'violet': 0}
            for bet in bets:
                if bet.color in color_counts:
                    color_counts[bet.color] += 1
            
            min_color = min(color_counts.items(), key=lambda x: x[1])[0]
            print(f"{game_type.upper()}: Green={color_counts['green']}, Red={color_counts['red']}, Violet={color_counts['violet']} | Min: {min_color}")
    
    print("="*50)

if __name__ == "__main__":
    create_test_data()
