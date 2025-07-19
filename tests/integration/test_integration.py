"""
Integration tests for the Color Prediction Game.
Tests complete user workflows and system interactions end-to-end.
"""

import json
import time
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from datetime import timedelta

from polling.models import (
    Player, Admin, GameRound, Bet, Transaction, 
    MasterWalletTransaction, PaymentTransaction, WithdrawalRequest
)
from tests.conftest import BaseTestCase, PlayerFactory, AdminFactory, GameRoundFactory
from tests.utils import (
    TestClient, AssertionHelpers, TestDataBuilder, MockServices,
    setup_test_notification_types
)


class UserRegistrationToFirstBetIntegrationTest(BaseTestCase):
    """Test complete user journey from registration to first bet."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        
        # Create active game round
        self.game_round = GameRoundFactory(ended=False)
    
    @patch('polling.otp_utils.OTPService.send_otp')
    @patch('polling.otp_utils.OTPService.verify_otp')
    def test_complete_user_journey(self, mock_verify_otp, mock_send_otp):
        """Test complete user journey from registration to placing first bet."""
        
        # Mock OTP services
        mock_send_otp.return_value = (True, 'OTP sent successfully', '123456')
        mock_verify_otp.return_value = (True, 'OTP verified successfully')
        
        # Step 1: User Registration
        registration_data = {
            'username': 'newuser',
            'email': 'newuser@gmail.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
        }
        
        response = self.client.post('/register/', registration_data)
        self.assertEqual(response.status_code, 302)  # Redirect to OTP verification
        
        # Check user was created
        player = Player.objects.get(username='newuser')
        self.assertFalse(player.email_verified)
        self.assertEqual(player.balance, 0)  # Zero initial balance
        
        # Step 2: OTP Verification
        verification_data = {'otp': '123456'}
        response = self.client.post('/verify-otp/', verification_data)
        self.assertEqual(response.status_code, 302)  # Redirect after verification
        
        # Check user is verified
        player.refresh_from_db()
        self.assertTrue(player.email_verified)
        
        # Step 3: User Login
        login_data = {
            'username': 'newuser',
            'password': 'SecurePass123!'
        }
        
        response = self.client.post('/login/', login_data)
        self.assertEqual(response.status_code, 302)  # Redirect to dashboard
        
        # Check session is set
        self.assertTrue(self.client.session.get('is_authenticated'))
        
        # Step 4: Add Money to Wallet
        with MockServices.mock_razorpay_success():
            deposit_data = {
                'amount': 1000,
                'payment_method': 'razorpay'
            }
            
            response = self.client.post_json('/api/deposit/', deposit_data)
            data = self.assert_json_response(response, 200)
            self.assertTrue(data['success'])
        
        # Check balance updated
        player.refresh_from_db()
        self.assertEqual(player.balance, 1000)
        
        # Check transaction created
        transaction = Transaction.objects.filter(
            player=player,
            transaction_type='deposit',
            amount=1000
        ).first()
        self.assertIsNotNone(transaction)
        
        # Step 5: Place First Bet
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
            player=player,
            round=self.game_round,
            amount=100
        ).first()
        self.assertIsNotNone(bet)
        
        # Check balance deducted
        player.refresh_from_db()
        self.assertEqual(player.balance, 900)
        
        # Step 6: Game Result and Winnings (if player wins)
        self.game_round.result_color = 'red'  # Player wins
        self.game_round.ended = True
        self.game_round.save()
        
        # Process game results
        from polling.game_logic import process_game_results
        process_game_results(self.game_round)
        
        # Check winnings
        player.refresh_from_db()
        self.assertEqual(player.balance, 1000)  # 900 + 200 (2x bet)
        
        # Check winning transaction
        win_transaction = Transaction.objects.filter(
            player=player,
            transaction_type='win'
        ).first()
        self.assertIsNotNone(win_transaction)


class AdminGameControlIntegrationTest(BaseTestCase):
    """Test admin game control workflow."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        
        # Create admin
        self.admin = AdminFactory()
        self.client.login_admin(self.admin)
        
        # Create players and bets
        self.scenario = TestDataBuilder().with_players(3).with_game_rounds(1).build()
        self.game_round = self.scenario['game_rounds'][0]
        
        # Create bets
        for i, player in enumerate(self.scenario['players']):
            color = ['red', 'green', 'violet'][i]
            amount = (i + 1) * 100
            Bet.objects.create(
                player=player,
                round=self.game_round,
                bet_type='color',
                color=color,
                amount=amount
            )
    
    def test_admin_game_control_workflow(self):
        """Test complete admin game control workflow."""
        
        # Step 1: Admin views live betting stats
        response = self.client.get('/control-panel/api/live-betting-stats/')
        data = self.assert_json_response(response, 200)
        
        self.assertIn('betting_stats', data)
        self.assertIn('red', data['betting_stats'])
        self.assertIn('green', data['betting_stats'])
        self.assertIn('violet', data['betting_stats'])
        
        # Step 2: Admin selects winning color
        select_data = {
            'room': 'main',
            'color': 'green'  # Green wins
        }
        
        response = self.client.post_json('/control-panel/api/select-color/', select_data)
        data = self.assert_json_response(response, 200)
        self.assertTrue(data['success'])
        
        # Check game round ended with correct result
        self.game_round.refresh_from_db()
        self.assertEqual(self.game_round.result_color, 'green')
        self.assertTrue(self.game_round.ended)
        
        # Step 3: Check results were processed
        # Green bettor should win, others should lose
        green_player = self.scenario['players'][1]  # Player who bet on green
        green_player.refresh_from_db()
        
        # Green bettor should have winnings
        win_transaction = Transaction.objects.filter(
            player=green_player,
            transaction_type='win'
        ).first()
        self.assertIsNotNone(win_transaction)
        
        # Step 4: Check master wallet received house earnings
        master_transaction = MasterWalletTransaction.objects.filter(
            transaction_type='house_win',
            reference_id=self.game_round.period_id
        ).first()
        self.assertIsNotNone(master_transaction)
        
        # Step 5: Admin views updated financial stats
        response = self.client.get('/control-panel/api/financial-stats/')
        data = self.assert_json_response(response, 200)
        
        self.assertIn('total_revenue', data)
        self.assertIn('total_payouts', data)


