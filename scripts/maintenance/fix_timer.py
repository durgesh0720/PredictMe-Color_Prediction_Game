#!/usr/bin/env python3
"""
Fix script to restart the timer for current game rounds
"""
import os
import django
import asyncio
import time

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.timer_sync import server_timer
from polling.models import GameRound
from channels.db import database_sync_to_async

@database_sync_to_async
def get_active_rounds():
    """Get active rounds from database"""
    return list(GameRound.objects.filter(ended=False))

async def fix_timer():
    """Fix the timer system by restarting timers for active rounds"""
    print("🔧 Fixing Timer System...")
    
    # Ensure timer management is running
    server_timer.ensure_timer_management_started()
    print("✅ Timer management started")
    
    # Get active rounds
    active_rounds = await get_active_rounds()
    print(f"Found {len(active_rounds)} active rounds")
    
    for round_obj in active_rounds:
        print(f"\n🎮 Processing round {round_obj.period_id} in room {round_obj.room}")
        
        # Check if round has expired
        current_time = time.time()
        db_start_time = round_obj.start_time.timestamp()
        elapsed_time = current_time - db_start_time
        
        print(f"  Elapsed time: {elapsed_time:.1f}s")
        
        if elapsed_time >= 50:  # Round duration is 50 seconds
            print(f"  ⚠️ Round has expired, should be ended")
            continue
        
        # Try to start timer for this round
        try:
            timer_started = await server_timer.start_round_timer(round_obj.room, round_obj)
            if timer_started:
                print(f"  ✅ Timer restarted for room {round_obj.room}")
                
                # Check timer state
                time_remaining, phase = server_timer.get_accurate_time_remaining(round_obj.room)
                print(f"  ⏱️ Time remaining: {time_remaining:.1f}s, Phase: {phase}")
            else:
                print(f"  ❌ Failed to restart timer for room {round_obj.room}")
        except Exception as e:
            print(f"  ❌ Error restarting timer: {e}")
    
    print(f"\n📊 Final status:")
    print(f"Active timers: {list(server_timer.active_timers.keys())}")
    print(f"Timer management running: {server_timer.timer_task and not server_timer.timer_task.done()}")

if __name__ == "__main__":
    asyncio.run(fix_timer())
