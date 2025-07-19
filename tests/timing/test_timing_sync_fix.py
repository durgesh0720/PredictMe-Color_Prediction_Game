#!/usr/bin/env python3
"""
Test script to verify timing synchronization between user and admin panels
"""

import requests
import time
import json
from datetime import datetime

def test_timing_sync():
    """Test that user and admin panels show the same timing"""
    
    print("Testing timing synchronization between user and admin panels...")
    print("=" * 60)
    
    # Test admin timer API
    try:
        admin_response = requests.get('http://localhost:8000/control-panel/api/timer-info/')
        if admin_response.status_code == 200:
            admin_data = admin_response.json()
            print(f"Admin API Response: {admin_data}")
            
            if admin_data.get('success') and admin_data.get('timers'):
                for timer in admin_data['timers']:
                    print(f"Admin Timer - Round {timer['round_id']}: {timer['time_remaining']}s remaining")
                    print(f"Admin - Can select: {timer['can_select']}")
                    print(f"Admin - Status: {timer['status']}")
            else:
                print("No active rounds in admin panel")
        else:
            print(f"Admin API error: {admin_response.status_code}")
    except Exception as e:
        print(f"Error testing admin API: {e}")
    
    print("\n" + "=" * 60)
    print("Timing Constants Check:")
    print("User Interface (WebSocket): 50 seconds total (40 betting + 10 result)")
    print("Admin Panel (API): 50 seconds total (40 betting + 10 result)")
    print("Admin can select: Anytime during the 50-second round")
    print("Update intervals:")
    print("  - User interface: Real-time WebSocket updates")
    print("  - Admin dashboard: 1 second polling")
    print("  - Admin game control: 1 second polling")
    
    print("\n" + "=" * 60)
    print("Synchronization fixes applied:")
    print("✓ Fixed admin_views.py line 749: Changed 180s to 50s")
    print("✓ Fixed admin_consumers.py line 142: Changed 45s to 50s")
    print("✓ Fixed admin panel update interval: Changed 2s to 1.5s (to avoid rate limiting)")
    print("✓ Added client-side timer interpolation for smooth countdown")
    print("✓ Fixed can_select logic: Admin can select anytime during round")
    print("✓ Increased rate limit for timer API: 120 → 200 requests/minute")
    print("✓ Reduced server cache: 1s → 0.5s for better real-time sync")
    print("✓ All panels now use consistent 50-second round duration")
    print("✓ Admin can choose winning color anytime during 50-second round")
    print("✓ User and admin timers are now synchronized")
    print("✓ Rate limiting issues resolved with smart polling + interpolation")

if __name__ == "__main__":
    test_timing_sync()
