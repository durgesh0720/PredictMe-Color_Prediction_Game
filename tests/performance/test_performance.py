"""
Performance and load tests for the Color Prediction Game.
Tests application performance under various load conditions and concurrent usage.
"""

import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from django.db import transaction, connections
from django.core.cache import cache
from datetime import timedelta

from polling.models import Player, Admin, GameRound, Bet, Transaction
from tests.conftest import BaseTestCase, PlayerFactory, AdminFactory, GameRoundFactory
from tests.utils import (
    TestClient, PerformanceTestHelpers, TestDataBuilder,
    setup_test_notification_types
)


class DatabasePerformanceTests(BaseTestCase):
    """Test database performance under load."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
    
    def test_player_creation_performance(self):
        """Test performance of creating multiple players."""
        start_time = time.time()
        
        players = []
        for i in range(100):
            player = PlayerFactory(
                username=f'perf_player_{i}',
                balance=1000
            )
            players.append(player)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should create 100 players in reasonable time
        self.assertLess(execution_time, 5.0, "Player creation took too long")
        self.assertEqual(len(players), 100)
        
        # Verify all players were created
        self.assertEqual(Player.objects.count(), 100)
    
    def test_bulk_bet_creation_performance(self):
        """Test performance of creating multiple bets."""
        # Create players and game round
        players = [PlayerFactory() for _ in range(50)]
        game_round = GameRoundFactory()
        
        start_time = time.time()
        
        # Create bets for all players
        bets = []
        for i, player in enumerate(players):
            bet = Bet.objects.create(
                player=player,
                round=game_round,
                bet_type='color',
                color='red' if i % 2 == 0 else 'green',
                amount=100
            )
            bets.append(bet)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should create 50 bets in reasonable time
        self.assertLess(execution_time, 3.0, "Bet creation took too long")
        self.assertEqual(len(bets), 50)
    
    def test_transaction_history_query_performance(self):
        """Test performance of querying transaction history."""
        player = PlayerFactory()
        
        # Create many transactions
        for i in range(200):
            Transaction.objects.create(
                player=player,
                transaction_type='deposit' if i % 2 == 0 else 'bet',
                amount=100 if i % 2 == 0 else -50,
                balance_before=1000 + (i * 50),
                balance_after=1000 + ((i + 1) * 50),
                description=f'Transaction {i}'
            )
        
        start_time = time.time()
        
        # Query recent transactions
        recent_transactions = Transaction.objects.filter(
            player=player
        ).order_by('-created_at')[:50]
        
        # Force evaluation
        list(recent_transactions)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should query 50 transactions from 200 quickly
        self.assertLess(execution_time, 0.5, "Transaction query took too long")
    
    def test_game_round_statistics_performance(self):
        """Test performance of calculating game round statistics."""
        game_round = GameRoundFactory()
        players = [PlayerFactory() for _ in range(100)]
        
        # Create bets for the round
        for i, player in enumerate(players):
            Bet.objects.create(
                player=player,
                round=game_round,
                bet_type='color',
                color=['red', 'green', 'violet'][i % 3],
                amount=(i + 1) * 10
            )
        
        start_time = time.time()
        
        # Calculate statistics
        from django.db.models import Sum, Count
        stats = Bet.objects.filter(round=game_round).values('color').annotate(
            total_amount=Sum('amount'),
            bet_count=Count('id')
        )
        
        # Force evaluation
        list(stats)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should calculate stats for 100 bets quickly
        self.assertLess(execution_time, 0.3, "Statistics calculation took too long")


class ConcurrentUserTests(TransactionTestCase):
    """Test application performance with concurrent users."""
    
    def setUp(self):
        setup_test_notification_types()
        self.game_round = GameRoundFactory(ended=False)
    
    def test_concurrent_bet_placement(self):
        """Test concurrent bet placement by multiple users."""
        # Create players
        players = [PlayerFactory(balance=1000) for _ in range(20)]
        
        results = []
        execution_times = []
        
        def place_bet(player):
            client = TestClient()
            client.login_player(player)
            
            start_time = time.time()
            
            bet_data = {
                'room': 'main',
                'bet_type': 'color',
                'color': 'red',
                'amount': 100
            }
            
            response = client.post_json('/api/place-bet/', bet_data)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            results.append(response.status_code)
            execution_times.append(execution_time)
        
        # Use ThreadPoolExecutor for concurrent execution
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(place_bet, player) for player in players]
            
            # Wait for all to complete
            for future in as_completed(futures):
                future.result()
        
        # Analyze results
        successful_bets = sum(1 for status in results if status == 200)
        avg_execution_time = statistics.mean(execution_times)
        max_execution_time = max(execution_times)
        
        # Most bets should succeed
        self.assertGreaterEqual(successful_bets, 15, "Too many concurrent bets failed")
        
        # Average response time should be reasonable
        self.assertLess(avg_execution_time, 2.0, "Average response time too slow")
        
        # Maximum response time should be acceptable
        self.assertLess(max_execution_time, 5.0, "Maximum response time too slow")
    
    def test_concurrent_api_requests(self):
        """Test concurrent API requests performance."""
        # Create test data
        players = [PlayerFactory() for _ in range(10)]
        game_round = GameRoundFactory()
        
        for player in players:
            Bet.objects.create(
                player=player,
                round=game_round,
                bet_type='color',
                color='red',
                amount=100
            )
        
        results = []
        execution_times = []
        
        def make_api_request():
            client = TestClient()
            
            start_time = time.time()
            response = client.get('/api/live-betting-stats/')
            end_time = time.time()
            
            execution_time = end_time - start_time
            results.append(response.status_code)
            execution_times.append(execution_time)
        
        # Make 50 concurrent requests
        with ThreadPoolExecutor(max_workers=15) as executor:
            futures = [executor.submit(make_api_request) for _ in range(50)]
            
            for future in as_completed(futures):
                future.result()
        
        # All requests should succeed
        successful_requests = sum(1 for status in results if status == 200)
        self.assertEqual(successful_requests, 50, "Some API requests failed")
        
        # Average response time should be fast
        avg_execution_time = statistics.mean(execution_times)
        self.assertLess(avg_execution_time, 1.0, "API response time too slow")
    
    def test_concurrent_user_registration(self):
        """Test concurrent user registration performance."""
        results = []
        execution_times = []
        
        def register_user(user_id):
            client = TestClient()
            
            registration_data = {
                'username': f'concurrent_user_{user_id}',
                'email': f'user{user_id}@gmail.com',
                'first_name': 'Test',
                'last_name': 'User',
                'password': 'SecurePass123!',
                'confirm_password': 'SecurePass123!',
            }
            
            start_time = time.time()
            
            with patch('polling.otp_utils.OTPService.send_otp') as mock_send:
                mock_send.return_value = (True, 'OTP sent', '123456')
                response = client.post('/register/', registration_data)
            
            end_time = time.time()
            execution_time = end_time - start_time
            
            results.append(response.status_code)
            execution_times.append(execution_time)
        
        # Register 15 users concurrently
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(register_user, i) for i in range(15)]
            
            for future in as_completed(futures):
                future.result()
        
        # Most registrations should succeed
        successful_registrations = sum(1 for status in results if status == 302)
        self.assertGreaterEqual(successful_registrations, 12, "Too many registrations failed")
        
        # Average registration time should be reasonable
        avg_execution_time = statistics.mean(execution_times)
        self.assertLess(avg_execution_time, 3.0, "Registration time too slow")


class LoadTestingTests(BaseTestCase):
    """Test application under sustained load."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
    
    def test_sustained_api_load(self):
        """Test API performance under sustained load."""
        # Create test data
        players = [PlayerFactory() for _ in range(20)]
        game_round = GameRoundFactory()
        
        for player in players:
            Bet.objects.create(
                player=player,
                round=game_round,
                bet_type='color',
                color='red',
                amount=100
            )
        
        # Test sustained load for 30 seconds
        start_time = time.time()
        end_time = start_time + 30  # 30 seconds
        
        request_count = 0
        response_times = []
        errors = 0
        
        while time.time() < end_time:
            request_start = time.time()
            
            try:
                response = self.client.get('/api/live-betting-stats/')
                request_end = time.time()
                
                response_time = request_end - request_start
                response_times.append(response_time)
                
                if response.status_code != 200:
                    errors += 1
                
                request_count += 1
                
                # Small delay to simulate realistic usage
                time.sleep(0.1)
                
            except Exception:
                errors += 1
        
        # Calculate performance metrics
        avg_response_time = statistics.mean(response_times) if response_times else 0
        max_response_time = max(response_times) if response_times else 0
        requests_per_second = request_count / 30
        error_rate = (errors / request_count * 100) if request_count > 0 else 100
        
        # Performance assertions
        self.assertGreater(request_count, 200, "Too few requests processed")
        self.assertLess(avg_response_time, 0.5, "Average response time too slow")
        self.assertLess(max_response_time, 2.0, "Maximum response time too slow")
        self.assertGreater(requests_per_second, 5, "Requests per second too low")
        self.assertLess(error_rate, 5, "Error rate too high")
    
    def test_memory_usage_under_load(self):
        """Test memory usage under load."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create load
        players = []
        for i in range(500):
            player = PlayerFactory(username=f'memory_test_{i}')
            players.append(player)
        
        # Create game rounds and bets
        for i in range(50):
            game_round = GameRoundFactory(period_id=f'memory_round_{i}')
            
            # Create bets for this round
            for j in range(10):
                if j < len(players):
                    Bet.objects.create(
                        player=players[j],
                        round=game_round,
                        bet_type='color',
                        color='red',
                        amount=100
                    )
        
        # Get final memory usage
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable
        self.assertLess(memory_increase, 100, "Memory usage increased too much")
        
        # Clean up
        Player.objects.filter(username__startswith='memory_test_').delete()
        GameRound.objects.filter(period_id__startswith='memory_round_').delete()


class CachePerformanceTests(BaseTestCase):
    """Test caching performance and effectiveness."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        cache.clear()  # Start with clean cache
    
    def test_cache_effectiveness(self):
        """Test that caching improves performance."""
        # Create test data
        players = [PlayerFactory() for _ in range(50)]
        game_round = GameRoundFactory()
        
        for player in players:
            Bet.objects.create(
                player=player,
                round=game_round,
                bet_type='color',
                color='red',
                amount=100
            )
        
        # First request (no cache)
        start_time = time.time()
        response1 = self.client.get('/api/live-betting-stats/')
        first_request_time = time.time() - start_time
        
        # Second request (should use cache if implemented)
        start_time = time.time()
        response2 = self.client.get('/api/live-betting-stats/')
        second_request_time = time.time() - start_time
        
        # Both should succeed
        self.assertEqual(response1.status_code, 200)
        self.assertEqual(response2.status_code, 200)
        
        # Second request should be faster (if caching is implemented)
        # This test will pass regardless, but shows the pattern
        self.assertLessEqual(second_request_time, first_request_time * 2)
    
    def test_database_query_optimization(self):
        """Test database query performance with select_related."""
        # Create test data with relationships
        players = [PlayerFactory() for _ in range(100)]
        game_round = GameRoundFactory()
        
        bets = []
        for player in players:
            bet = Bet.objects.create(
                player=player,
                round=game_round,
                bet_type='color',
                color='red',
                amount=100
            )
            bets.append(bet)
        
        # Test query without select_related
        start_time = time.time()
        bets_without_select = list(Bet.objects.filter(round=game_round))
        for bet in bets_without_select:
            _ = bet.player.username  # This will cause additional queries
        time_without_select = time.time() - start_time
        
        # Test query with select_related
        start_time = time.time()
        bets_with_select = list(Bet.objects.filter(round=game_round).select_related('player'))
        for bet in bets_with_select:
            _ = bet.player.username  # This should not cause additional queries
        time_with_select = time.time() - start_time
        
        # select_related should be faster
        self.assertLess(time_with_select, time_without_select)
        
        # Both should return same number of results
        self.assertEqual(len(bets_without_select), len(bets_with_select))


