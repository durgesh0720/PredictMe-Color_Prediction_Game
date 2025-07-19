#!/usr/bin/env python3
"""
Cleanup script to ensure only one main room round is active at a time.
This script will:
1. End all existing active rounds
2. Create a single new active round for main room only
3. Clean up any non-main room data
"""

import os
import sys
import django
from datetime import timedelta

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.utils import timezone
from polling.models import GameRound, Bet, Player

def cleanup_single_room():
    """Cleanup to ensure only one main room round is active"""
    
    print("🧹 Starting single room cleanup...")
    
    # 1. End all existing active rounds
    active_rounds = GameRound.objects.filter(ended=False)
    active_count = active_rounds.count()
    
    if active_count > 0:
        print(f"📊 Found {active_count} active rounds - ending them...")
        active_rounds.update(ended=True)
        print(f"✅ Ended {active_count} active rounds")
    else:
        print("✅ No active rounds found")
    
    # 2. Clean up non-main room rounds (optional - keep for history)
    non_main_rounds = GameRound.objects.exclude(room='main')
    non_main_count = non_main_rounds.count()
    
    if non_main_count > 0:
        print(f"📊 Found {non_main_count} non-main room rounds")
        # Update them to main room instead of deleting (preserve history)
        non_main_rounds.update(room='main')
        print(f"✅ Updated {non_main_count} rounds to main room")
    
    # 3. Create a single new active round for main room
    print("🎮 Creating new active round for main room...")
    
    new_round = GameRound.objects.create(
        room='main',
        game_type='parity',
        start_time=timezone.now() - timedelta(seconds=10),  # Started 10 seconds ago
        ended=False
    )
    
    print(f"✅ Created new active round: {new_round.period_id}")
    
    # 4. Add some test bets if there are players
    players = Player.objects.filter(is_active=True)[:3]
    if players:
        print("🎯 Adding test bets...")
        colors = ['green', 'red', 'violet']
        
        for i, player in enumerate(players):
            color = colors[i % len(colors)]
            bet = Bet.objects.create(
                player=player,
                round=new_round,
                bet_type='color',
                color=color,
                amount=50
            )
            print(f"  - {player.username} bet ₹50 on {color}")
    
    # 5. Summary
    print("\n🎉 Single Room Cleanup Complete!")
    print("=" * 50)
    print(f"✅ Active rounds: 1 (main room only)")
    print(f"✅ Round ID: {new_round.period_id}")
    print(f"✅ Room: main")
    print(f"✅ Game type: parity")
    print(f"✅ Test bets: {len(players)}")
    print("=" * 50)
    
    # 6. Verification
    active_check = GameRound.objects.filter(ended=False).count()
    main_room_check = GameRound.objects.filter(ended=False, room='main').count()
    
    if active_check == 1 and main_room_check == 1:
        print("✅ Verification passed: Only 1 active round in main room")
    else:
        print(f"❌ Verification failed: {active_check} active rounds, {main_room_check} in main room")
    
    return new_round

if __name__ == "__main__":
    try:
        new_round = cleanup_single_room()
        print(f"\n🎯 Ready to play! Visit: http://127.0.0.1:8000/room/main/")
        print(f"🎯 Admin control: http://127.0.0.1:8000/control-panel/game-control-live/")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        sys.exit(1)
