"""
Test utilities and helper functions for the Color Prediction Game test suite.
"""

import json
import time
from decimal import Decimal
from unittest.mock import Mock, patch
from django.test import Client
from django.utils import timezone
from django.core import mail
from datetime import timedelta

from polling.models import Player, Admin, GameRound, Bet, Transaction


class TestClient(Client):
    """Extended test client with additional helper methods."""
    
    def login_player(self, player):
        """Login a player and return success status."""
        session = self.session
        session['user_id'] = player.id
        session['username'] = player.username
        session['is_authenticated'] = True
        session.save()
        return True
    
    def login_admin(self, admin):
        """Login an admin and return success status."""
        session = self.session
        session['admin_id'] = admin.id
        session['admin_username'] = admin.username
        session['is_admin_authenticated'] = True
        session.save()
        return True
    
    def logout_player(self):
        """Logout current player."""
        session = self.session
        session.pop('user_id', None)
        session.pop('username', None)
        session.pop('is_authenticated', None)
        session.save()
    
    def logout_admin(self):
        """Logout current admin."""
        session = self.session
        session.pop('admin_id', None)
        session.pop('admin_username', None)
        session.pop('is_admin_authenticated', None)
        session.save()
    
    def post_json(self, path, data, **extra):
        """POST JSON data to a URL."""
        return self.post(
            path,
            json.dumps(data),
            content_type='application/json',
            **extra
        )
    
    def assert_json_response(self, response, expected_status=200):
        """Assert response is JSON with expected status."""
        assert response.status_code == expected_status
        assert 'application/json' in response.get('Content-Type', '')
        return response.json()


class MockWebSocketConsumer:
    """Mock WebSocket consumer for testing."""
    
    def __init__(self):
        self.messages = []
        self.connected = False
        self.groups = []
    
    async def connect(self):
        self.connected = True
    
    async def disconnect(self, close_code):
        self.connected = False
    
    async def send(self, text_data):
        self.messages.append(json.loads(text_data))
    
    async def group_add(self, group_name, channel_name):
        if group_name not in self.groups:
            self.groups.append(group_name)
    
    async def group_discard(self, group_name, channel_name):
        if group_name in self.groups:
            self.groups.remove(group_name)


class TestDataBuilder:
    """Builder pattern for creating complex test data scenarios."""
    
    def __init__(self):
        self.players = []
        self.admins = []
        self.game_rounds = []
        self.bets = []
        self.transactions = []
    
    def with_players(self, count=1, **kwargs):
        """Add players to the test scenario."""
        from tests.conftest import PlayerFactory
        for i in range(count):
            player_kwargs = kwargs.copy()
            if 'username' not in player_kwargs:
                player_kwargs['username'] = f'player{i+1}'
            player = PlayerFactory(**player_kwargs)
            self.players.append(player)
        return self
    
    def with_admins(self, count=1, **kwargs):
        """Add admins to the test scenario."""
        from tests.conftest import AdminFactory
        for i in range(count):
            admin_kwargs = kwargs.copy()
            if 'username' not in admin_kwargs:
                admin_kwargs['username'] = f'admin{i+1}'
            admin = AdminFactory(**admin_kwargs)
            self.admins.append(admin)
        return self
    
    def with_game_rounds(self, count=1, **kwargs):
        """Add game rounds to the test scenario."""
        from tests.conftest import GameRoundFactory
        for i in range(count):
            round_kwargs = kwargs.copy()
            if 'period_id' not in round_kwargs:
                round_kwargs['period_id'] = f'round_{i+1}'
            game_round = GameRoundFactory(**round_kwargs)
            self.game_rounds.append(game_round)
        return self
    
    def with_bets(self, player_index=0, round_index=0, count=1, **kwargs):
        """Add bets to the test scenario."""
        from tests.conftest import BetFactory
        player = self.players[player_index] if self.players else None
        game_round = self.game_rounds[round_index] if self.game_rounds else None
        
        for i in range(count):
            bet_kwargs = kwargs.copy()
            if player:
                bet_kwargs['player'] = player
            if game_round:
                bet_kwargs['round'] = game_round
            bet = BetFactory(**bet_kwargs)
            self.bets.append(bet)
        return self
    
    def with_transactions(self, player_index=0, count=1, **kwargs):
        """Add transactions to the test scenario."""
        from tests.conftest import TransactionFactory
        player = self.players[player_index] if self.players else None
        
        for i in range(count):
            transaction_kwargs = kwargs.copy()
            if player:
                transaction_kwargs['player'] = player
            transaction = TransactionFactory(**transaction_kwargs)
            self.transactions.append(transaction)
        return self
    
    def build(self):
        """Return the built test scenario."""
        return {
            'players': self.players,
            'admins': self.admins,
            'game_rounds': self.game_rounds,
            'bets': self.bets,
            'transactions': self.transactions,
        }


