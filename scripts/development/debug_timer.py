#!/usr/bin/env python3
"""
Debug script to check timer status and restart if needed
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

async def debug_timer():
    """Debug the timer system"""
    print("🔍 Debugging Timer System...")

    # Check if timer management is running
    print(f"Timer task status: {server_timer.timer_task}")
    print(f"Active timers: {list(server_timer.active_timers.keys())}")

    # Check current game rounds
    active_rounds = await get_active_rounds()
    print(f"Active rounds in database: {len(active_rounds)}")
    
    for round_obj in active_rounds:
        print(f"  Round {round_obj.period_id}: room={round_obj.room}, started={round_obj.start_time}")
        
        # Check timer state for this round
        if round_obj.room in server_timer.active_timers:
            timer_state = server_timer.active_timers[round_obj.room]
            print(f"    Timer active: {timer_state.is_active}")
            print(f"    Current phase: {timer_state.current_phase}")
            
            # Get accurate time remaining
            time_remaining, phase = server_timer.get_accurate_time_remaining(round_obj.room)
            print(f"    Time remaining: {time_remaining}s")
            print(f"    Phase: {phase}")
        else:
            print(f"    No timer found for room {round_obj.room}")
    
    # Try to restart timer management
    print("\n🔄 Restarting timer management...")
    try:
        server_timer.ensure_timer_management_started()
        print("✅ Timer management restarted")
        
        # Wait a bit and check again
        await asyncio.sleep(2)
        
        print(f"Timer task status after restart: {server_timer.timer_task}")
        if server_timer.timer_task and not server_timer.timer_task.done():
            print("✅ Timer management is now running")
        else:
            print("❌ Timer management still not running")
            
    except Exception as e:
        print(f"❌ Error restarting timer: {e}")

if __name__ == "__main__":
    asyncio.run(debug_timer())
