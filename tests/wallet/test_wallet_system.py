"""
Comprehensive wallet system tests for the Color Prediction Game.
Tests transaction handling, balance management, payment processing, and fraud detection.
"""

import json
from decimal import Decimal
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.db import transaction
from django.utils import timezone
from datetime import timedelta

from polling.models import (
    Player, Transaction, MasterWalletTransaction, 
    PaymentTransaction, WithdrawalRequest
)
from polling.wallet_service import WalletService
from polling.fraud_detection import FraudDetectionService
from tests.conftest import BaseTestCase, PlayerFactory, TransactionFactory
from tests.utils import (
    TestClient, AssertionHelpers, MockServices, 
    setup_test_notification_types
)


class WalletServiceTests(BaseTestCase):
    """Test wallet service functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.player = self.create_player(balance=1000)
        self.wallet_service = WalletService()
    
    def test_deposit_money_success(self):
        """Test successful money deposit."""
        initial_balance = self.player.balance
        deposit_amount = 500
        
        result = self.wallet_service.deposit_money(
            player=self.player,
            amount=deposit_amount,
            payment_method='razorpay',
            transaction_id='txn_123456'
        )
        
        self.assertTrue(result['success'])
        
        # Check balance updated
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance + deposit_amount)
        
        # Check transaction created
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='deposit',
            amount=deposit_amount
        ).first()
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.balance_after, initial_balance + deposit_amount)
    
    def test_deposit_money_below_minimum(self):
        """Test deposit below minimum amount."""
        result = self.wallet_service.deposit_money(
            player=self.player,
            amount=5,  # Below minimum
            payment_method='razorpay',
            transaction_id='txn_123456'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('minimum', result['message'].lower())
        
        # Balance should not change
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 1000)
    
    def test_deposit_money_above_maximum(self):
        """Test deposit above maximum amount."""
        result = self.wallet_service.deposit_money(
            player=self.player,
            amount=50000,  # Above maximum
            payment_method='razorpay',
            transaction_id='txn_123456'
        )
        
        self.assertFalse(result['success'])
        self.assertIn('maximum', result['message'].lower())
    
    def test_withdraw_money_success(self):
        """Test successful money withdrawal."""
        initial_balance = self.player.balance
        withdrawal_amount = 300
        
        result = self.wallet_service.withdraw_money(
            player=self.player,
            amount=withdrawal_amount,
            withdrawal_method='bank_transfer',
            account_details={'account': '123456789'}
        )
        
        self.assertTrue(result['success'])
        
        # Check balance updated
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance - withdrawal_amount)
        
        # Check transaction created
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='withdrawal',
            amount=-withdrawal_amount
        ).first()
        self.assertIsNotNone(transaction)
    
    def test_withdraw_money_insufficient_balance(self):
        """Test withdrawal with insufficient balance."""
        result = self.wallet_service.withdraw_money(
            player=self.player,
            amount=1500,  # More than balance
            withdrawal_method='bank_transfer',
            account_details={'account': '123456789'}
        )
        
        self.assertFalse(result['success'])
        self.assertIn('insufficient', result['message'].lower())
        
        # Balance should not change
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 1000)
    
    def test_withdraw_money_below_minimum(self):
        """Test withdrawal below minimum amount."""
        result = self.wallet_service.withdraw_money(
            player=self.player,
            amount=10,  # Below minimum
            withdrawal_method='bank_transfer',
            account_details={'account': '123456789'}
        )
        
        self.assertFalse(result['success'])
        self.assertIn('minimum', result['message'].lower())
    
    def test_transfer_to_master_wallet(self):
        """Test transfer to master wallet."""
        transfer_amount = 200
        
        result = self.wallet_service.transfer_to_master_wallet(
            amount=transfer_amount,
            description='House win',
            reference_id='game_123'
        )
        
        self.assertTrue(result['success'])
        
        # Check master wallet transaction created
        master_transaction = MasterWalletTransaction.objects.filter(
            transaction_type='house_win',
            amount=transfer_amount
        ).first()
        self.assertIsNotNone(master_transaction)
    
    def test_get_transaction_history(self):
        """Test getting transaction history."""
        # Create some transactions
        TransactionFactory(player=self.player, transaction_type='deposit', amount=500)
        TransactionFactory(player=self.player, transaction_type='bet', amount=-100)
        TransactionFactory(player=self.player, transaction_type='win', amount=200)
        
        history = self.wallet_service.get_transaction_history(
            player=self.player,
            limit=10
        )
        
        self.assertEqual(len(history), 3)
        self.assertEqual(history[0]['transaction_type'], 'win')  # Most recent first
    
    def test_get_balance_summary(self):
        """Test getting balance summary."""
        # Create some transactions
        TransactionFactory(player=self.player, transaction_type='deposit', amount=500)
        TransactionFactory(player=self.player, transaction_type='bet', amount=-100)
        
        summary = self.wallet_service.get_balance_summary(self.player)
        
        self.assertIn('current_balance', summary)
        self.assertIn('total_deposits', summary)
        self.assertIn('total_withdrawals', summary)
        self.assertIn('total_bets', summary)
        self.assertIn('total_winnings', summary)


class TransactionTests(BaseTestCase):
    """Test transaction handling and integrity."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.player = self.create_player(balance=1000)
    
    def test_atomic_transaction_success(self):
        """Test atomic transaction processing."""
        initial_balance = self.player.balance
        
        with transaction.atomic():
            # Deduct money for bet
            self.player.balance -= 100
            self.player.save()
            
            # Create transaction record
            Transaction.objects.create(
                player=self.player,
                transaction_type='bet',
                amount=-100,
                balance_before=initial_balance,
                balance_after=self.player.balance,
                description='Test bet'
            )
        
        # Both operations should succeed
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 900)
        
        transaction_record = Transaction.objects.filter(
            player=self.player,
            transaction_type='bet'
        ).first()
        self.assertIsNotNone(transaction_record)
    
    def test_atomic_transaction_rollback(self):
        """Test atomic transaction rollback on error."""
        initial_balance = self.player.balance
        
        try:
            with transaction.atomic():
                # Deduct money
                self.player.balance -= 100
                self.player.save()
                
                # Simulate error
                raise Exception("Simulated error")
                
                # This transaction creation should not happen
                Transaction.objects.create(
                    player=self.player,
                    transaction_type='bet',
                    amount=-100,
                    balance_before=initial_balance,
                    balance_after=self.player.balance,
                    description='Test bet'
                )
        except Exception:
            pass
        
        # Balance should be rolled back
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance)
        
        # No transaction should be created
        self.assertFalse(Transaction.objects.filter(
            player=self.player,
            transaction_type='bet'
        ).exists())
    
    def test_concurrent_transaction_handling(self):
        """Test handling of concurrent transactions."""
        # This test simulates race conditions
        # In practice, database constraints and atomic operations prevent issues
        
        initial_balance = self.player.balance
        
        # Simulate two concurrent bet attempts
        def place_bet(amount):
            with transaction.atomic():
                player = Player.objects.select_for_update().get(id=self.player.id)
                if player.balance >= amount:
                    player.balance -= amount
                    player.save()
                    return True
                return False
        
        # Both bets should be processed correctly
        result1 = place_bet(100)
        result2 = place_bet(200)
        
        self.assertTrue(result1)
        self.assertTrue(result2)
        
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 700)  # 1000 - 100 - 200
    
    def test_transaction_validation(self):
        """Test transaction validation rules."""
        # Test negative deposit (should fail)
        with self.assertRaises(Exception):
            Transaction.objects.create(
                player=self.player,
                transaction_type='deposit',
                amount=-100,  # Negative deposit
                balance_before=1000,
                balance_after=900,
                description='Invalid deposit'
            )
        
        # Test positive withdrawal (should fail)
        with self.assertRaises(Exception):
            Transaction.objects.create(
                player=self.player,
                transaction_type='withdrawal',
                amount=100,  # Positive withdrawal
                balance_before=1000,
                balance_after=1100,
                description='Invalid withdrawal'
            )


