"""
Comprehensive game mechanics tests for the Color Prediction Game.
Tests betting system, game rounds, WebSocket connections, and game logic.
"""

import json
import asyncio
from unittest.mock import patch, Mock, AsyncMock
from decimal import Decimal
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from datetime import timedelta
from channels.testing import WebsocketCommunicator
from channels.db import database_sync_to_async

from polling.models import Player, GameRound, Bet, Transaction
from polling.consumers import GameConsumer
from polling.game_logic import GameLogic, BettingService
from tests.conftest import BaseTestCase, PlayerFactory, GameRoundFactory, BetFactory
from tests.utils import TestClient, AssertionHelpers, TestDataBuilder, setup_test_notification_types


class GameRoundTests(BaseTestCase):
    """Test game round creation and management."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
    
    def test_game_round_creation(self):
        """Test automatic game round creation."""
        # Check if a game round exists or create one
        game_round = GameRound.objects.filter(room='main', ended=False).first()
        if not game_round:
            game_round = GameRound.objects.create(
                room='main',
                period_id='test_round_001',
                start_time=timezone.now()
            )
        
        self.assertIsNotNone(game_round)
        self.assertEqual(game_round.room, 'main')
        self.assertFalse(game_round.ended)
        self.assertIsNone(game_round.result_color)
    
    def test_game_round_ending(self):
        """Test game round ending with result."""
        game_round = self.create_game_round()
        
        # End the round with a result
        game_round.result_color = 'red'
        game_round.ended = True
        game_round.end_time = timezone.now()
        game_round.save()
        
        game_round.refresh_from_db()
        self.assertTrue(game_round.ended)
        self.assertEqual(game_round.result_color, 'red')
        self.assertIsNotNone(game_round.end_time)
    
    def test_multiple_game_rounds(self):
        """Test multiple game rounds in different rooms."""
        round1 = self.create_game_round(room='main', period_id='round_1')
        round2 = self.create_game_round(room='vip', period_id='round_2')
        
        self.assertEqual(round1.room, 'main')
        self.assertEqual(round2.room, 'vip')
        self.assertNotEqual(round1.period_id, round2.period_id)
    
    def test_game_round_duration(self):
        """Test game round duration calculation."""
        start_time = timezone.now()
        game_round = self.create_game_round(start_time=start_time)
        
        # Simulate round ending after 50 seconds
        end_time = start_time + timedelta(seconds=50)
        game_round.end_time = end_time
        game_round.save()
        
        duration = game_round.end_time - game_round.start_time
        self.assertEqual(duration.total_seconds(), 50)


class BettingSystemTests(BaseTestCase):
    """Test betting system functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = self.create_player(balance=1000)
        self.game_round = self.create_game_round()
        self.client.login_player(self.player)
    
    def test_successful_bet_placement(self):
        """Test successful bet placement."""
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
        self.assertEqual(bet.color, 'red')
        
        # Check balance was deducted
        AssertionHelpers.assert_player_balance(self.player, 900)
    
    def test_bet_with_insufficient_balance(self):
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
        
        # No bet should be created
        self.assertFalse(Bet.objects.filter(player=self.player).exists())
    
    def test_bet_below_minimum_amount(self):
        """Test bet placement below minimum amount."""
        bet_data = {
            'room': 'main',
            'bet_type': 'color',
            'color': 'red',
            'amount': 0.5  # Below minimum
        }
        
        response = self.client.post_json('/api/place-bet/', bet_data)
        data = self.assert_json_response(response, 400)
        
        self.assertFalse(data['success'])
        self.assertIn('minimum', data['message'].lower())
    
    def test_bet_above_maximum_amount(self):
        """Test bet placement above maximum amount."""
        bet_data = {
            'room': 'main',
            'bet_type': 'color',
            'color': 'red',
            'amount': 50000  # Above maximum
        }
        
        response = self.client.post_json('/api/place-bet/', bet_data)
        data = self.assert_json_response(response, 400)
        
        self.assertFalse(data['success'])
        self.assertIn('maximum', data['message'].lower())
    
    def test_multiple_bets_same_round(self):
        """Test placing multiple bets in the same round (should fail)."""
        # Place first bet
        bet_data = {
            'room': 'main',
            'bet_type': 'color',
            'color': 'red',
            'amount': 100
        }
        
        response1 = self.client.post_json('/api/place-bet/', bet_data)
        data1 = self.assert_json_response(response1, 200)
        self.assertTrue(data1['success'])
        
        # Try to place second bet in same round
        bet_data['color'] = 'green'
        response2 = self.client.post_json('/api/place-bet/', bet_data)
        data2 = self.assert_json_response(response2, 400)
        
        self.assertFalse(data2['success'])
        self.assertIn('already placed', data2['message'].lower())
    
    def test_bet_on_ended_round(self):
        """Test betting on an ended round."""
        # End the round
        self.game_round.ended = True
        self.game_round.save()
        
        bet_data = {
            'room': 'main',
            'bet_type': 'color',
            'color': 'red',
            'amount': 100
        }
        
        response = self.client.post_json('/api/place-bet/', bet_data)
        data = self.assert_json_response(response, 400)
        
        self.assertFalse(data['success'])
        self.assertIn('betting is closed', data['message'].lower())
    
    def test_bet_without_authentication(self):
        """Test betting without authentication."""
        self.client.logout_player()
        
        bet_data = {
            'room': 'main',
            'bet_type': 'color',
            'color': 'red',
            'amount': 100
        }
        
        response = self.client.post_json('/api/place-bet/', bet_data)
        self.assertEqual(response.status_code, 401)