class PaymentIntegrationTest(BaseTestCase):
    """Test payment system integration."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory(balance=0)
        self.client.login_player(self.player)
    
    @patch('polling.payment_service.razorpay.Order.create')
    @patch('polling.payment_service.razorpay.Utility.verify_payment_signature')
    def test_complete_payment_workflow(self, mock_verify, mock_create_order):
        """Test complete payment workflow from order creation to balance update."""
        
        # Mock Razorpay responses
        mock_create_order.return_value = {
            'id': 'order_test123',
            'amount': 50000,  # 500 INR in paise
            'currency': 'INR',
            'status': 'created'
        }
        mock_verify.return_value = True
        
        # Step 1: Create payment order
        order_data = {
            'amount': 500,
            'currency': 'INR'
        }
        
        response = self.client.post_json('/api/create-payment-order/', order_data)
        data = self.assert_json_response(response, 200)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['order_id'], 'order_test123')
        
        # Step 2: Simulate payment completion
        payment_data = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'signature_test123',
            'amount': 500
        }
        
        response = self.client.post_json('/api/verify-payment/', payment_data)
        data = self.assert_json_response(response, 200)
        
        self.assertTrue(data['success'])
        
        # Step 3: Check balance updated
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 500)
        
        # Step 4: Check transaction created
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='deposit',
            amount=500
        ).first()
        self.assertIsNotNone(transaction)
        
        # Step 5: Check payment transaction record
        payment_transaction = PaymentTransaction.objects.filter(
            player=self.player,
            razorpay_order_id='order_test123'
        ).first()
        self.assertIsNotNone(payment_transaction)
        self.assertEqual(payment_transaction.status, 'completed')


class WithdrawalIntegrationTest(BaseTestCase):
    """Test withdrawal system integration."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory(balance=2000)
        self.admin = AdminFactory()
    
    def test_complete_withdrawal_workflow(self):
        """Test complete withdrawal workflow from request to approval."""
        
        # Step 1: Player requests withdrawal
        self.client.login_player(self.player)
        
        withdrawal_data = {
            'amount': 500,
            'withdrawal_method': 'bank_transfer',
            'account_details': {
                'account_number': '123456789',
                'ifsc_code': 'HDFC0001234',
                'account_holder': 'Test User'
            }
        }
        
        response = self.client.post_json('/api/request-withdrawal/', withdrawal_data)
        data = self.assert_json_response(response, 200)
        self.assertTrue(data['success'])
        
        # Check withdrawal request created
        withdrawal = WithdrawalRequest.objects.filter(
            player=self.player,
            amount=500
        ).first()
        self.assertIsNotNone(withdrawal)
        self.assertEqual(withdrawal.status, 'pending')
        
        # Step 2: Admin reviews and approves withdrawal
        self.client.login_admin(self.admin)
        
        approval_data = {
            'withdrawal_id': withdrawal.id,
            'action': 'approve',
            'admin_notes': 'Approved after verification'
        }
        
        response = self.client.post_json('/control-panel/api/process-withdrawal/', approval_data)
        data = self.assert_json_response(response, 200)
        self.assertTrue(data['success'])
        
        # Step 3: Check withdrawal processed
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'approved')
        
        # Step 4: Check balance deducted
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 1500)  # 2000 - 500
        
        # Step 5: Check transaction created
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='withdrawal',
            amount=-500
        ).first()
        self.assertIsNotNone(transaction)
        
        # Step 6: Check master wallet transaction
        master_transaction = MasterWalletTransaction.objects.filter(
            transaction_type='withdrawal_payout',
            amount=-500
        ).first()
        self.assertIsNotNone(master_transaction)