class PaymentIntegrationTests(BaseTestCase):
    """Test payment gateway integration."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = self.create_player(balance=1000)
        self.client.login_player(self.player)
    
    @patch('polling.payment_service.razorpay.Order.create')
    def test_create_payment_order_success(self, mock_create_order):
        """Test successful payment order creation."""
        mock_create_order.return_value = {
            'id': 'order_test123',
            'amount': 50000,  # 500 INR in paise
            'currency': 'INR',
            'status': 'created'
        }
        
        payment_data = {
            'amount': 500,
            'currency': 'INR'
        }
        
        response = self.client.post_json('/api/create-payment-order/', payment_data)
        data = self.assert_json_response(response, 200)
        
        self.assertTrue(data['success'])
        self.assertEqual(data['order_id'], 'order_test123')
        mock_create_order.assert_called_once()
    
    @patch('polling.payment_service.razorpay.Order.create')
    def test_create_payment_order_failure(self, mock_create_order):
        """Test payment order creation failure."""
        mock_create_order.side_effect = Exception('Payment gateway error')
        
        payment_data = {
            'amount': 500,
            'currency': 'INR'
        }
        
        response = self.client.post_json('/api/create-payment-order/', payment_data)
        data = self.assert_json_response(response, 500)
        
        self.assertFalse(data['success'])
        self.assertIn('error', data['message'].lower())
    
    @patch('polling.payment_service.razorpay.Utility.verify_payment_signature')
    def test_verify_payment_success(self, mock_verify):
        """Test successful payment verification."""
        mock_verify.return_value = True
        
        verification_data = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'signature_test123'
        }
        
        response = self.client.post_json('/api/verify-payment/', verification_data)
        data = self.assert_json_response(response, 200)
        
        self.assertTrue(data['success'])
        mock_verify.assert_called_once()
    
    @patch('polling.payment_service.razorpay.Utility.verify_payment_signature')
    def test_verify_payment_failure(self, mock_verify):
        """Test payment verification failure."""
        mock_verify.return_value = False
        
        verification_data = {
            'razorpay_order_id': 'order_test123',
            'razorpay_payment_id': 'pay_test123',
            'razorpay_signature': 'invalid_signature'
        }
        
        response = self.client.post_json('/api/verify-payment/', verification_data)
        data = self.assert_json_response(response, 400)
        
        self.assertFalse(data['success'])
        self.assertIn('verification failed', data['message'].lower())


class FraudDetectionTests(BaseTestCase):
    """Test fraud detection system."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.player = self.create_player(balance=1000)
        self.fraud_service = FraudDetectionService()
    
    def test_calculate_fraud_score_low_risk(self):
        """Test fraud score calculation for low-risk transaction."""
        transaction_data = {
            'player': self.player,
            'amount': 100,
            'transaction_type': 'deposit',
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0...'
        }
        
        score, factors = self.fraud_service.calculate_fraud_score(transaction_data)
        
        self.assertLess(score, 50)  # Low risk
        self.assertIsInstance(factors, list)
    
    def test_calculate_fraud_score_high_risk(self):
        """Test fraud score calculation for high-risk transaction."""
        # Create multiple recent transactions to simulate suspicious activity
        for i in range(10):
            TransactionFactory(
                player=self.player,
                transaction_type='deposit',
                amount=1000,
                created_at=timezone.now() - timedelta(minutes=i)
            )
        
        transaction_data = {
            'player': self.player,
            'amount': 5000,  # Large amount
            'transaction_type': 'deposit',
            'ip_address': '192.168.1.1',
            'user_agent': 'Mozilla/5.0...'
        }
        
        score, factors = self.fraud_service.calculate_fraud_score(transaction_data)
        
        self.assertGreater(score, 70)  # High risk
        self.assertIn('Multiple recent transactions', ' '.join(factors))
    
    def test_fraud_detection_blocks_suspicious_transaction(self):
        """Test that fraud detection blocks suspicious transactions."""
        # Create suspicious pattern
        for i in range(15):  # Many recent transactions
            TransactionFactory(
                player=self.player,
                transaction_type='deposit',
                amount=1000,
                created_at=timezone.now() - timedelta(minutes=i)
            )
        
        wallet_service = WalletService()
        result = wallet_service.deposit_money(
            player=self.player,
            amount=10000,  # Large amount
            payment_method='razorpay',
            transaction_id='txn_suspicious'
        )
        
        # Should be blocked due to high fraud score
        self.assertFalse(result['success'])
        self.assertIn('fraud', result['message'].lower())
    
    def test_fraud_detection_allows_normal_transaction(self):
        """Test that fraud detection allows normal transactions."""
        wallet_service = WalletService()
        result = wallet_service.deposit_money(
            player=self.player,
            amount=100,  # Normal amount
            payment_method='razorpay',
            transaction_id='txn_normal'
        )
        
        # Should be allowed
        self.assertTrue(result['success'])


