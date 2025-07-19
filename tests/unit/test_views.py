# Test cases for Color Prediction Game views

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from unittest.mock import patch, Mock
import json

from .models import Player, GameRound, Bet, Admin
from .security import InputValidator


class ViewsTestCase(TestCase):
    """Test cases for main views"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000
        )
        self.admin = Admin.objects.create(
            username='admin',
            is_active=True
        )
        self.game_round = GameRound.objects.create(
            room='test_room',
            game_type='parity'
        )
    
    def create_authenticated_session(self, user_id):
        """Helper to create authenticated session"""
        session = self.client.session
        session['is_authenticated'] = True
        session['user_id'] = user_id
        session.save()
    
    def test_index_view_unauthenticated(self):
        """Test index view for unauthenticated user"""
        response = self.client.get(reverse('index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Color Prediction Game')
        self.assertFalse(response.context['is_authenticated'])
        self.assertIsNone(response.context['current_user'])
    
    def test_index_view_authenticated(self):
        """Test index view for authenticated user"""
        self.create_authenticated_session(self.player.id)
        response = self.client.get(reverse('index'))
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_authenticated'])
        self.assertEqual(response.context['current_user'], self.player)
    
    def test_room_view_unauthenticated(self):
        """Test room view redirects unauthenticated users"""
        response = self.client.get(reverse('room', args=['test_room']))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
    
    def test_room_view_authenticated(self):
        """Test room view for authenticated user"""
        self.create_authenticated_session(self.player.id)
        response = self.client.get(reverse('room', args=['test_room']))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['room_name'], 'test_room')
        self.assertEqual(response.context['player'], self.player)
    
    def test_room_view_invalid_room_name(self):
        """Test room view with invalid room name"""
        self.create_authenticated_session(self.player.id)
        response = self.client.get(reverse('room', args=['invalid@room!']))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('index'))
    
    def test_join_room_unauthenticated(self):
        """Test join room redirects unauthenticated users"""
        response = self.client.post(reverse('join_room'), {
            'room_name': 'test_room'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
    
    def test_join_room_authenticated(self):
        """Test join room for authenticated user"""
        self.create_authenticated_session(self.player.id)
        response = self.client.post(reverse('join_room'), {
            'room_name': 'test_room'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('room', args=['test_room']))
    
    def test_join_room_invalid_name(self):
        """Test join room with invalid room name defaults to main"""
        self.create_authenticated_session(self.player.id)
        response = self.client.post(reverse('join_room'), {
            'room_name': 'invalid@room!'
        })
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('room', args=['main']))
    
    def test_player_stats_valid_user(self):
        """Test player stats API for valid user"""
        # Create some bets for the player
        Bet.objects.create(
            player=self.player,
            round=self.game_round,
            amount=100,
            color='red',
            correct=True,
            payout=200
        )
        
        response = self.client.get(reverse('player_stats', args=[self.player.username]))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['username'], self.player.username)
        self.assertEqual(data['balance'], self.player.balance)
        self.assertIn('recent_bets', data)
        self.assertIn('total_wagered', data)
        self.assertIn('total_winnings', data)
    
    def test_player_stats_invalid_user(self):
        """Test player stats API for non-existent user"""
        response = self.client.get(reverse('player_stats', args=['nonexistent']))
        
        self.assertEqual(response.status_code, 404)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_player_stats_invalid_username_format(self):
        """Test player stats API with invalid username format"""
        response = self.client.get(reverse('player_stats', args=['invalid@user!']))
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertIn('error', data)
    
    def test_game_history_view(self):
        """Test game history view"""
        # Create completed game round
        completed_round = GameRound.objects.create(
            room='test_room',
            game_type='parity',
            ended=True,
            result_number=5,
            result_color='violet'
        )
        
        response = self.client.get(reverse('game_history'))
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Game History')
        self.assertIn('rounds', response.context)
    
    def test_game_history_with_filter(self):
        """Test game history with game type filter"""
        response = self.client.get(reverse('game_history') + '?game_type=parity')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['game_type'], 'parity')
    
    def test_upload_avatar_unauthenticated(self):
        """Test avatar upload redirects unauthenticated users"""
        response = self.client.post(reverse('upload_avatar'))
        
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('login'))
    
    def test_upload_avatar_get(self):
        """Test avatar upload GET request"""
        self.create_authenticated_session(self.player.id)
        response = self.client.get(reverse('upload_avatar'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['player'], self.player)
    
    def test_upload_avatar_no_file(self):
        """Test avatar upload without file"""
        self.create_authenticated_session(self.player.id)
        response = self.client.post(reverse('upload_avatar'))
        
        self.assertEqual(response.status_code, 200)
        # Should show error message about selecting file
    
    @patch('polling.views.add_security_headers')
    def test_security_headers_added(self, mock_add_headers):
        """Test that security headers are added to responses"""
        mock_add_headers.return_value = Mock()
        
        response = self.client.get(reverse('index'))
        
        # Verify security headers function was called
        mock_add_headers.assert_called_once()
    
    def test_player_bet_history_api(self):
        """Test player bet history API"""
        # Create some bets
        for i in range(5):
            Bet.objects.create(
                player=self.player,
                round=self.game_round,
                amount=100 + i,
                color='red',
                correct=i % 2 == 0
            )
        
        response = self.client.get(reverse('player_bet_history', args=[self.player.username]))
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertIn('bets', data)
        self.assertIn('player_stats', data)
        self.assertIn('pagination', data)
        self.assertEqual(len(data['bets']), 5)
    
    def test_player_bet_history_pagination(self):
        """Test player bet history API pagination"""
        response = self.client.get(
            reverse('player_bet_history', args=[self.player.username]) + 
            '?page=1&limit=10'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        self.assertEqual(data['pagination']['page'], 1)
        self.assertEqual(data['pagination']['limit'], 10)
    
    def test_player_bet_history_invalid_pagination(self):
        """Test player bet history API with invalid pagination parameters"""
        response = self.client.get(
            reverse('player_bet_history', args=[self.player.username]) + 
            '?page=invalid&limit=1000'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        
        # Should default to page 1 and limit to max 100
        self.assertEqual(data['pagination']['page'], 1)
        self.assertEqual(data['pagination']['limit'], 100)


class ValidationTestCase(TestCase):
    """Test cases for validation functions"""
    
    def test_validate_username_valid(self):
        """Test username validation with valid usernames"""
        valid_usernames = ['user123', 'test_user', 'player-1', 'abc']

        for username in valid_usernames:
            is_valid, result = InputValidator.validate_username(username)
            self.assertTrue(is_valid, f"Username '{username}' should be valid")
            self.assertEqual(result, username)

    def test_validate_username_invalid(self):
        """Test username validation with invalid usernames"""
        invalid_usernames = [
            '',           # Empty
            'ab',         # Too short
            'a' * 21,     # Too long
            'user@name',  # Invalid character
            'user name',  # Space
            'user!',      # Special character
        ]

        for username in invalid_usernames:
            is_valid, result = InputValidator.validate_username(username)
            self.assertFalse(is_valid, f"Username '{username}' should be invalid")
            self.assertIsInstance(result, str)  # Error message
    
    def test_validate_bet_amount_valid(self):
        """Test bet amount validation with valid amounts"""
        valid_amounts = [1, 10, 100, 1000, '50', '999']

        for amount in valid_amounts:
            is_valid, result = InputValidator.validate_bet_amount(amount)
            self.assertTrue(is_valid, f"Amount '{amount}' should be valid")
            self.assertIsInstance(result, int)

    def test_validate_bet_amount_invalid(self):
        """Test bet amount validation with invalid amounts"""
        invalid_amounts = [
            0,           # Zero
            -10,         # Negative
            'invalid',   # Non-numeric
            '',          # Empty
            None,        # None
            10001,       # Too high
        ]

        for amount in invalid_amounts:
            is_valid, result = InputValidator.validate_bet_amount(amount)
            self.assertFalse(is_valid, f"Amount '{amount}' should be invalid")
            self.assertIsInstance(result, str)  # Error message

    def test_validate_bet_amount_with_max(self):
        """Test bet amount validation with maximum limit"""
        is_valid, result = InputValidator.validate_bet_amount(500, max_amount=1000)
        self.assertTrue(is_valid)

        is_valid, result = InputValidator.validate_bet_amount(1500, max_amount=1000)
        self.assertFalse(is_valid)
        self.assertIn('Insufficient balance', result)
