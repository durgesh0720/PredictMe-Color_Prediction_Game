#!/usr/bin/env python3
"""
Test script to verify real-time betting updates in admin panel
This script simulates placing bets and checks if the admin panel updates correctly
"""

import asyncio
import websockets
import json
import time
import random
from datetime import datetime

# WebSocket URLs
USER_WS_URL = "ws://localhost:8000/ws/parity/"
ADMIN_WS_URL = "ws://localhost:8000/ws/control-panel/game-control/"

# Test user credentials (you may need to adjust these)
TEST_USERS = [
    {"username": "testuser1", "token": "test_token_1"},
    {"username": "testuser2", "token": "test_token_2"},
    {"username": "testuser3", "token": "test_token_3"},
]

COLORS = ["red", "green", "violet", "blue"]
BET_AMOUNTS = [10, 20, 50, 100]

class BettingTester:
    def __init__(self):
        self.admin_ws = None
        self.user_connections = []
        self.running = True
        
    async def connect_admin(self):
        """Connect to admin WebSocket"""
        try:
            print("Connecting to admin WebSocket...")
            self.admin_ws = await websockets.connect(ADMIN_WS_URL)
            print("✅ Admin WebSocket connected")
            
            # Start listening for admin messages
            asyncio.create_task(self.listen_admin_messages())
            
            # Request initial stats
            await self.admin_ws.send(json.dumps({
                "type": "get_live_stats"
            }))
            
        except Exception as e:
            print(f"❌ Failed to connect to admin WebSocket: {e}")
    
    async def listen_admin_messages(self):
        """Listen for messages from admin WebSocket"""
        try:
            async for message in self.admin_ws:
                data = json.loads(message)
                if data.get('type') == 'live_betting_stats':
                    print(f"📊 Admin received betting stats: {data.get('stats', {})}")
                elif data.get('type') == 'bet_placed_update':
                    print(f"🎯 Admin received bet update: {data.get('username')} bet ₹{data.get('amount')} on {data.get('color')}")
                else:
                    print(f"📨 Admin received: {data.get('type', 'unknown')}")
        except websockets.exceptions.ConnectionClosed:
            print("🔌 Admin WebSocket connection closed")
        except Exception as e:
            print(f"❌ Error in admin message listener: {e}")
    
    async def connect_user(self, username):
        """Connect a user to the betting WebSocket"""
        try:
            print(f"Connecting user {username}...")
            ws = await websockets.connect(USER_WS_URL)
            print(f"✅ User {username} connected")
            
            # Send authentication (simplified for testing)
            await ws.send(json.dumps({
                "type": "authenticate",
                "username": username
            }))
            
            self.user_connections.append((username, ws))
            return ws
            
        except Exception as e:
            print(f"❌ Failed to connect user {username}: {e}")
            return None
    
    async def place_bet(self, username, ws, color, amount):
        """Place a bet for a user"""
        try:
            bet_data = {
                "type": "bet",
                "bet_type": "color",
                "color": color,
                "amount": amount,
                "timestamp": time.time()
            }
            
            await ws.send(json.dumps(bet_data))
            print(f"🎲 {username} placed bet: ₹{amount} on {color}")
            
            # Wait for response
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            if response_data.get('type') == 'error':
                print(f"❌ Bet failed for {username}: {response_data.get('message')}")
                return False
            else:
                print(f"✅ Bet confirmed for {username}")
                return True
                
        except asyncio.TimeoutError:
            print(f"⏰ Timeout waiting for bet response from {username}")
            return False
        except Exception as e:
            print(f"❌ Error placing bet for {username}: {e}")
            return False
    
    async def simulate_betting_session(self):
        """Simulate a betting session with multiple users"""
        print("🚀 Starting betting simulation...")
        
        # Connect admin first
        await self.connect_admin()
        await asyncio.sleep(2)
        
        # Connect test users
        for i in range(3):  # Connect 3 test users
            username = f"testuser{i+1}"
            ws = await self.connect_user(username)
            if ws:
                await asyncio.sleep(1)
        
        print(f"👥 Connected {len(self.user_connections)} users")
        
        # Simulate betting for 30 seconds
        start_time = time.time()
        bet_count = 0
        
        while time.time() - start_time < 30 and self.running:
            # Pick a random user and place a bet
            if self.user_connections:
                username, ws = random.choice(self.user_connections)
                color = random.choice(COLORS)
                amount = random.choice(BET_AMOUNTS)
                
                success = await self.place_bet(username, ws, color, amount)
                if success:
                    bet_count += 1
                
                # Wait between bets
                await asyncio.sleep(random.uniform(2, 5))
        
        print(f"🏁 Simulation completed. Placed {bet_count} bets in 30 seconds")
        
        # Keep admin connection open for a bit longer to see final stats
        print("📊 Waiting for final stats updates...")
        await asyncio.sleep(10)
    
    async def cleanup(self):
        """Clean up connections"""
        print("🧹 Cleaning up connections...")
        
        for username, ws in self.user_connections:
            try:
                await ws.close()
                print(f"🔌 Closed connection for {username}")
            except:
                pass
        
        if self.admin_ws:
            try:
                await self.admin_ws.close()
                print("🔌 Closed admin connection")
            except:
                pass

async def main():
    """Main test function"""
    print("🎮 WebSocket Betting Update Test")
    print("=" * 50)
    
    tester = BettingTester()
    
    try:
        await tester.simulate_betting_session()
    except KeyboardInterrupt:
        print("\n⏹️  Test interrupted by user")
        tester.running = False
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
    finally:
        await tester.cleanup()
    
    print("✅ Test completed")

if __name__ == "__main__":
    print("Starting WebSocket betting test...")
    print("Make sure the Django server is running on localhost:8000")
    print("Open the admin panel at http://localhost:8000/admin/game-control-live/")
    print("Press Ctrl+C to stop the test")
    print()
    
    asyncio.run(main())
