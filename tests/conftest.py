"""
Test configuration and fixtures for the Color Prediction Game test suite.
This file contains test utilities and simple factories used across all test modules.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal

from polling.models import (
    Player, Admin, GameRound, Bet, Transaction,
    MasterWalletTransaction, NotificationType, OTPVerification
)


# Simple factory functions for creating test instances

_player_counter = 0
_admin_counter = 0
_round_counter = 0

def PlayerFactory(**kwargs):
    """Factory function for creating test Player instances."""
    global _player_counter
    _player_counter += 1

    defaults = {
        'username': f'testuser{_player_counter}',
        'email': f'testuser{_player_counter}@example.com',
        'first_name': 'Test',
        'last_name': 'User',
        'password_hash': 'hashed_password',
        'balance': 1000,
        'is_active': True,
        'email_verified': True,
    }
    defaults.update(kwargs)
    return Player.objects.create(**defaults)


def AdminFactory(**kwargs):
    """Factory function for creating test Admin instances."""
    global _admin_counter
    _admin_counter += 1

    defaults = {
        'username': f'admin{_admin_counter}',
        'password_hash': 'hashed_password',
        'is_active': True,
    }
    defaults.update(kwargs)
    return Admin.objects.create(**defaults)


def GameRoundFactory(**kwargs):
    """Factory function for creating test GameRound instances."""
    global _round_counter
    _round_counter += 1

    defaults = {
        'room': 'main',
        'period_id': f'round_{_round_counter}',
        'start_time': timezone.now(),
        'game_type': 'parity',
        'ended': False,
    }
    defaults.update(kwargs)
    return GameRound.objects.create(**defaults)


def BetFactory(**kwargs):
    """Factory function for creating test Bet instances."""
    defaults = {
        'bet_type': 'color',
        'color': 'red',
        'amount': 100,
    }

    # Create player and round if not provided
    if 'player' not in kwargs:
        defaults['player'] = PlayerFactory()
    if 'round' not in kwargs:
        defaults['round'] = GameRoundFactory()

    defaults.update(kwargs)
    return Bet.objects.create(**defaults)


def TransactionFactory(**kwargs):
    """Factory function for creating test Transaction instances."""
    defaults = {
        'transaction_type': 'deposit',
        'amount': 100,
        'balance_before': 1000,
        'balance_after': 1100,
        'description': 'Test transaction',
    }

    # Create player if not provided
    if 'player' not in kwargs:
        defaults['player'] = PlayerFactory()

    defaults.update(kwargs)
    return Transaction.objects.create(**defaults)


def NotificationTypeFactory(**kwargs):
    """Factory function for creating test NotificationType instances."""
    defaults = {
        'name': f'test_notification_{timezone.now().timestamp()}',
        'category': 'game',
        'description': 'Test notification type',
        'is_active': True,
        'default_enabled': True,
    }
    defaults.update(kwargs)
    return NotificationType.objects.create(**defaults)


# Django test utilities (no pytest fixtures needed)


class BaseTestCase(TestCase):
    """Base test case with common utilities for all tests."""
    
    def setUp(self):
        """Set up test data."""
        self.client = Client()
        
        # Create notification types
        self.notification_types = [
            NotificationTypeFactory(name='account_activity'),
            NotificationTypeFactory(name='wallet_transaction'),
            NotificationTypeFactory(name='game_result'),
            NotificationTypeFactory(name='security_alert'),
        ]
    
    def create_player(self, **kwargs):
        """Create a test player with default values."""
        defaults = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'balance': 1000,
            'is_active': True,
            'email_verified': True,
        }
        defaults.update(kwargs)
        return PlayerFactory(**defaults)
    
    def create_admin(self, **kwargs):
        """Create a test admin with default values."""
        defaults = {
            'username': 'testadmin',
            'is_active': True,
        }
        defaults.update(kwargs)
        return AdminFactory(**defaults)
    
    def create_game_round(self, **kwargs):
        """Create a test game round with default values."""
        defaults = {
            'room': 'main',
            'period_id': 'test_round',
            'start_time': timezone.now(),
        }
        defaults.update(kwargs)
        return GameRoundFactory(**defaults)
    
    def authenticate_player(self, player):
        """Authenticate a player in the test client."""
        session = self.client.session
        session['user_id'] = player.id
        session['username'] = player.username
        session['is_authenticated'] = True
        session.save()
    
    def authenticate_admin(self, admin):
        """Authenticate an admin in the test client."""
        session = self.client.session
        session['admin_id'] = admin.id
        session['admin_username'] = admin.username
        session['is_admin_authenticated'] = True
        session.save()
    
    def assert_redirects_to_login(self, response):
        """Assert that response redirects to login page."""
        self.assertIn(response.status_code, [302, 401])
    
    def assert_json_response(self, response, expected_status=200):
        """Assert that response is valid JSON with expected status."""
        self.assertEqual(response.status_code, expected_status)
        self.assertEqual(response['Content-Type'], 'application/json')
        return response.json()
    
    def create_bet(self, player=None, game_round=None, **kwargs):
        """Create a test bet."""
        if not player:
            player = self.create_player()
        if not game_round:
            game_round = self.create_game_round()
        
        defaults = {
            'player': player,
            'round': game_round,
            'bet_type': 'color',
            'color': 'red',
            'amount': 100,
        }
        defaults.update(kwargs)
        return BetFactory(**defaults)
    
    def create_transaction(self, player=None, **kwargs):
        """Create a test transaction."""
        if not player:
            player = self.create_player()
        
        defaults = {
            'player': player,
            'transaction_type': 'deposit',
            'amount': 100,
            'balance_before': player.balance,
            'balance_after': player.balance + 100,
            'description': 'Test transaction',
        }
        defaults.update(kwargs)
        return TransactionFactory(**defaults)


class TestDataMixin:
    """Mixin providing common test data creation methods."""
    
    @classmethod
    def setUpTestData(cls):
        """Set up test data that can be shared across test methods."""
        # Create notification types
        cls.notification_types = [
            NotificationTypeFactory(name='account_activity'),
            NotificationTypeFactory(name='wallet_transaction'),
            NotificationTypeFactory(name='game_result'),
            NotificationTypeFactory(name='security_alert'),
        ]
    
    def create_test_scenario(self):
        """Create a complete test scenario with players, rounds, and bets."""
        # Create players
        self.player1 = PlayerFactory(username='player1', balance=1000)
        self.player2 = PlayerFactory(username='player2', balance=2000)
        
        # Create admin
        self.admin = AdminFactory(username='testadmin')
        
        # Create game round
        self.game_round = GameRoundFactory(
            room='main',
            period_id='test_scenario_round'
        )
        
        # Create bets
        self.bet1 = BetFactory(
            player=self.player1,
            round=self.game_round,
            color='red',
            amount=100
        )
        self.bet2 = BetFactory(
            player=self.player2,
            round=self.game_round,
            color='green',
            amount=200
        )
        
        return {
            'players': [self.player1, self.player2],
            'admin': self.admin,
            'game_round': self.game_round,
            'bets': [self.bet1, self.bet2],
        }