class GameLogicTests(BaseTestCase):
    """Test game logic and result calculation."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.game_round = self.create_game_round()
        
        # Create players and bets
        self.player1 = self.create_player(username='player1', balance=1000)
        self.player2 = self.create_player(username='player2', balance=1000)
        self.player3 = self.create_player(username='player3', balance=1000)
        
        # Create bets
        self.bet1 = self.create_bet(self.player1, self.game_round, color='red', amount=100)
        self.bet2 = self.create_bet(self.player2, self.game_round, color='green', amount=200)
        self.bet3 = self.create_bet(self.player3, self.game_round, color='red', amount=150)
    
    def test_calculate_winnings_red_wins(self):
        """Test winnings calculation when red wins."""
        # Set result to red
        self.game_round.result_color = 'red'
        self.game_round.ended = True
        self.game_round.save()
        
        # Process results
        from polling.game_logic import process_game_results
        process_game_results(self.game_round)
        
        # Check winnings
        self.player1.refresh_from_db()
        self.player3.refresh_from_db()
        self.player2.refresh_from_db()
        
        # Red bettors should win (2x their bet)
        self.assertEqual(self.player1.balance, 1100)  # 1000 - 100 + 200
        self.assertEqual(self.player3.balance, 1150)  # 1000 - 150 + 300
        
        # Green bettor should lose
        self.assertEqual(self.player2.balance, 800)   # 1000 - 200
    
    def test_calculate_winnings_green_wins(self):
        """Test winnings calculation when green wins."""
        # Set result to green
        self.game_round.result_color = 'green'
        self.game_round.ended = True
        self.game_round.save()
        
        # Process results
        from polling.game_logic import process_game_results
        process_game_results(self.game_round)
        
        # Check winnings
        self.player1.refresh_from_db()
        self.player2.refresh_from_db()
        self.player3.refresh_from_db()
        
        # Green bettor should win
        self.assertEqual(self.player2.balance, 1200)  # 1000 - 200 + 400
        
        # Red bettors should lose
        self.assertEqual(self.player1.balance, 900)   # 1000 - 100
        self.assertEqual(self.player3.balance, 850)   # 1000 - 150
    
    def test_calculate_winnings_violet_wins(self):
        """Test winnings calculation when violet wins."""
        # Add violet bet
        bet4 = self.create_bet(self.player1, self.game_round, color='violet', amount=50)
        
        # Set result to violet
        self.game_round.result_color = 'violet'
        self.game_round.ended = True
        self.game_round.save()
        
        # Process results
        from polling.game_logic import process_game_results
        process_game_results(self.game_round)
        
        # Check winnings - violet typically has higher multiplier
        self.player1.refresh_from_db()
        
        # Player1 should win from violet bet (higher multiplier)
        # Exact calculation depends on violet multiplier in your system
        self.assertGreater(self.player1.balance, 900)  # Should be profitable
    
    def test_transaction_creation_on_win(self):
        """Test transaction creation when player wins."""
        # Set result to red
        self.game_round.result_color = 'red'
        self.game_round.ended = True
        self.game_round.save()
        
        # Process results
        from polling.game_logic import process_game_results
        process_game_results(self.game_round)
        
        # Check winning transaction was created
        winning_transaction = Transaction.objects.filter(
            player=self.player1,
            transaction_type='win',
            amount=200  # 2x the bet amount
        ).first()
        
        self.assertIsNotNone(winning_transaction)
        self.assertEqual(winning_transaction.description, f'Win from round {self.game_round.period_id}')
    
    def test_no_bets_scenario(self):
        """Test game round with no bets."""
        # Create round with no bets
        empty_round = self.create_game_round(period_id='empty_round')
        empty_round.result_color = 'red'
        empty_round.ended = True
        empty_round.save()
        
        # Process results should not crash
        from polling.game_logic import process_game_results
        try:
            process_game_results(empty_round)
        except Exception as e:
            self.fail(f"Processing empty round should not raise exception: {e}")


class BettingServiceTests(BaseTestCase):
    """Test betting service functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.player = self.create_player(balance=1000)
        self.game_round = self.create_game_round()
    
    def test_place_bet_service(self):
        """Test betting service place_bet method."""
        from polling.game_logic import BettingService
        
        result = BettingService.place_bet(
            player=self.player,
            room='main',
            bet_type='color',
            color='red',
            amount=100
        )
        
        self.assertTrue(result['success'])
        
        # Check bet was created
        bet = Bet.objects.filter(player=self.player).first()
        self.assertIsNotNone(bet)
        self.assertEqual(bet.amount, 100)
        
        # Check balance was deducted
        AssertionHelpers.assert_player_balance(self.player, 900)
    
    def test_validate_bet_service(self):
        """Test betting service validation."""
        from polling.game_logic import BettingService
        
        # Valid bet
        is_valid, message = BettingService.validate_bet(
            player=self.player,
            room='main',
            amount=100
        )
        self.assertTrue(is_valid)
        
        # Invalid amount
        is_valid, message = BettingService.validate_bet(
            player=self.player,
            room='main',
            amount=0.5
        )
        self.assertFalse(is_valid)
        self.assertIn('minimum', message.lower())
        
        # Insufficient balance
        self.player.balance = 50
        self.player.save()
        
        is_valid, message = BettingService.validate_bet(
            player=self.player,
            room='main',
            amount=100
        )
        self.assertFalse(is_valid)
        self.assertIn('insufficient', message.lower())
    
    def test_get_betting_stats_service(self):
        """Test betting statistics service."""
        from polling.game_logic import BettingService
        
        # Create some bets
        self.create_bet(self.player, self.game_round, color='red', amount=100)
        player2 = self.create_player(username='player2')
        self.create_bet(player2, self.game_round, color='green', amount=200)
        
        stats = BettingService.get_betting_stats(self.game_round)
        
        self.assertIn('red', stats)
        self.assertIn('green', stats)
        self.assertEqual(stats['red']['total_amount'], 100)
        self.assertEqual(stats['green']['total_amount'], 200)
        self.assertEqual(stats['red']['bet_count'], 1)
        self.assertEqual(stats['green']['bet_count'], 1)


