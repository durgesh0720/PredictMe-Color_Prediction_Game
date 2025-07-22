#!/usr/bin/env python3
"""
Comprehensive WebSocket stability diagnostic script
"""
import os
import django
import asyncio
import time
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.websocket_reliability import reliable_ws_manager
from polling.monitoring import monitoring
from polling.models import GameRound, Player
from django.utils import timezone
from datetime import timedelta

async def diagnose_websocket_stability():
    """Diagnose WebSocket connection stability issues"""
    print("🔍 WebSocket Stability Diagnostic Report")
    print("=" * 60)
    
    # 1. Check WebSocket reliability stats
    print("\n📊 WebSocket Reliability Statistics:")
    try:
        stats = reliable_ws_manager.get_stats()
        print(f"   Total pending messages: {stats['total_pending']}")
        print(f"   Overdue messages: {stats['overdue_messages']}")
        print(f"   Critical messages: {stats['critical_messages']}")
        print(f"   Average retry count: {stats['avg_retry_count']:.2f}")
        
        if stats['overdue_messages'] > 0:
            print("   ⚠️ WARNING: Overdue messages detected - may cause connection issues")
        if stats['total_pending'] > 50:
            print("   ⚠️ WARNING: High pending message count - may cause memory issues")
        if stats['critical_messages'] > 10:
            print("   ⚠️ WARNING: Many critical messages pending - may cause game disruption")
            
    except Exception as e:
        print(f"   ❌ Error getting reliability stats: {e}")
    
    # 2. Check active game rounds
    print("\n🎮 Active Game Rounds:")
    try:
        active_rounds = GameRound.objects.filter(ended=False)
        print(f"   Active rounds count: {active_rounds.count()}")
        
        for round_obj in active_rounds:
            elapsed = (timezone.now() - round_obj.start_time).total_seconds()
            print(f"   Round {round_obj.period_id}: {elapsed:.1f}s elapsed, room={round_obj.room}")
            
            if elapsed > 60:  # Rounds should last ~50 seconds
                print(f"     ⚠️ WARNING: Round {round_obj.period_id} is overdue ({elapsed:.1f}s)")
                
    except Exception as e:
        print(f"   ❌ Error checking game rounds: {e}")
    
    # 3. Check monitoring system
    print("\n📈 Monitoring System Status:")
    try:
        # Check if monitoring is running
        print(f"   Monitoring active: {hasattr(monitoring, 'monitoring_task')}")
        
        # Check recent WebSocket events (if available)
        recent_time = timezone.now() - timedelta(minutes=5)
        recent_players = Player.objects.filter(last_login__gte=recent_time).count()
        print(f"   Recent active players (5min): {recent_players}")
        
    except Exception as e:
        print(f"   ❌ Error checking monitoring: {e}")
    
    # 4. Check for common stability issues
    print("\n🔧 Common Stability Issues Check:")
    
    # Check for stuck rounds
    stuck_rounds = GameRound.objects.filter(
        ended=False,
        start_time__lt=timezone.now() - timedelta(minutes=2)
    )
    if stuck_rounds.exists():
        print(f"   ⚠️ WARNING: {stuck_rounds.count()} stuck rounds detected")
        for round_obj in stuck_rounds:
            elapsed = (timezone.now() - round_obj.start_time).total_seconds()
            print(f"     Round {round_obj.period_id}: stuck for {elapsed:.1f}s")
    else:
        print("   ✅ No stuck rounds detected")
    
    # Check for memory leaks in game_rooms
    try:
        from polling.consumers import game_rooms
        print(f"   Active game rooms in memory: {len(game_rooms)}")
        
        for room_name, room_data in game_rooms.items():
            players_count = len(room_data.get('players', set()))
            print(f"     Room {room_name}: {players_count} players")
            
            if players_count == 0:
                print(f"       ⚠️ WARNING: Empty room {room_name} still in memory")
                
    except Exception as e:
        print(f"   ❌ Error checking game rooms: {e}")
    
    # 5. Recommendations
    print("\n💡 Stability Recommendations:")
    
    recommendations = []
    
    # Check reliability stats for recommendations
    try:
        stats = reliable_ws_manager.get_stats()
        if stats['overdue_messages'] > 5:
            recommendations.append("Reduce WebSocket message timeout or increase retry attempts")
        if stats['total_pending'] > 30:
            recommendations.append("Implement message queue cleanup or increase processing speed")
    except:
        pass
    
    # Check for stuck rounds
    if stuck_rounds.exists():
        recommendations.append("Implement automatic round cleanup for stuck rounds")
        recommendations.append("Add round timeout monitoring")
    
    # Check for empty rooms
    try:
        from polling.consumers import game_rooms
        empty_rooms = sum(1 for room_data in game_rooms.values() 
                         if len(room_data.get('players', set())) == 0)
        if empty_rooms > 0:
            recommendations.append("Implement automatic cleanup of empty game rooms")
    except:
        pass
    
    if not recommendations:
        recommendations.append("✅ No immediate stability issues detected")
    
    for i, rec in enumerate(recommendations, 1):
        print(f"   {i}. {rec}")
    
    print("\n" + "=" * 60)
    print("🎯 Next Steps:")
    print("1. Monitor the above metrics regularly")
    print("2. Implement recommended fixes if issues are found")
    print("3. Check browser console for client-side connection errors")
    print("4. Monitor server logs for WebSocket disconnection patterns")

if __name__ == "__main__":
    asyncio.run(diagnose_websocket_stability())
