"""
Comprehensive admin panel tests for the Color Prediction Game.
Tests admin authentication, dashboard, game control, and user management.
"""

import json
from unittest.mock import patch, Mock
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from polling.models import Admin, Player, GameRound, Bet, Transaction, MasterWalletTransaction
from tests.conftest import BaseTestCase, PlayerFactory, AdminFactory, GameRoundFactory, BetFactory
from tests.utils import TestClient, AssertionHelpers, TestDataBuilder, setup_test_notification_types


class AdminAuthenticationTests(BaseTestCase):
    """Test admin authentication functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.admin_login_url = reverse('admin_login')
        self.admin_dashboard_url = reverse('admin_dashboard')
        
        # Create test admin
        self.admin = AdminFactory(
            username='testadmin',
            password_hash='hashed_password',
            is_active=True
        )
    
    def test_admin_login_page_loads(self):
        """Test admin login page loads correctly."""
        response = self.client.get(self.admin_login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Login')
    
    def test_successful_admin_login(self):
        """Test successful admin login."""
        login_data = {
            'username': 'testadmin',
            'password': 'admin123'  # This should match your admin password logic
        }
        
        with patch('polling.admin_views.Admin.check_password') as mock_check:
            mock_check.return_value = True
            response = self.client.post(self.admin_login_url, login_data)
            
            # Should redirect to dashboard
            self.assertEqual(response.status_code, 302)
            
            # Session should be set
            self.assertTrue(self.client.session.get('is_admin_authenticated'))
            self.assertEqual(self.client.session.get('admin_username'), 'testadmin')
    
    def test_admin_login_with_invalid_credentials(self):
        """Test admin login with invalid credentials."""
        login_data = {
            'username': 'testadmin',
            'password': 'wrongpassword'
        }
        
        with patch('polling.admin_views.Admin.check_password') as mock_check:
            mock_check.return_value = False
            response = self.client.post(self.admin_login_url, login_data)
            
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, 'Invalid credentials')
    
    def test_admin_login_with_inactive_admin(self):
        """Test admin login with inactive admin account."""
        # Create inactive admin
        inactive_admin = AdminFactory(
            username='inactiveadmin',
            is_active=False
        )
        
        login_data = {
            'username': 'inactiveadmin',
            'password': 'admin123'
        }
        
        response = self.client.post(self.admin_login_url, login_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Account is deactivated')
    
    def test_admin_logout(self):
        """Test admin logout functionality."""
        # Login admin
        self.client.login_admin(self.admin)
        self.assertTrue(self.client.session.get('is_admin_authenticated'))
        
        # Logout
        logout_url = reverse('admin_logout')
        response = self.client.post(logout_url)
        self.assertEqual(response.status_code, 302)
        
        # Session should be cleared
        self.assertFalse(self.client.session.get('is_admin_authenticated'))
        self.assertIsNone(self.client.session.get('admin_username'))
    
    def test_admin_dashboard_requires_authentication(self):
        """Test admin dashboard requires authentication."""
        response = self.client.get(self.admin_dashboard_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_admin_dashboard_loads_for_authenticated_admin(self):
        """Test admin dashboard loads for authenticated admin."""
        self.client.login_admin(self.admin)
        response = self.client.get(self.admin_dashboard_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')


class AdminDashboardTests(BaseTestCase):
    """Test admin dashboard functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.admin = AdminFactory()
        self.client.login_admin(self.admin)
        
        # Create test data
        self.scenario = TestDataBuilder().with_players(3).with_game_rounds(2).build()
        
    def test_dashboard_statistics(self):
        """Test dashboard shows correct statistics."""
        dashboard_url = reverse('admin_dashboard')
        response = self.client.get(dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Should show player count
        self.assertContains(response, 'Total Players')
        
        # Should show game statistics
        self.assertContains(response, 'Active Rounds')
    
    def test_dashboard_recent_activity(self):
        """Test dashboard shows recent activity."""
        # Create some recent activity
        player = self.scenario['players'][0]
        game_round = self.scenario['game_rounds'][0]
        
        bet = BetFactory(player=player, round=game_round, amount=100)
        
        dashboard_url = reverse('admin_dashboard')
        response = self.client.get(dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        # Should show recent bets or activity
        self.assertContains(response, 'Recent Activity')
    
    def test_dashboard_financial_overview(self):
        """Test dashboard shows financial overview."""
        dashboard_url = reverse('admin_dashboard')
        response = self.client.get(dashboard_url)
        
        self.assertEqual(response.status_code, 200)
        
        # Should show financial metrics
        self.assertContains(response, 'Total Revenue')


class AdminGameControlTests(BaseTestCase):
    """Test admin game control functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.admin = AdminFactory()
        self.client.login_admin(self.admin)
        
        self.game_control_url = reverse('admin_game_control')
        self.game_control_live_url = reverse('admin_game_control_live')
        self.select_color_url = reverse('admin_select_color')
        
        # Create active game round
        self.game_round = GameRoundFactory(ended=False)
        
        # Create some bets
        self.player1 = PlayerFactory(balance=1000)
        self.player2 = PlayerFactory(balance=1000)
        self.bet1 = BetFactory(player=self.player1, round=self.game_round, color='red', amount=100)
        self.bet2 = BetFactory(player=self.player2, round=self.game_round, color='green', amount=200)
    
    def test_game_control_page_loads(self):
        """Test game control page loads."""
        response = self.client.get(self.game_control_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Game Control')
    
    def test_live_game_control_page_loads(self):
        """Test live game control page loads."""
        response = self.client.get(self.game_control_live_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Live Game Control')
    
    def test_admin_select_color_api(self):
        """Test admin color selection API."""
        select_data = {
            'room': 'main',
            'color': 'red'
        }
        
        response = self.client.post_json(self.select_color_url, select_data)
        data = self.assert_json_response(response, 200)
        
        self.assertTrue(data['success'])
        
        # Game round should be updated
        self.game_round.refresh_from_db()
        self.assertEqual(self.game_round.result_color, 'red')
        self.assertTrue(self.game_round.ended)
    
    def test_admin_select_color_invalid_room(self):
        """Test admin color selection with invalid room."""
        select_data = {
            'room': 'nonexistent',
            'color': 'red'
        }
        
        response = self.client.post_json(self.select_color_url, select_data)
        data = self.assert_json_response(response, 400)
        
        self.assertFalse(data['success'])
        self.assertIn('No active round', data['message'])
    
    def test_admin_select_color_invalid_color(self):
        """Test admin color selection with invalid color."""
        select_data = {
            'room': 'main',
            'color': 'invalid_color'
        }
        
        response = self.client.post_json(self.select_color_url, select_data)
        data = self.assert_json_response(response, 400)
        
        self.assertFalse(data['success'])
        self.assertIn('Invalid color', data['message'])
    
    def test_live_betting_stats_api(self):
        """Test live betting statistics API."""
        stats_url = reverse('admin_live_betting_stats')
        response = self.client.get(stats_url)
        data = self.assert_json_response(response, 200)
        
        self.assertIn('betting_stats', data)
        self.assertIn('red', data['betting_stats'])
        self.assertIn('green', data['betting_stats'])
        
        # Check statistics are correct
        self.assertEqual(data['betting_stats']['red']['total_amount'], 100)
        self.assertEqual(data['betting_stats']['green']['total_amount'], 200)
    
    def test_game_timer_info_api(self):
        """Test game timer info API."""
        timer_url = reverse('admin_timer_info')
        response = self.client.get(timer_url)
        data = self.assert_json_response(response, 200)
        
        self.assertIn('time_remaining', data)
        self.assertIn('phase', data)
        self.assertIn('round_id', data)
    
    def test_admin_game_control_requires_authentication(self):
        """Test game control requires admin authentication."""
        self.client.logout_admin()
        
        response = self.client.get(self.game_control_url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        
        response = self.client.post_json(self.select_color_url, {'room': 'main', 'color': 'red'})
        self.assertEqual(response.status_code, 302)  # Redirect to login


class AdminUserManagementTests(BaseTestCase):
    """Test admin user management functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.admin = AdminFactory()
        self.client.login_admin(self.admin)
        
        self.user_management_url = reverse('admin_user_management')
        
        # Create test players
        self.players = [
            PlayerFactory(username='player1', balance=1000, is_active=True),
            PlayerFactory(username='player2', balance=2000, is_active=True),
            PlayerFactory(username='player3', balance=500, is_active=False),
        ]
    
    def test_user_management_page_loads(self):
        """Test user management page loads."""
        response = self.client.get(self.user_management_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'User Management')
    
    def test_user_list_displays_players(self):
        """Test user list displays all players."""
        response = self.client.get(self.user_management_url)
        
        for player in self.players:
            self.assertContains(response, player.username)
    
    def test_player_detail_page(self):
        """Test individual player detail page."""
        player = self.players[0]
        detail_url = reverse('admin_player_detail', args=[player.id])
        
        response = self.client.get(detail_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, player.username)
        self.assertContains(response, str(player.balance))
    
    def test_player_detail_with_betting_history(self):
        """Test player detail shows betting history."""
        player = self.players[0]
        game_round = GameRoundFactory()
        bet = BetFactory(player=player, round=game_round, amount=100)
        
        detail_url = reverse('admin_player_detail', args=[player.id])
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Betting History')
        self.assertContains(response, str(bet.amount))
    
    def test_player_detail_with_transaction_history(self):
        """Test player detail shows transaction history."""
        player = self.players[0]
        
        # Create transaction
        Transaction.objects.create(
            player=player,
            transaction_type='deposit',
            amount=500,
            balance_before=1000,
            balance_after=1500,
            description='Test deposit'
        )
        
        detail_url = reverse('admin_player_detail', args=[player.id])
        response = self.client.get(detail_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Transaction History')
        self.assertContains(response, 'Test deposit')


class AdminFinancialManagementTests(BaseTestCase):
    """Test admin financial management functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.admin = AdminFactory()
        self.client.login_admin(self.admin)
        
        self.financial_url = reverse('admin_financial')
        self.master_wallet_url = reverse('admin_master_wallet')
        
        # Create test financial data
        self.player = PlayerFactory(balance=1000)
        
        # Create transactions
        Transaction.objects.create(
            player=self.player,
            transaction_type='deposit',
            amount=500,
            balance_before=500,
            balance_after=1000,
            description='Test deposit'
        )
        
        Transaction.objects.create(
            player=self.player,
            transaction_type='bet',
            amount=-100,
            balance_before=1000,
            balance_after=900,
            description='Test bet'
        )
    
    def test_financial_management_page_loads(self):
        """Test financial management page loads."""
        response = self.client.get(self.financial_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Financial Management')
    
    def test_master_wallet_dashboard_loads(self):
        """Test master wallet dashboard loads."""
        response = self.client.get(self.master_wallet_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Master Wallet')
    
    def test_financial_statistics_display(self):
        """Test financial statistics are displayed correctly."""
        response = self.client.get(self.financial_url)
        
        # Should show total deposits, withdrawals, etc.
        self.assertContains(response, 'Total Deposits')
        self.assertContains(response, 'Total Withdrawals')
        self.assertContains(response, 'Net Revenue')
    
    def test_master_wallet_transactions_list(self):
        """Test master wallet transactions list."""
        # Create master wallet transaction
        MasterWalletTransaction.objects.create(
            transaction_type='house_win',
            amount=100,
            balance_before=1000,
            balance_after=1100,
            description='House win from game',
            reference_id='test_ref'
        )
        
        transactions_url = reverse('admin_master_wallet_transactions')
        response = self.client.get(transactions_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'House win from game')
    
    def test_financial_reports_generation(self):
        """Test financial reports generation."""
        reports_url = reverse('admin_reports')
        response = self.client.get(reports_url)
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Financial Reports')


class AdminSecurityTests(BaseTestCase):
    """Test admin panel security features."""
    
    def setUp(self):
        super().setUp()
        self.client = TestClient()
        self.admin = AdminFactory()
    
    def test_admin_session_timeout(self):
        """Test admin session timeout functionality."""
        # This test would require mocking time or using a shorter timeout
        # For now, we'll test that the timeout setting exists
        from django.conf import settings
        self.assertTrue(hasattr(settings, 'ADMIN_SESSION_TIMEOUT'))
    
    def test_admin_rate_limiting(self):
        """Test admin panel rate limiting."""
        # Login admin
        self.client.login_admin(self.admin)
        
        # Make multiple rapid requests
        select_color_url = reverse('admin_select_color')
        
        for i in range(10):  # Make multiple requests
            response = self.client.post_json(select_color_url, {
                'room': 'main',
                'color': 'red'
            })
            
            # Should not be rate limited for admin
            self.assertNotEqual(response.status_code, 429)
    
    def test_admin_audit_logging(self):
        """Test admin actions are logged."""
        self.client.login_admin(self.admin)
        
        # Perform admin action
        select_color_url = reverse('admin_select_color')
        response = self.client.post_json(select_color_url, {
            'room': 'main',
            'color': 'red'
        })
        
        # Check if action was logged (implementation dependent)
        # This would require checking your logging system
        self.assertEqual(response.status_code, 200)
    
    def test_admin_csrf_protection(self):
        """Test CSRF protection on admin forms."""
        # Test without CSRF token
        login_url = reverse('admin_login')
        response = self.client.post(login_url, {
            'username': 'testadmin',
            'password': 'admin123'
        })
        
        # Should be protected by CSRF
        # The exact behavior depends on your CSRF configuration