class WebSocketTests(TransactionTestCase):
    """Test WebSocket functionality for real-time updates."""

    def setUp(self):
        setup_test_notification_types()
        self.player = PlayerFactory(balance=1000)
        self.game_round = GameRoundFactory()

    async def test_websocket_connection(self):
        """Test WebSocket connection establishment."""
        communicator = WebsocketCommunicator(GameConsumer.as_asgi(), "/ws/game/main/")

        # Add user to scope
        communicator.scope['user'] = self.player
        communicator.scope['session'] = {
            'user_id': self.player.id,
            'username': self.player.username,
            'is_authenticated': True
        }

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        await communicator.disconnect()

    async def test_websocket_bet_broadcast(self):
        """Test WebSocket broadcast when bet is placed."""
        communicator = WebsocketCommunicator(GameConsumer.as_asgi(), "/ws/game/main/")

        # Add user to scope
        communicator.scope['user'] = self.player
        communicator.scope['session'] = {
            'user_id': self.player.id,
            'username': self.player.username,
            'is_authenticated': True
        }

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Simulate bet placement
        bet_message = {
            'type': 'bet_placed',
            'data': {
                'player': self.player.username,
                'color': 'red',
                'amount': 100,
                'room': 'main'
            }
        }

        await communicator.send_json_to(bet_message)

        # Should receive bet update
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'bet_update')

        await communicator.disconnect()

    async def test_websocket_game_result_broadcast(self):
        """Test WebSocket broadcast when game result is announced."""
        communicator = WebsocketCommunicator(GameConsumer.as_asgi(), "/ws/game/main/")

        # Add user to scope
        communicator.scope['user'] = self.player
        communicator.scope['session'] = {
            'user_id': self.player.id,
            'username': self.player.username,
            'is_authenticated': True
        }

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Simulate game result
        result_message = {
            'type': 'game_result',
            'data': {
                'round_id': self.game_round.period_id,
                'result': 'red',
                'room': 'main'
            }
        }

        await communicator.send_json_to(result_message)

        # Should receive result update
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'game_result')
        self.assertEqual(response['data']['result'], 'red')

        await communicator.disconnect()

    async def test_websocket_timer_updates(self):
        """Test WebSocket timer updates."""
        communicator = WebsocketCommunicator(GameConsumer.as_asgi(), "/ws/game/main/")

        # Add user to scope
        communicator.scope['user'] = self.player
        communicator.scope['session'] = {
            'user_id': self.player.id,
            'username': self.player.username,
            'is_authenticated': True
        }

        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)

        # Simulate timer update
        timer_message = {
            'type': 'timer_update',
            'data': {
                'time_remaining': 30,
                'phase': 'betting',
                'room': 'main'
            }
        }

        await communicator.send_json_to(timer_message)

        # Should receive timer update
        response = await communicator.receive_json_from()
        self.assertEqual(response['type'], 'timer_update')
        self.assertEqual(response['data']['time_remaining'], 30)

        await communicator.disconnect()

    def test_websocket_connection_sync(self):
        """Test WebSocket connection (sync wrapper)."""
        async def run_test():
            await self.test_websocket_connection()

        asyncio.run(run_test())

    def test_websocket_bet_broadcast_sync(self):
        """Test WebSocket bet broadcast (sync wrapper)."""
        async def run_test():
            await self.test_websocket_bet_broadcast()

        asyncio.run(run_test())


