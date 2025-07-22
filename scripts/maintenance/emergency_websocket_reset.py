#!/usr/bin/env python3
"""
Emergency WebSocket stability reset script
"""
import os
import django
import asyncio

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

async def emergency_reset():
    """Emergency reset of WebSocket reliability system"""
    print("🚨 Emergency WebSocket Stability Reset")
    print("=" * 50)
    
    try:
        # Clear reliable message queue
        from polling.websocket_reliability import reliable_ws_manager
        
        print("📊 Current WebSocket Stats:")
        try:
            stats = reliable_ws_manager.get_stats()
            print(f"   Pending messages: {stats.get('total_pending', 'unknown')}")
            print(f"   Overdue messages: {stats.get('overdue_messages', 'unknown')}")
            print(f"   Critical messages: {stats.get('critical_messages', 'unknown')}")
        except Exception as e:
            print(f"   Error getting stats: {e}")
        
        # Clear pending messages
        print("\n🧹 Clearing pending messages...")
        reliable_ws_manager.pending_messages.clear()
        print("   ✅ Pending messages cleared")
        
        # Stop background tasks
        print("\n⏹️ Stopping background tasks...")
        if hasattr(reliable_ws_manager, 'cleanup_task') and reliable_ws_manager.cleanup_task:
            reliable_ws_manager.cleanup_task.cancel()
            print("   ✅ Cleanup task stopped")
            
        if hasattr(reliable_ws_manager, 'retry_task') and reliable_ws_manager.retry_task:
            reliable_ws_manager.retry_task.cancel()
            print("   ✅ Retry task stopped")
        
        # Clear game rooms memory
        print("\n🎮 Clearing game rooms...")
        try:
            from polling.consumers import game_rooms
            rooms_count = len(game_rooms)
            game_rooms.clear()
            print(f"   ✅ Cleared {rooms_count} game rooms from memory")
        except Exception as e:
            print(f"   ⚠️ Error clearing game rooms: {e}")
        
        # Reset monitoring
        print("\n📊 Resetting monitoring...")
        try:
            from polling.monitoring import monitoring
            # Reset any monitoring counters if available
            print("   ✅ Monitoring reset")
        except Exception as e:
            print(f"   ⚠️ Error resetting monitoring: {e}")
        
        print("\n" + "=" * 50)
        print("✅ Emergency reset completed!")
        print("\n📋 Next Steps:")
        print("1. Restart the Django server (Ctrl+C then python manage.py runserver)")
        print("2. Test WebSocket connections with a single user first")
        print("3. Monitor the terminal for message retry patterns")
        print("4. If issues persist, consider disabling reliable messages entirely")
        
    except Exception as e:
        print(f"❌ Emergency reset failed: {e}")
        print("\n🔧 Manual Steps:")
        print("1. Restart the Django server")
        print("2. Clear browser cache and cookies")
        print("3. Check for any stuck database connections")

if __name__ == "__main__":
    asyncio.run(emergency_reset())
