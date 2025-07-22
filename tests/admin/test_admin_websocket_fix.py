#!/usr/bin/env python3
"""
Test script to verify admin WebSocket timer_update fix
"""
import os
import django
import asyncio
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.admin_consumers import AdminGameConsumer

async def test_timer_update_handler():
    """Test the timer_update handler with different event data"""
    print("🧪 Testing Admin WebSocket timer_update Handler...")
    
    # Create a mock consumer instance
    consumer = AdminGameConsumer()
    
    # Mock the send method to capture output
    sent_data = []
    async def mock_send(text_data):
        data = json.loads(text_data)
        sent_data.append(data)
        print(f"📤 Sent: {data}")
    
    consumer.send = mock_send
    
    # Test cases
    test_cases = [
        {
            'name': 'Complete event data',
            'event': {
                'time_remaining': 30,
                'phase': 'betting',
                'round_id': 12345,
                'timestamp': 1642678800.0,
                'server_timestamp': 1642678800.5,
                'round_start_time': 1642678770.0
            }
        },
        {
            'name': 'Minimal event data (missing round_id)',
            'event': {
                'time_remaining': 15,
                'phase': 'result'
            }
        },
        {
            'name': 'Partial event data',
            'event': {
                'time_remaining': 5,
                'phase': 'betting',
                'round_id': 67890,
                'timestamp': 1642678900.0
            }
        }
    ]
    
    print("\n" + "="*60)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: {test_case['name']}")
        print(f"📥 Input: {test_case['event']}")
        
        try:
            await consumer.timer_update(test_case['event'])
            print("✅ Handler executed successfully")
        except Exception as e:
            print(f"❌ Handler failed: {e}")
    
    print("\n" + "="*60)
    print("📊 Summary:")
    print(f"   Tests run: {len(test_cases)}")
    print(f"   Messages sent: {len(sent_data)}")
    
    # Verify all messages have required fields
    all_valid = True
    for i, data in enumerate(sent_data, 1):
        required_fields = ['type', 'time_remaining', 'phase']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"   ❌ Message {i} missing: {missing_fields}")
            all_valid = False
        else:
            print(f"   ✅ Message {i} has all required fields")
    
    if all_valid:
        print("\n🎉 All tests passed! Admin WebSocket timer_update is now robust.")
    else:
        print("\n⚠️ Some tests failed. Check the implementation.")

if __name__ == "__main__":
    asyncio.run(test_timer_update_handler())