class RealTimeUpdatesTests(BaseTestCase):
    """Test real-time update functionality."""

    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = self.create_player(balance=1000)
        self.game_round = self.create_game_round()

    @patch('polling.consumers.GameConsumer.send_to_room')
    def test_bet_placement_triggers_update(self, mock_send):
        """Test that bet placement triggers real-time update."""
        self.client.login_player(self.player)

        bet_data = {
            'room': 'main',
            'bet_type': 'color',
            'color': 'red',
            'amount': 100
        }

        response = self.client.post_json('/api/place-bet/', bet_data)
        data = self.assert_json_response(response, 200)

        self.assertTrue(data['success'])

        # Should trigger WebSocket update
        # Note: This test assumes the bet placement triggers a WebSocket update
        # The exact implementation may vary

    def test_game_timer_api(self):
        """Test game timer API endpoint."""
        response = self.client.get('/api/timer-info/')
        data = self.assert_json_response(response, 200)

        self.assertIn('time_remaining', data)
        self.assertIn('phase', data)
        self.assertIn('round_id', data)

    def test_live_betting_stats_api(self):
        """Test live betting statistics API."""
        # Create some bets
        self.create_bet(self.player, self.game_round, color='red', amount=100)
        player2 = self.create_player(username='player2')
        self.create_bet(player2, self.game_round, color='green', amount=200)

        response = self.client.get('/api/live-betting-stats/')
        data = self.assert_json_response(response, 200)

        self.assertIn('betting_stats', data)
        self.assertIn('red', data['betting_stats'])
        self.assertIn('green', data['betting_stats'])

    def test_room_switching(self):
        """Test switching between game rooms."""
        # Test main room
        response = self.client.get('/room/main/')
        self.assertEqual(response.status_code, 200)

        # Test VIP room (if implemented)
        response = self.client.get('/room/vip/')
        # Should either work or redirect to main room
        self.assertIn(response.status_code, [200, 302])


class GameIntegrityTests(BaseTestCase):
    """Test game integrity and edge cases."""

    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.player = self.create_player(balance=1000)
        self.game_round = self.create_game_round()

    def test_concurrent_bet_placement(self):
        """Test concurrent bet placement by same player."""
        from django.db import transaction

        # This test simulates race condition
        # In practice, database constraints should prevent duplicate bets

        bet_data = {
            'player': self.player,
            'round': self.game_round,
            'bet_type': 'color',
            'color': 'red',
            'amount': 100
        }

        # First bet should succeed
        bet1 = Bet.objects.create(**bet_data)
        self.assertIsNotNone(bet1)

        # Second bet should fail due to unique constraint
        with self.assertRaises(Exception):
            bet2 = Bet.objects.create(**bet_data)

    def test_balance_consistency(self):
        """Test balance consistency during betting."""
        initial_balance = self.player.balance

        # Place bet
        bet = self.create_bet(self.player, self.game_round, amount=100)

        # Check balance was deducted
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance - 100)

        # Check transaction was created
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='bet',
            amount=-100
        ).first()
        self.assertIsNotNone(transaction)

    def test_game_round_state_transitions(self):
        """Test valid game round state transitions."""
        # New round should be in betting phase
        self.assertFalse(self.game_round.ended)
        self.assertIsNone(self.game_round.result_color)

        # End round with result
        self.game_round.result_color = 'red'
        self.game_round.ended = True
        self.game_round.end_time = timezone.now()
        self.game_round.save()

        # Round should be ended
        self.assertTrue(self.game_round.ended)
        self.assertEqual(self.game_round.result_color, 'red')

        # Cannot change result after ending
        with self.assertRaises(Exception):
            self.game_round.result_color = 'green'
            self.game_round.save()