class WithdrawalSystemTests(BaseTestCase):
    """Test withdrawal system functionality."""

    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = self.create_player(balance=2000)
        self.client.login_player(self.player)

    def test_create_withdrawal_request(self):
        """Test creating a withdrawal request."""
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

    def test_withdrawal_request_insufficient_balance(self):
        """Test withdrawal request with insufficient balance."""
        withdrawal_data = {
            'amount': 3000,  # More than balance
            'withdrawal_method': 'bank_transfer',
            'account_details': {
                'account_number': '123456789',
                'ifsc_code': 'HDFC0001234',
                'account_holder': 'Test User'
            }
        }

        response = self.client.post_json('/api/request-withdrawal/', withdrawal_data)
        data = self.assert_json_response(response, 400)

        self.assertFalse(data['success'])
        self.assertIn('insufficient', data['message'].lower())

    def test_withdrawal_approval_process(self):
        """Test withdrawal approval by admin."""
        # Create withdrawal request
        withdrawal = WithdrawalRequest.objects.create(
            player=self.player,
            amount=500,
            withdrawal_method='bank_transfer',
            account_details={'account': '123456789'},
            status='pending'
        )

        # Admin approves withdrawal
        admin = self.create_admin()
        self.client.login_admin(admin)

        approval_data = {
            'withdrawal_id': withdrawal.id,
            'action': 'approve',
            'admin_notes': 'Approved after verification'
        }

        response = self.client.post_json('/api/admin/process-withdrawal/', approval_data)
        data = self.assert_json_response(response, 200)

        self.assertTrue(data['success'])

        # Check withdrawal status updated
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'approved')

        # Check balance deducted
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 1500)  # 2000 - 500

    def test_withdrawal_rejection_process(self):
        """Test withdrawal rejection by admin."""
        # Create withdrawal request
        withdrawal = WithdrawalRequest.objects.create(
            player=self.player,
            amount=500,
            withdrawal_method='bank_transfer',
            account_details={'account': '123456789'},
            status='pending'
        )

        initial_balance = self.player.balance

        # Admin rejects withdrawal
        admin = self.create_admin()
        self.client.login_admin(admin)

        rejection_data = {
            'withdrawal_id': withdrawal.id,
            'action': 'reject',
            'admin_notes': 'Rejected due to incomplete documents'
        }

        response = self.client.post_json('/api/admin/process-withdrawal/', rejection_data)
        data = self.assert_json_response(response, 200)

        self.assertTrue(data['success'])

        # Check withdrawal status updated
        withdrawal.refresh_from_db()
        self.assertEqual(withdrawal.status, 'rejected')

        # Check balance unchanged
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance)

    def test_daily_withdrawal_limit(self):
        """Test daily withdrawal limit enforcement."""
        # Create multiple withdrawal requests in same day
        total_today = 0

        for i in range(3):
            withdrawal_amount = 2000
            withdrawal = WithdrawalRequest.objects.create(
                player=self.player,
                amount=withdrawal_amount,
                withdrawal_method='bank_transfer',
                account_details={'account': '123456789'},
                status='approved',
                created_at=timezone.now()
            )
            total_today += withdrawal_amount

        # Try to create another withdrawal that exceeds daily limit
        withdrawal_data = {
            'amount': 20000,  # This should exceed daily limit
            'withdrawal_method': 'bank_transfer',
            'account_details': {
                'account_number': '123456789',
                'ifsc_code': 'HDFC0001234',
                'account_holder': 'Test User'
            }
        }

        response = self.client.post_json('/api/request-withdrawal/', withdrawal_data)
        data = self.assert_json_response(response, 400)

        self.assertFalse(data['success'])
        self.assertIn('daily limit', data['message'].lower())


