"""
Comprehensive test suite for critical security fixes
Run with: python manage.py test tests.test_critical_fixes
"""
import asyncio
import time
import json
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.utils import timezone
from unittest.mock import patch, MagicMock
from channels.testing import WebsocketCommunicator
from channels.routing import URLRouter
from channels.auth import AuthMiddlewareStack

from polling.models import Player, GameRound, Bet, Transaction
from polling.secure_random import secure_random
from polling.websocket_reliability import reliable_ws_manager
from polling.timer_sync import server_timer
from polling.error_recovery import error_recovery
from polling.responsible_gambling import responsible_gambling, BettingLimits
from polling.monitoring import monitoring
from polling.consumers import GameConsumer


class SecureRandomizationTests(TestCase):
    """Test cryptographically secure randomization"""
    
    def test_secure_number_generation(self):
        """Test that secure random numbers are unpredictable"""
        round_id = "test_round_001"
        
        # Generate multiple numbers
        numbers = []
        hashes = []
        for i in range(100):
            number, hash_val = secure_random.generate_secure_number(f"{round_id}_{i}", 0, 9)
            numbers.append(number)
            hashes.append(hash_val)
        
        # Check that numbers are in valid range
        self.assertTrue(all(0 <= n <= 9 for n in numbers))
        
        # Check that hashes are unique (very high probability)
        self.assertEqual(len(set(hashes)), len(hashes))
        
        # Check distribution (should be roughly uniform)
        distribution = [numbers.count(i) for i in range(10)]
        # No number should appear more than 20 times in 100 generations (very loose check)
        self.assertTrue(all(count <= 20 for count in distribution))
    
    def test_color_number_mapping(self):
        """Test color to number mapping consistency"""
        test_cases = [
            ('green', [1, 3, 7, 9]),
            ('red', [2, 8]),
            ('violet', [0, 5]),
            ('blue', [4, 6])
        ]
        
        for color, expected_numbers in test_cases:
            for _ in range(10):  # Test multiple times
                number, _ = secure_random.generate_number_for_color("test", color)
                self.assertIn(number, expected_numbers)
    
    def test_minimum_bet_color_selection(self):
        """Test minimum bet color selection logic"""
        bet_stats = {
            'red': {'total_amount': 1000, 'total_count': 5},
            'green': {'total_amount': 500, 'total_count': 3},  # Minimum
            'violet': {'total_amount': 1500, 'total_count': 8},
            'blue': {'total_amount': 800, 'total_count': 4}
        }
        
        color, number, hash_val = secure_random.select_minimum_bet_color("test", bet_stats)
        self.assertEqual(color, 'green')
        self.assertIn(number, [1, 3, 7, 9])
        self.assertIsInstance(hash_val, str)


class WebSocketReliabilityTests(TestCase):
    """Test WebSocket message reliability"""
    
    def setUp(self):
        self.reliable_manager = reliable_ws_manager
    
    def test_message_acknowledgment(self):
        """Test message acknowledgment system"""
        # Send a reliable message
        message_id = asyncio.run(self.reliable_manager.send_reliable_message(
            "test_group",
            {"type": "test_message", "data": "test"},
            critical=True
        ))
        
        # Check that message is pending
        self.assertIn(message_id, self.reliable_manager.pending_messages)
        
        # Acknowledge the message
        asyncio.run(self.reliable_manager.acknowledge_message(message_id))
        
        # Check that message is no longer pending
        self.assertNotIn(message_id, self.reliable_manager.pending_messages)
    
    def test_reliability_stats(self):
        """Test reliability statistics"""
        stats = self.reliable_manager.get_stats()
        
        required_keys = ['total_pending', 'overdue_messages', 'critical_messages']
        for key in required_keys:
            self.assertIn(key, stats)
            self.assertIsInstance(stats[key], int)


