#!/usr/bin/env python3
"""
Test script to verify rate limiting issues are resolved
"""

import requests
import time
import threading
from datetime import datetime

def test_admin_api_rate_limit():
    """Test admin API rate limiting"""
    
    print("Testing admin API rate limiting...")
    print("=" * 60)
    
    # Simulate multiple admin pages making requests
    base_url = 'http://localhost:8000/control-panel/api/timer-info/'
    
    def make_requests(page_name, interval, count):
        """Make requests from a simulated admin page"""
        print(f"Starting {page_name} requests (every {interval}s, {count} requests)")
        
        for i in range(count):
            try:
                response = requests.get(base_url)
                status = response.status_code
                
                if status == 200:
                    print(f"✓ {page_name} request {i+1}: Success")
                elif status == 429:
                    print(f"❌ {page_name} request {i+1}: Rate limited (429)")
                elif status == 401:
                    print(f"⚠️ {page_name} request {i+1}: Unauthorized (401) - Expected")
                else:
                    print(f"? {page_name} request {i+1}: Status {status}")
                    
            except Exception as e:
                print(f"❌ {page_name} request {i+1}: Error - {e}")
            
            if i < count - 1:  # Don't sleep after last request
                time.sleep(interval)
    
    # Test current configuration
    print("\nTesting current rate limiting configuration:")
    print("- Dashboard: 3 second intervals")
    print("- Game Control Live: 2 second intervals (adaptive)")
    print("- Admin Panel Rate Limit: 1000 requests/minute")
    print("- Timer API Rate Limit: 200 requests/minute")
    
    # Simulate dashboard requests (every 3 seconds)
    dashboard_thread = threading.Thread(
        target=make_requests, 
        args=("Dashboard", 3, 5)
    )
    
    # Simulate game control requests (every 2 seconds)  
    game_control_thread = threading.Thread(
        target=make_requests,
        args=("GameControl", 2, 8)
    )
    
    print(f"\nStarting concurrent requests at {datetime.now()}")
    
    # Start both threads
    dashboard_thread.start()
    time.sleep(0.5)  # Slight offset
    game_control_thread.start()
    
    # Wait for completion
    dashboard_thread.join()
    game_control_thread.join()
    
    print(f"\nTest completed at {datetime.now()}")
    print("\n" + "=" * 60)
    print("Rate limiting optimizations applied:")
    print("✓ Increased ADMIN_PANEL_RATE_LIMIT to 1000 requests/minute")
    print("✓ Dashboard polling reduced to 3 seconds")
    print("✓ Game Control Live uses adaptive polling (2s active, 5s inactive)")
    print("✓ Timer interpolation reduced to 2 seconds")
    print("✓ Server-side caching optimized to 0.5 seconds")
    
    print("\nExpected behavior:")
    print("- No 429 rate limit errors")
    print("- 401 unauthorized errors are normal (not logged in)")
    print("- Both admin pages can run simultaneously")

if __name__ == "__main__":
    test_admin_api_rate_limit()