class MasterWalletTests(BaseTestCase):
    """Test master wallet functionality."""

    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.admin = self.create_admin()
        self.client.login_admin(self.admin)

    def test_master_wallet_balance_tracking(self):
        """Test master wallet balance tracking."""
        # Create some house wins
        MasterWalletTransaction.objects.create(
            transaction_type='house_win',
            amount=1000,
            balance_before=5000,
            balance_after=6000,
            description='House win from game round 123',
            reference_id='round_123'
        )

        MasterWalletTransaction.objects.create(
            transaction_type='withdrawal_payout',
            amount=-500,
            balance_before=6000,
            balance_after=5500,
            description='Withdrawal payout to player',
            reference_id='withdrawal_456'
        )

        # Check master wallet balance
        response = self.client.get('/api/admin/master-wallet-balance/')
        data = self.assert_json_response(response, 200)

        self.assertIn('balance', data)
        self.assertIn('total_revenue', data)
        self.assertIn('total_payouts', data)

    def test_master_wallet_transaction_history(self):
        """Test master wallet transaction history."""
        # Create transactions
        for i in range(5):
            MasterWalletTransaction.objects.create(
                transaction_type='house_win',
                amount=100 * (i + 1),
                balance_before=1000 + (100 * i),
                balance_after=1000 + (100 * (i + 1)),
                description=f'House win {i + 1}',
                reference_id=f'round_{i + 1}'
            )

        response = self.client.get('/api/admin/master-wallet-transactions/')
        data = self.assert_json_response(response, 200)

        self.assertIn('transactions', data)
        self.assertEqual(len(data['transactions']), 5)

        # Should be ordered by most recent first
        self.assertEqual(data['transactions'][0]['amount'], 500)  # Last transaction

    def test_revenue_calculation(self):
        """Test revenue calculation from game results."""
        # Create players and game round
        player1 = self.create_player(balance=1000)
        player2 = self.create_player(balance=1000)
        game_round = self.create_game_round()

        # Create bets
        bet1 = self.create_bet(player1, game_round, color='red', amount=100)
        bet2 = self.create_bet(player2, game_round, color='green', amount=200)

        # Set game result (red wins)
        game_round.result_color = 'red'
        game_round.ended = True
        game_round.save()

        # Process game results
        from polling.game_logic import process_game_results
        process_game_results(game_round)

        # Check master wallet received house edge
        master_transaction = MasterWalletTransaction.objects.filter(
            transaction_type='house_win',
            reference_id=game_round.period_id
        ).first()

        # House should get the losing bets minus winnings paid out
        # This depends on your specific game logic implementation
        self.assertIsNotNone(master_transaction)

    def test_master_wallet_statistics(self):
        """Test master wallet statistics calculation."""
        # Create various transactions
        transactions = [
            ('house_win', 1000),
            ('house_win', 500),
            ('withdrawal_payout', -300),
            ('deposit_fee', 50),
            ('withdrawal_payout', -200),
        ]

        balance = 10000
        for trans_type, amount in transactions:
            balance += amount
            MasterWalletTransaction.objects.create(
                transaction_type=trans_type,
                amount=amount,
                balance_before=balance - amount,
                balance_after=balance,
                description=f'Test {trans_type}',
                reference_id=f'ref_{trans_type}'
            )

        response = self.client.get('/api/admin/master-wallet-stats/')
        data = self.assert_json_response(response, 200)

        self.assertIn('total_revenue', data)
        self.assertIn('total_payouts', data)
        self.assertIn('net_profit', data)
        self.assertIn('transaction_count', data)