class MultiPlayerGameIntegrationTest(TransactionTestCase):
    """Test multi-player game scenarios."""
    
    def setUp(self):
        setup_test_notification_types()
        
        # Create multiple players
        self.players = []
        for i in range(5):
            player = PlayerFactory(
                username=f'player{i+1}',
                balance=1000
            )
            self.players.append(player)
        
        # Create game round
        self.game_round = GameRoundFactory(ended=False)
    
    def test_multi_player_betting_and_results(self):
        """Test multiple players betting and result processing."""
        
        # Step 1: Multiple players place bets
        bet_colors = ['red', 'green', 'red', 'violet', 'green']
        bet_amounts = [100, 200, 150, 300, 250]
        
        for i, player in enumerate(self.players):
            Bet.objects.create(
                player=player,
                round=self.game_round,
                bet_type='color',
                color=bet_colors[i],
                amount=bet_amounts[i]
            )
            
            # Update player balance
            player.balance -= bet_amounts[i]
            player.save()
        
        # Step 2: Set game result (red wins)
        self.game_round.result_color = 'red'
        self.game_round.ended = True
        self.game_round.save()
        
        # Step 3: Process results
        from polling.game_logic import process_game_results
        process_game_results(self.game_round)
        
        # Step 4: Check results
        # Players 0 and 2 bet on red and should win
        for i in [0, 2]:  # Red bettors
            player = self.players[i]
            player.refresh_from_db()
            
            # Should have original balance - bet + winnings
            expected_balance = 1000 - bet_amounts[i] + (bet_amounts[i] * 2)
            self.assertEqual(player.balance, expected_balance)
            
            # Should have winning transaction
            win_transaction = Transaction.objects.filter(
                player=player,
                transaction_type='win'
            ).first()
            self.assertIsNotNone(win_transaction)
        
        # Other players should have lost their bets
        for i in [1, 3, 4]:  # Non-red bettors
            player = self.players[i]
            player.refresh_from_db()
            
            # Should have original balance - bet amount
            expected_balance = 1000 - bet_amounts[i]
            self.assertEqual(player.balance, expected_balance)
        
        # Step 5: Check master wallet received house earnings
        total_bets = sum(bet_amounts)
        total_winnings = (bet_amounts[0] + bet_amounts[2]) * 2  # Red bets * 2
        house_earnings = total_bets - total_winnings
        
        master_transaction = MasterWalletTransaction.objects.filter(
            transaction_type='house_win',
            reference_id=self.game_round.period_id
        ).first()
        
        if house_earnings > 0:
            self.assertIsNotNone(master_transaction)
            self.assertEqual(master_transaction.amount, house_earnings)


class SystemStressTest(BaseTestCase):
    """Test system under stress conditions."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
    
    def test_concurrent_betting_stress(self):
        """Test system under concurrent betting load."""
        import threading
        import time
        
        # Create multiple players
        players = []
        for i in range(20):
            player = PlayerFactory(
                username=f'stress_player_{i}',
                balance=1000
            )
            players.append(player)
        
        # Create game round
        game_round = GameRoundFactory(ended=False)
        
        results = []
        
        def place_bet(player):
            client = TestClient()
            client.login_player(player)
            
            bet_data = {
                'room': 'main',
                'bet_type': 'color',
                'color': 'red',
                'amount': 100
            }
            
            response = client.post_json('/api/place-bet/', bet_data)
            results.append(response.status_code)
        
        # Create threads for concurrent betting
        threads = []
        for player in players:
            thread = threading.Thread(target=place_bet, args=(player,))
            threads.append(thread)
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        end_time = time.time()
        
        # Check results
        successful_bets = sum(1 for status in results if status == 200)
        
        # Most bets should succeed (allowing for some race conditions)
        self.assertGreaterEqual(successful_bets, 15)
        
        # Should complete within reasonable time
        execution_time = end_time - start_time
        self.assertLess(execution_time, 10.0, "Concurrent betting took too long")
        
        # Check database consistency
        total_bets = Bet.objects.filter(round=game_round).count()
        self.assertEqual(total_bets, successful_bets)