class TimerSynchronizationTests(TestCase):
    """Test server-authoritative timer synchronization"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.player = Player.objects.create(user=self.user, username='testuser')
        self.game_round = GameRound.objects.create(room='main')
    
    def test_bet_timing_validation(self):
        """Test server-side bet timing validation"""
        # Start timer
        asyncio.run(server_timer.start_round_timer('main', self.game_round))
        
        # Test valid timing
        is_valid, reason = server_timer.validate_bet_timing('main')
        self.assertTrue(is_valid)
        
        # Test with client timestamp
        current_time = time.time()
        is_valid, reason = server_timer.validate_bet_timing('main', current_time)
        self.assertTrue(is_valid)
        
        # Test with old client timestamp (should fail)
        old_time = current_time - 10  # 10 seconds ago
        is_valid, reason = server_timer.validate_bet_timing('main', old_time)
        self.assertFalse(is_valid)
    
    def test_timer_sync_data(self):
        """Test timer synchronization data"""
        asyncio.run(server_timer.start_round_timer('main', self.game_round))
        
        sync_data = server_timer.get_sync_data('main')
        
        required_keys = ['server_time', 'time_remaining', 'phase', 'round_active']
        for key in required_keys:
            self.assertIn(key, sync_data)


class AtomicOperationsTests(TransactionTestCase):
    """Test atomic database operations"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.player = Player.objects.create(user=self.user, username='testuser', balance=10000)
        self.game_round = GameRound.objects.create(room='main')
    
    def test_atomic_bet_placement(self):
        """Test that bet placement is atomic"""
        from polling.wallet_utils import place_bet_with_wallet
        
        initial_balance = self.player.balance
        bet_amount = 1000
        
        # Place bet
        success, bet, error = place_bet_with_wallet(
            self.player, self.game_round, 'color', 'red', None, bet_amount
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(bet)
        
        # Check that balance was debited
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance - bet_amount)
        
        # Check that transaction was created
        transaction = Transaction.objects.filter(player=self.player, bet=bet).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, bet_amount)
        self.assertEqual(transaction.transaction_type, 'bet')
    
    def test_duplicate_bet_prevention(self):
        """Test that duplicate bets are prevented"""
        from polling.wallet_utils import place_bet_with_wallet
        
        # Place first bet
        success1, bet1, error1 = place_bet_with_wallet(
            self.player, self.game_round, 'color', 'red', None, 1000
        )
        self.assertTrue(success1)
        
        # Try to place second bet (should fail)
        success2, bet2, error2 = place_bet_with_wallet(
            self.player, self.game_round, 'color', 'green', None, 1000
        )
        self.assertFalse(success2)
        self.assertIsNone(bet2)
        self.assertIn("one bet per round", error2)


class ResponsibleGamblingTests(TestCase):
    """Test responsible gambling features"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.player = Player.objects.create(user=self.user, username='testuser', balance=50000)
        self.player_id = str(self.player.id)
    
    def test_betting_limits_validation(self):
        """Test betting limits enforcement"""
        # Set custom limits
        limits = BettingLimits(
            daily_loss_limit=5000,  # $50
            session_loss_limit=2000,  # $20
            max_bet_amount=1000  # $10
        )
        responsible_gambling.set_player_limits(self.player_id, limits)
        
        # Test bet amount validation
        is_valid, reason = asyncio.run(responsible_gambling.validate_bet(self.player_id, 500))
        self.assertTrue(is_valid)
        
        # Test bet amount too high
        is_valid, reason = asyncio.run(responsible_gambling.validate_bet(self.player_id, 1500))
        self.assertFalse(is_valid)
        self.assertIn("Maximum bet amount", reason)
    
    def test_session_management(self):
        """Test gambling session management"""
        # Start session
        session_started = asyncio.run(responsible_gambling.start_session(self.player_id))
        self.assertTrue(session_started)
        
        # Check session stats
        stats = responsible_gambling.get_session_stats(self.player_id)
        self.assertTrue(stats['active'])
        self.assertGreater(stats['session_duration'], 0)
    
    def test_cooling_off_period(self):
        """Test cooling-off period functionality"""
        # Trigger cooling-off
        asyncio.run(responsible_gambling.force_cooling_off(self.player_id, 1))  # 1 hour
        
        # Try to validate bet (should fail)
        is_valid, reason = asyncio.run(responsible_gambling.validate_bet(self.player_id, 500))
        self.assertFalse(is_valid)
        self.assertIn("Cooling-off period", reason)


class ErrorRecoveryTests(TestCase):
    """Test error recovery system"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.player = Player.objects.create(user=self.user, username='testuser')
    
    def test_stuck_round_detection(self):
        """Test stuck round detection"""
        # Create an old round that should be detected as stuck
        old_time = timezone.now() - timezone.timedelta(minutes=15)
        stuck_round = GameRound.objects.create(
            room='main',
            start_time=old_time,
            ended=False
        )
        
        # Manually trigger stuck round check
        asyncio.run(error_recovery._check_stuck_rounds())
        
        # Check if recovery action was created
        recovery_id = f"stuck_round_{stuck_round.id}"
        self.assertIn(recovery_id, error_recovery.pending_recoveries)
    
    def test_recovery_stats(self):
        """Test recovery system statistics"""
        stats = error_recovery.get_recovery_stats()
        
        required_keys = ['pending_recoveries', 'critical_recoveries', 'recovery_task_running']
        for key in required_keys:
            self.assertIn(key, stats)