class BalanceIntegrityTests(TransactionTestCase):
    """Test balance integrity and consistency."""

    def setUp(self):
        setup_test_notification_types()
        self.player = PlayerFactory(balance=1000)

    def test_balance_consistency_after_multiple_operations(self):
        """Test balance remains consistent after multiple operations."""
        initial_balance = self.player.balance

        # Perform multiple operations
        operations = [
            ('deposit', 500),
            ('bet', -100),
            ('win', 200),
            ('withdrawal', -300),
            ('deposit', 250),
        ]

        expected_balance = initial_balance
        for operation, amount in operations:
            expected_balance += amount

            # Update balance
            self.player.balance += amount
            self.player.save()

            # Create transaction record
            Transaction.objects.create(
                player=self.player,
                transaction_type=operation,
                amount=amount,
                balance_before=self.player.balance - amount,
                balance_after=self.player.balance,
                description=f'Test {operation}'
            )

        # Check final balance
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, expected_balance)

        # Check transaction history sums correctly
        from django.db import models
        total_transactions = Transaction.objects.filter(
            player=self.player
        ).aggregate(total=models.Sum('amount'))['total']

        self.assertEqual(
            initial_balance + total_transactions,
            self.player.balance
        )

    def test_concurrent_balance_updates(self):
        """Test concurrent balance updates maintain integrity."""
        from django.db import transaction
        import threading

        def update_balance(amount):
            with transaction.atomic():
                player = Player.objects.select_for_update().get(id=self.player.id)
                player.balance += amount
                player.save()

        # Create multiple threads to update balance concurrently
        threads = []
        for i in range(10):
            thread = threading.Thread(target=update_balance, args=(10,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check final balance
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 1100)  # 1000 + (10 * 10)
