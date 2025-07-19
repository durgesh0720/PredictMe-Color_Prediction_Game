"""
Comprehensive API endpoints tests for the Color Prediction Game.
Tests all API endpoints, security measures, rate limiting, and error handling.
"""

import json
import time
from unittest.mock import patch, Mock
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from polling.models import Player, Admin, GameRound, Bet, Transaction, NotificationType
from tests.conftest import BaseTestCase, PlayerFactory, AdminFactory, GameRoundFactory
from tests.utils import (
    TestClient, AssertionHelpers, SecurityTestHelpers, 
    setup_test_notification_types
)


class PublicAPITests(BaseTestCase):
    """Test public API endpoints that don't require authentication."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
    
    def test_player_stats_api(self):
        """Test player statistics API endpoint."""
        player = PlayerFactory(username='testplayer')
        
        # Create some betting history
        game_round = GameRoundFactory()
        bet = Bet.objects.create(
            player=player,
            round=game_round,
            bet_type='color',
            color='red',
            amount=100
        )
        
        response = self.client.get(f'/api/player/{player.username}/')
        data = self.assert_json_response(response, 200)
        
        self.assertIn('username', data)
        self.assertIn('total_bets', data)
        self.assertIn('total_winnings', data)
        self.assertEqual(data['username'], 'testplayer')
    
    def test_player_stats_invalid_username(self):
        """Test player stats API with invalid username."""
        response = self.client.get('/api/player/nonexistent/')
        data = self.assert_json_response(response, 404)
        
        self.assertFalse(data['success'])
        self.assertIn('not found', data['message'].lower())
    
    def test_live_betting_stats_api(self):
        """Test live betting statistics API."""
        # Create active round with bets
        game_round = GameRoundFactory(ended=False)
        player1 = PlayerFactory()
        player2 = PlayerFactory()
        
        Bet.objects.create(
            player=player1,
            round=game_round,
            bet_type='color',
            color='red',
            amount=100
        )
        
        Bet.objects.create(
            player=player2,
            round=game_round,
            bet_type='color',
            color='green',
            amount=200
        )
        
        response = self.client.get('/api/live-betting-stats/')
        data = self.assert_json_response(response, 200)
        
        self.assertIn('betting_stats', data)
        self.assertIn('red', data['betting_stats'])
        self.assertIn('green', data['betting_stats'])
        self.assertEqual(data['betting_stats']['red']['total_amount'], 100)
        self.assertEqual(data['betting_stats']['green']['total_amount'], 200)


class AuthenticatedAPITests(BaseTestCase):
    """Test API endpoints that require user authentication."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory(balance=1000, email_verified=True)
        self.client.login_player(self.player)
        
        # Create active game round
        self.game_round = GameRoundFactory(ended=False)
    
    def test_place_bet_api_success(self):
        """Test successful bet placement via API."""
        bet_data = {
            'room': 'main',
            'bet_type': 'color',
            'color': 'red',
            'amount': 100
        }
        
        response = self.client.post_json('/api/place-bet/', bet_data)
        data = self.assert_json_response(response, 200)
        
        self.assertTrue(data['success'])
        
        # Check bet was created
        bet = Bet.objects.filter(
            player=self.player,
            round=self.game_round,
            amount=100
        ).first()
        self.assertIsNotNone(bet)
        
        # Check balance was deducted
        AssertionHelpers.assert_player_balance(self.player, 900)
    
    def test_place_bet_api_insufficient_balance(self):
        """Test bet placement with insufficient balance."""
        # Set low balance
        self.player.balance = 50
        self.player.save()
        
        bet_data = {
            'room': 'main',
            'bet_type': 'color',
            'color': 'red',
            'amount': 100
        }
        
        response = self.client.post_json('/api/place-bet/', bet_data)
        data = self.assert_json_response(response, 400)
        
        self.assertFalse(data['success'])
        self.assertIn('insufficient', data['message'].lower())
    
    def test_api_requires_authentication(self):
        """Test that protected APIs require authentication."""
        self.client.logout_player()
        
        protected_endpoints = [
            '/api/place-bet/',
            '/api/user/history/',
            '/api/user/balance/',
            '/api/user/transactions/',
        ]
        
        for endpoint in protected_endpoints:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 401, f"Endpoint {endpoint} should require authentication")