class AssertionHelpers:
    """Helper methods for common test assertions."""
    
    @staticmethod
    def assert_player_balance(player, expected_balance):
        """Assert player has expected balance."""
        player.refresh_from_db()
        assert player.balance == expected_balance, f"Expected balance {expected_balance}, got {player.balance}"
    
    @staticmethod
    def assert_transaction_created(player, transaction_type, amount):
        """Assert a transaction was created for the player."""
        transaction = Transaction.objects.filter(
            player=player,
            transaction_type=transaction_type,
            amount=amount
        ).first()
        assert transaction is not None, f"No {transaction_type} transaction found for {amount}"
        return transaction
    
    @staticmethod
    def assert_bet_created(player, game_round, amount):
        """Assert a bet was created."""
        bet = Bet.objects.filter(
            player=player,
            round=game_round,
            amount=amount
        ).first()
        assert bet is not None, f"No bet found for player {player.username} in round {game_round.period_id}"
        return bet
    
    @staticmethod
    def assert_email_sent(subject_contains=None, to_email=None):
        """Assert an email was sent."""
        assert len(mail.outbox) > 0, "No emails were sent"
        
        if subject_contains:
            found = any(subject_contains in email.subject for email in mail.outbox)
            assert found, f"No email found with subject containing '{subject_contains}'"
        
        if to_email:
            found = any(to_email in email.to for email in mail.outbox)
            assert found, f"No email found sent to '{to_email}'"
    
    @staticmethod
    def assert_game_round_ended(game_round, expected_result=None):
        """Assert a game round has ended with expected result."""
        game_round.refresh_from_db()
        assert game_round.ended, f"Game round {game_round.period_id} has not ended"
        
        if expected_result:
            assert game_round.result_color == expected_result, \
                f"Expected result {expected_result}, got {game_round.result_color}"


class MockServices:
    """Mock external services for testing."""
    
    @staticmethod
    def mock_razorpay_success():
        """Mock successful Razorpay payment."""
        return patch('polling.payment_service.razorpay.Order.create', return_value={
            'id': 'order_test123',
            'amount': 10000,
            'currency': 'INR',
            'status': 'created'
        })
    
    @staticmethod
    def mock_razorpay_failure():
        """Mock failed Razorpay payment."""
        return patch('polling.payment_service.razorpay.Order.create', 
                    side_effect=Exception('Payment failed'))
    
    @staticmethod
    def mock_email_service():
        """Mock email service."""
        return patch('polling.email_service.EmailService.send_email_with_rotation', 
                    return_value=True)
    
    @staticmethod
    def mock_fraud_detection(risk_score=25):
        """Mock fraud detection service."""
        return patch('polling.fraud_detection.FraudDetectionService.calculate_fraud_score',
                    return_value=(risk_score, ['test_factor']))


class PerformanceTestHelpers:
    """Helpers for performance testing."""
    
    @staticmethod
    def time_function(func, *args, **kwargs):
        """Time the execution of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    @staticmethod
    def assert_response_time(response_time, max_time):
        """Assert response time is within acceptable limits."""
        assert response_time <= max_time, \
            f"Response time {response_time:.3f}s exceeded maximum {max_time}s"
    
    @staticmethod
    def create_load_test_data(players_count=100, rounds_count=10):
        """Create data for load testing."""
        from tests.conftest import PlayerFactory, GameRoundFactory
        
        players = [PlayerFactory() for _ in range(players_count)]
        rounds = [GameRoundFactory() for _ in range(rounds_count)]
        
        return players, rounds


class SecurityTestHelpers:
    """Helpers for security testing."""
    
    @staticmethod
    def get_csrf_token(client, url='/'):
        """Get CSRF token from a page."""
        response = client.get(url)
        return response.cookies.get('csrftoken', {}).value
    
    @staticmethod
    def test_sql_injection_payload():
        """Return common SQL injection payloads."""
        return [
            "'; DROP TABLE polling_player; --",
            "' OR '1'='1",
            "'; SELECT * FROM polling_player; --",
            "' UNION SELECT * FROM polling_admin; --"
        ]
    
    @staticmethod
    def test_xss_payload():
        """Return common XSS payloads."""
        return [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "';alert('xss');//"
        ]
    
    @staticmethod
    def test_path_traversal_payload():
        """Return path traversal payloads."""
        return [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32\\config\\sam",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd"
        ]


# Global test utilities
def clear_test_data():
    """Clear all test data from database."""
    models_to_clear = [Bet, Transaction, GameRound, Player, Admin]
    for model in models_to_clear:
        model.objects.all().delete()


def setup_test_notification_types():
    """Set up notification types for tests."""
    from polling.models import NotificationType
    
    types = [
        ('account_activity', 'account'),
        ('wallet_transaction', 'wallet'),
        ('game_result', 'game'),
        ('security_alert', 'security'),
    ]
    
    for name, category in types:
        NotificationType.objects.get_or_create(
            name=name,
            defaults={
                'category': category,
                'description': f'Test {name}',
                'is_active': True,
                'default_enabled': True,
            }
        )