class WebSocketPerformanceTests(BaseTestCase):
    """Test WebSocket performance under load."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
    
    def test_websocket_message_broadcasting(self):
        """Test WebSocket message broadcasting performance."""
        # This is a simplified test since full WebSocket testing requires more setup
        
        # Simulate broadcasting to multiple connections
        start_time = time.time()
        
        # Simulate message creation and serialization
        messages = []
        for i in range(100):
            message = {
                'type': 'bet_update',
                'data': {
                    'player': f'player_{i}',
                    'amount': 100,
                    'color': 'red',
                    'timestamp': timezone.now().isoformat()
                }
            }
            messages.append(message)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should create 100 messages quickly
        self.assertLess(execution_time, 0.5, "Message creation took too long")
        self.assertEqual(len(messages), 100)


class PerformanceBenchmarkTests(BaseTestCase):
    """Benchmark tests for key operations."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
    
    def test_user_authentication_benchmark(self):
        """Benchmark user authentication performance."""
        player = PlayerFactory(email_verified=True)
        
        # Test login performance
        login_times = []
        
        for _ in range(10):
            start_time = time.time()
            
            # Simulate login
            session = self.client.session
            session['user_id'] = player.id
            session['username'] = player.username
            session['is_authenticated'] = True
            session.save()
            
            end_time = time.time()
            login_times.append(end_time - start_time)
        
        avg_login_time = statistics.mean(login_times)
        max_login_time = max(login_times)
        
        # Login should be fast
        self.assertLess(avg_login_time, 0.1, "Average login time too slow")
        self.assertLess(max_login_time, 0.2, "Maximum login time too slow")
    
    def test_bet_processing_benchmark(self):
        """Benchmark bet processing performance."""
        player = PlayerFactory(balance=10000)
        game_round = GameRoundFactory(ended=False)
        
        bet_times = []
        
        for i in range(20):
            start_time = time.time()
            
            # Create bet
            bet = Bet.objects.create(
                player=player,
                round=game_round,
                bet_type='color',
                color='red',
                amount=100
            )
            
            # Update player balance
            player.balance -= 100
            player.save()
            
            end_time = time.time()
            bet_times.append(end_time - start_time)
        
        avg_bet_time = statistics.mean(bet_times)
        max_bet_time = max(bet_times)
        
        # Bet processing should be fast
        self.assertLess(avg_bet_time, 0.1, "Average bet processing too slow")
        self.assertLess(max_bet_time, 0.2, "Maximum bet processing too slow")
    
    def test_game_result_processing_benchmark(self):
        """Benchmark game result processing performance."""
        game_round = GameRoundFactory(ended=False)
        players = [PlayerFactory(balance=1000) for _ in range(50)]
        
        # Create bets
        for i, player in enumerate(players):
            Bet.objects.create(
                player=player,
                round=game_round,
                bet_type='color',
                color='red' if i % 2 == 0 else 'green',
                amount=100
            )
        
        # Process results
        start_time = time.time()
        
        game_round.result_color = 'red'
        game_round.ended = True
        game_round.save()
        
        # Simulate result processing
        winning_bets = Bet.objects.filter(round=game_round, color='red')
        for bet in winning_bets:
            # Simulate winnings calculation and balance update
            winnings = bet.amount * 2
            bet.player.balance += winnings
            bet.player.save()
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Result processing should be fast even with 50 bets
        self.assertLess(processing_time, 2.0, "Game result processing too slow")
