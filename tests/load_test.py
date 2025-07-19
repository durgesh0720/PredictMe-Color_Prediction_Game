"""
Load testing script for the color prediction game
Tests system performance under concurrent load

Usage:
python tests/load_test.py --users 100 --duration 60 --bet-rate 2
"""
import asyncio
import aiohttp
import websockets
import json
import time
import random
import argparse
import statistics
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import List, Dict


@dataclass
class TestResult:
    """Test result metrics"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    response_times: List[float] = None
    websocket_connections: int = 0
    websocket_failures: int = 0
    bet_successes: int = 0
    bet_failures: int = 0
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []


class LoadTester:
    """Load testing framework for the game system"""
    
    def __init__(self, base_url: str = "http://localhost:8000", ws_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.results = TestResult()
        self.active_sessions = []
        
    async def create_test_user(self, session: aiohttp.ClientSession, user_id: int) -> Dict:
        """Create a test user account"""
        try:
            # Register user
            register_data = {
                'username': f'testuser_{user_id}',
                'email': f'test_{user_id}@example.com',
                'password': 'testpass123',
                'confirm_password': 'testpass123'
            }
            
            start_time = time.time()
            async with session.post(f"{self.base_url}/register/", data=register_data) as resp:
                response_time = time.time() - start_time
                self.results.response_times.append(response_time)
                self.results.total_requests += 1
                
                if resp.status == 200 or resp.status == 302:  # Success or redirect
                    self.results.successful_requests += 1
                    return {
                        'username': register_data['username'],
                        'password': register_data['password'],
                        'user_id': user_id
                    }
                else:
                    self.results.failed_requests += 1
                    return None
                    
        except Exception as e:
            print(f"Error creating user {user_id}: {e}")
            self.results.failed_requests += 1
            return None
    
    async def login_user(self, session: aiohttp.ClientSession, user_data: Dict) -> bool:
        """Login a test user"""
        try:
            login_data = {
                'username': user_data['username'],
                'password': user_data['password']
            }
            
            start_time = time.time()
            async with session.post(f"{self.base_url}/login/", data=login_data) as resp:
                response_time = time.time() - start_time
                self.results.response_times.append(response_time)
                self.results.total_requests += 1
                
                if resp.status == 200 or resp.status == 302:
                    self.results.successful_requests += 1
                    return True
                else:
                    self.results.failed_requests += 1
                    return False
                    
        except Exception as e:
            print(f"Error logging in user {user_data['username']}: {e}")
            self.results.failed_requests += 1
            return False
    
    async def websocket_client(self, user_data: Dict, duration: int, bet_rate: float):
        """Simulate a WebSocket client for a user"""
        try:
            # Connect to WebSocket
            uri = f"{self.ws_url}/ws/game/main/"
            async with websockets.connect(uri) as websocket:
                self.results.websocket_connections += 1
                print(f"WebSocket connected for user {user_data['username']}")
                
                # Send initial game state request
                await websocket.send(json.dumps({
                    'type': 'get_game_state'
                }))
                
                start_time = time.time()
                last_bet_time = 0
                
                while time.time() - start_time < duration:
                    try:
                        # Listen for messages with timeout
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)
                        
                        # Handle different message types
                        if data.get('type') == 'game_state':
                            # Check if we can place a bet
                            current_time = time.time()
                            if (current_time - last_bet_time > (1.0 / bet_rate) and 
                                data.get('phase') == 'betting' and 
                                not data.get('betting_closed')):
                                
                                await self.place_bet(websocket, user_data)
                                last_bet_time = current_time
                        
                        elif data.get('type') == 'timer_update':
                            # Acknowledge timer updates if required
                            if data.get('requires_ack'):
                                await websocket.send(json.dumps({
                                    'type': 'message_ack',
                                    'message_id': data.get('message_id')
                                }))
                        
                        elif data.get('type') == 'round_ended':
                            # Acknowledge round end messages
                            if data.get('requires_ack'):
                                await websocket.send(json.dumps({
                                    'type': 'message_ack',
                                    'message_id': data.get('message_id')
                                }))
                    
                    except asyncio.TimeoutError:
                        # Send ping to keep connection alive
                        await websocket.send(json.dumps({
                            'type': 'ping',
                            'timestamp': time.time()
                        }))
                    
                    except Exception as e:
                        print(f"WebSocket error for user {user_data['username']}: {e}")
                        break
                
                print(f"WebSocket session ended for user {user_data['username']}")
                
        except Exception as e:
            print(f"WebSocket connection failed for user {user_data['username']}: {e}")
            self.results.websocket_failures += 1
    
    async def place_bet(self, websocket, user_data: Dict):
        """Place a bet through WebSocket"""
        try:
            colors = ['red', 'green', 'violet', 'blue']
            bet_amounts = [100, 200, 500, 1000]  # $1, $2, $5, $10
            
            bet_data = {
                'type': 'place_bet',
                'bet_type': 'color',
                'color': random.choice(colors),
                'amount': random.choice(bet_amounts),
                'timestamp': time.time()
            }
            
            await websocket.send(json.dumps(bet_data))
            
            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)
            
            if response_data.get('type') == 'bet_placed':
                self.results.bet_successes += 1
                print(f"Bet placed successfully for user {user_data['username']}")
            else:
                self.results.bet_failures += 1
                print(f"Bet failed for user {user_data['username']}: {response_data.get('message', 'Unknown error')}")
                
        except Exception as e:
            self.results.bet_failures += 1
            print(f"Error placing bet for user {user_data['username']}: {e}")
    
    async def api_load_test(self, session: aiohttp.ClientSession, duration: int):
        """Test API endpoints under load"""
        start_time = time.time()
        
        endpoints = [
            '/api/responsible-gambling/status/',
            '/api/monitoring/dashboard/',
            '/game-history/',
        ]
        
        while time.time() - start_time < duration:
            try:
                endpoint = random.choice(endpoints)
                
                start_req = time.time()
                async with session.get(f"{self.base_url}{endpoint}") as resp:
                    response_time = time.time() - start_req
                    self.results.response_times.append(response_time)
                    self.results.total_requests += 1
                    
                    if resp.status == 200:
                        self.results.successful_requests += 1
                    else:
                        self.results.failed_requests += 1
                
                # Random delay between requests
                await asyncio.sleep(random.uniform(0.1, 1.0))
                
            except Exception as e:
                self.results.failed_requests += 1
                print(f"API request error: {e}")
    
    async def run_user_simulation(self, user_id: int, duration: int, bet_rate: float):
        """Run complete user simulation"""
        async with aiohttp.ClientSession() as session:
            # Create and login user
            user_data = await self.create_test_user(session, user_id)
            if not user_data:
                return
            
            login_success = await self.login_user(session, user_data)
            if not login_success:
                return
            
            # Run WebSocket simulation and API testing concurrently
            tasks = [
                self.websocket_client(user_data, duration, bet_rate),
                self.api_load_test(session, duration)
            ]
            
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def run_load_test(self, num_users: int, duration: int, bet_rate: float):
        """Run the complete load test"""
        print(f"Starting load test with {num_users} users for {duration} seconds")
        print(f"Bet rate: {bet_rate} bets per second per user")
        
        start_time = time.time()
        
        # Create tasks for all users
        tasks = []
        for user_id in range(num_users):
            task = self.run_user_simulation(user_id, duration, bet_rate)
            tasks.append(task)
        
        # Run all user simulations concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        total_time = time.time() - start_time
        
        # Print results
        self.print_results(total_time)
    
    def print_results(self, total_time: float):
        """Print load test results"""
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        
        print(f"Total test duration: {total_time:.2f} seconds")
        print(f"Total requests: {self.results.total_requests}")
        print(f"Successful requests: {self.results.successful_requests}")
        print(f"Failed requests: {self.results.failed_requests}")
        
        if self.results.total_requests > 0:
            success_rate = (self.results.successful_requests / self.results.total_requests) * 100
            print(f"Success rate: {success_rate:.2f}%")
            
            requests_per_second = self.results.total_requests / total_time
            print(f"Requests per second: {requests_per_second:.2f}")
        
        if self.results.response_times:
            avg_response_time = statistics.mean(self.results.response_times)
            median_response_time = statistics.median(self.results.response_times)
            max_response_time = max(self.results.response_times)
            min_response_time = min(self.results.response_times)
            
            print(f"\nResponse Times:")
            print(f"  Average: {avg_response_time:.3f}s")
            print(f"  Median: {median_response_time:.3f}s")
            print(f"  Min: {min_response_time:.3f}s")
            print(f"  Max: {max_response_time:.3f}s")
        
        print(f"\nWebSocket Connections:")
        print(f"  Successful: {self.results.websocket_connections}")
        print(f"  Failed: {self.results.websocket_failures}")
        
        print(f"\nBetting:")
        print(f"  Successful bets: {self.results.bet_successes}")
        print(f"  Failed bets: {self.results.bet_failures}")
        
        if self.results.bet_successes + self.results.bet_failures > 0:
            bet_success_rate = (self.results.bet_successes / (self.results.bet_successes + self.results.bet_failures)) * 100
            print(f"  Bet success rate: {bet_success_rate:.2f}%")
        
        print("\n" + "="*60)


async def main():
    """Main function to run load tests"""
    parser = argparse.ArgumentParser(description='Load test the color prediction game')
    parser.add_argument('--users', type=int, default=10, help='Number of concurrent users')
    parser.add_argument('--duration', type=int, default=30, help='Test duration in seconds')
    parser.add_argument('--bet-rate', type=float, default=0.5, help='Bets per second per user')
    parser.add_argument('--base-url', default='http://localhost:8000', help='Base URL of the application')
    parser.add_argument('--ws-url', default='ws://localhost:8000', help='WebSocket URL of the application')
    
    args = parser.parse_args()
    
    tester = LoadTester(args.base_url, args.ws_url)
    await tester.run_load_test(args.users, args.duration, args.bet_rate)


if __name__ == '__main__':
    asyncio.run(main())