class APISecurityTests(BaseTestCase):
    """Test API security measures."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory(balance=1000)
        self.client.login_player(self.player)
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection in API endpoints."""
        sql_payloads = SecurityTestHelpers.test_sql_injection_payload()
        
        for payload in sql_payloads:
            # Test in username parameter
            response = self.client.get(f'/api/player/{payload}/')
            
            # Should return 400 or 404, not 500 (which would indicate SQL error)
            self.assertIn(response.status_code, [400, 404])
    
    def test_input_validation(self):
        """Test input validation on API endpoints."""
        # Test invalid bet amount
        invalid_data = [
            {'amount': -100},  # Negative amount
            {'amount': 'invalid'},  # Non-numeric amount
            {'amount': 999999},  # Too large amount
            {'color': 'invalid_color'},  # Invalid color
            {'room': ''},  # Empty room
        ]
        
        for data in invalid_data:
            bet_data = {
                'room': 'main',
                'bet_type': 'color',
                'color': 'red',
                'amount': 100
            }
            bet_data.update(data)
            
            response = self.client.post_json('/api/place-bet/', bet_data)
            
            # Should return 400 Bad Request for invalid data
            self.assertEqual(response.status_code, 400)


class URLRoutingTests(BaseTestCase):
    """Test URL routing and basic page loads."""
    
    def setUp(self):
        super().setUp()
        self.client = TestClient()
    
    def test_public_urls_accessible(self):
        """Test that public URLs are accessible."""
        public_urls = [
            '/',
            '/register/',
            '/login/',
            '/game-history/',
        ]
        
        for url in public_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200, f"URL {url} should be accessible")
    
    def test_invalid_urls_return_404(self):
        """Test that invalid URLs return 404."""
        invalid_urls = [
            '/nonexistent/',
            '/room/',  # Missing room name
            '/api/invalid/',
        ]
        
        for url in invalid_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 404, f"URL {url} should return 404")
    
    def test_room_urls(self):
        """Test room URL patterns."""
        # Test valid room
        response = self.client.get('/room/main/')
        # Should either load the room or redirect to login
        self.assertIn(response.status_code, [200, 302])
        
        # Test invalid room (should redirect to main room)
        response = self.client.get('/room/test_room/')
        self.assertIn(response.status_code, [200, 302])


class PerformanceTests(BaseTestCase):
    """Test API performance and load handling."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        
        # Create test data
        self.players = []
        for i in range(10):
            player = PlayerFactory(
                username=f'perftest{i}',
                balance=1000
            )
            self.players.append(player)
    
    def test_concurrent_api_requests(self):
        """Test handling of concurrent API requests."""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = self.client.get('/api/live-betting-stats/')
            results.append(response.status_code)
        
        # Create multiple threads
        threads = []
        for i in range(5):  # Reduced for test stability
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # All requests should succeed
        self.assertEqual(len(results), 5)
        self.assertTrue(all(status == 200 for status in results))
        
        # Should complete within reasonable time
        execution_time = end_time - start_time
        self.assertLess(execution_time, 5.0, "Concurrent requests took too long")
    
    def test_large_data_handling(self):
        """Test API handling of large datasets."""
        # Create many game rounds
        for i in range(50):  # Reduced for test performance
            GameRoundFactory(
                period_id=f'perf_round_{i}',
                result_color='red' if i % 2 == 0 else 'green',
                ended=True
            )
        
        start_time = time.time()
        response = self.client.get('/game-history/')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # Should complete within reasonable time
        execution_time = end_time - start_time
        self.assertLess(execution_time, 3.0, "Large data handling took too long")