class MonitoringTests(TestCase):
    """Test monitoring and alerting system"""
    
    def test_performance_tracking(self):
        """Test performance metrics tracking"""
        # Record some requests
        monitoring.record_request(True, 0.5)  # Successful request
        monitoring.record_request(False, 2.0)  # Failed request
        
        # Record WebSocket events
        monitoring.record_websocket_event('connect')
        monitoring.record_websocket_event('disconnect')
        
        # Get dashboard data
        dashboard_data = monitoring.get_dashboard_data()
        
        self.assertIn('system_status', dashboard_data)
        self.assertIn('performance_counters', dashboard_data)
        self.assertIn('alert_summary', dashboard_data)
    
    def test_alert_creation(self):
        """Test alert creation and resolution"""
        # Create a test alert
        asyncio.run(monitoring._create_alert(
            'test_alert',
            'high',
            'test',
            'Test Alert',
            'This is a test alert'
        ))
        
        # Check that alert was created
        self.assertIn('test_alert', monitoring.active_alerts)
        
        # Resolve the alert
        monitoring.resolve_alert('test_alert')
        
        # Check that alert was resolved
        alert = monitoring.active_alerts['test_alert']
        self.assertTrue(alert.resolved)


class IntegrationTests(TransactionTestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.player = Player.objects.create(user=self.user, username='testuser', balance=10000)
    
    def test_complete_betting_flow(self):
        """Test complete betting flow with all security measures"""
        # Create game round
        game_round = GameRound.objects.create(room='main')
        
        # Start timer
        asyncio.run(server_timer.start_round_timer('main', game_round))
        
        # Start gambling session
        asyncio.run(responsible_gambling.start_session(str(self.player.id)))
        
        # Validate bet timing and limits
        timing_valid, timing_reason = server_timer.validate_bet_timing('main')
        self.assertTrue(timing_valid)
        
        gambling_valid, gambling_reason = asyncio.run(
            responsible_gambling.validate_bet(str(self.player.id), 1000)
        )
        self.assertTrue(gambling_valid)
        
        # Place bet with all validations
        from polling.wallet_utils import place_bet_with_wallet
        success, bet, error = place_bet_with_wallet(
            self.player, game_round, 'color', 'red', None, 1000
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(bet)
        
        # Record bet for responsible gambling
        asyncio.run(responsible_gambling.record_bet(
            str(self.player.id), 1000, False, 0  # Lost bet
        ))
        
        # Check that all systems recorded the bet
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 9000)  # 10000 - 1000
        
        # Check transaction was created
        transaction = Transaction.objects.filter(player=self.player, bet=bet).first()
        self.assertIsNotNone(transaction)


if __name__ == '__main__':
    import django
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
    django.setup()
    
    from django.test.utils import get_runner
    from django.conf import settings
    
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(["tests.test_critical_fixes"])
