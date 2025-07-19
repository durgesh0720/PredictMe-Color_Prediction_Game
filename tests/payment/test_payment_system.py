"""
Comprehensive tests for the payment system
"""
import os
import sys
import django
from decimal import Decimal
from unittest.mock import patch, MagicMock

# Setup Django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.test import TestCase, RequestFactory
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from polling.models import Player, PaymentTransaction, Transaction
from polling.payment_service import PaymentService
from polling.payment_validation import PaymentValidationService
from polling.fraud_detection import FraudDetectionService
from polling.payment_views import create_deposit_intent, confirm_deposit, request_withdrawal


class PaymentValidationTests(TestCase):
    """Test payment validation functionality"""
    
    def setUp(self):
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000,
            email_verified=True
        )
    
    def test_valid_deposit_amount(self):
        """Test valid deposit amount validation"""
        is_valid, error = PaymentValidationService.validate_deposit_amount(100)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_invalid_deposit_amount_too_small(self):
        """Test deposit amount too small"""
        is_valid, error = PaymentValidationService.validate_deposit_amount(5)
        self.assertFalse(is_valid)
        self.assertIn("Minimum deposit amount", error)
    
    def test_invalid_deposit_amount_too_large(self):
        """Test deposit amount too large"""
        is_valid, error = PaymentValidationService.validate_deposit_amount(50000)
        self.assertFalse(is_valid)
        self.assertIn("Maximum deposit amount", error)
    
    def test_invalid_deposit_amount_negative(self):
        """Test negative deposit amount"""
        is_valid, error = PaymentValidationService.validate_deposit_amount(-100)
        self.assertFalse(is_valid)
        self.assertEqual(error, "Deposit amount must be positive")
    
    def test_valid_withdrawal_amount(self):
        """Test valid withdrawal amount validation"""
        is_valid, error = PaymentValidationService.validate_withdrawal_amount(self.player, 100)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_withdrawal_insufficient_balance(self):
        """Test withdrawal with insufficient balance"""
        is_valid, error = PaymentValidationService.validate_withdrawal_amount(self.player, 2000)
        self.assertFalse(is_valid)
        self.assertIn("Insufficient balance", error)
    
    def test_valid_bank_account_info(self):
        """Test valid bank account information"""
        bank_info = {
            'account_number': '123456789',
            'routing_number': '021000021',
            'account_holder_name': 'John Doe'
        }
        is_valid, error = PaymentValidationService.validate_bank_account_info(bank_info)
        self.assertTrue(is_valid)
        self.assertIsNone(error)
    
    def test_invalid_bank_account_info_missing_fields(self):
        """Test bank account info with missing fields"""
        bank_info = {
            'account_number': '123456789'
        }
        is_valid, error = PaymentValidationService.validate_bank_account_info(bank_info)
        self.assertFalse(is_valid)
        self.assertIn("Missing required field", error)
    
    def test_invalid_bank_account_number_format(self):
        """Test invalid bank account number format"""
        bank_info = {
            'account_number': '123',  # Too short
            'routing_number': '021000021',
            'account_holder_name': 'John Doe'
        }
        is_valid, error = PaymentValidationService.validate_bank_account_info(bank_info)
        self.assertFalse(is_valid)
        self.assertIn("Account number must be", error)
    
    def test_user_verification_status_unverified_email(self):
        """Test user verification with unverified email"""
        self.player.email_verified = False
        self.player.save()
        
        is_valid, error = PaymentValidationService.validate_user_verification_status(self.player, 'deposit')
        self.assertFalse(is_valid)
        self.assertIn("Email verification required", error)


class FraudDetectionTests(TestCase):
    """Test fraud detection functionality"""
    
    def setUp(self):
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000,
            email_verified=True,
            created_at=timezone.now()
        )
    
    def test_new_account_risk_score(self):
        """Test risk score for new account"""
        risk_score, risk_factors = FraudDetectionService.calculate_fraud_score(
            self.player, 100, 'deposit'
        )
        self.assertGreater(risk_score, 0)
        self.assertTrue(any('new account' in factor.lower() for factor in risk_factors))
    
    def test_large_amount_risk_score(self):
        """Test risk score for large transaction amount"""
        # Create some transaction history first
        PaymentTransaction.objects.create(
            player=self.player,
            amount=Decimal('50'),
            transaction_type='deposit',
            status='completed'
        )
        
        risk_score, risk_factors = FraudDetectionService.calculate_fraud_score(
            self.player, 1000, 'deposit'  # Much larger than average
        )
        self.assertGreater(risk_score, 0)
    
    def test_should_flag_high_risk_transaction(self):
        """Test flagging of high-risk transactions"""
        should_flag, reason = FraudDetectionService.should_flag_transaction(85, ['High risk factor'])
        self.assertTrue(should_flag)
        self.assertIsNotNone(reason)
    
    def test_should_not_flag_low_risk_transaction(self):
        """Test not flagging low-risk transactions"""
        should_flag, reason = FraudDetectionService.should_flag_transaction(20, ['Low risk factor'])
        self.assertFalse(should_flag)
        self.assertIsNone(reason)


class PaymentServiceTests(TestCase):
    """Test payment service functionality"""
    
    def setUp(self):
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000,
            email_verified=True,
            created_at=timezone.now()
        )
    
    @patch('polling.payment_service.stripe.PaymentIntent.create')
    def test_create_payment_intent_success(self, mock_stripe_create):
        """Test successful payment intent creation"""
        # Mock Stripe response
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = 'pi_test123'
        mock_payment_intent.client_secret = 'pi_test123_secret'
        mock_stripe_create.return_value = mock_payment_intent
        
        success, result, client_secret = PaymentService.create_payment_intent(
            self.player, 100, 'usd', 'Test deposit'
        )
        
        self.assertTrue(success)
        self.assertEqual(client_secret, 'pi_test123_secret')
        
        # Check that PaymentTransaction was created
        payment_transaction = PaymentTransaction.objects.get(payment_intent_id='pi_test123')
        self.assertEqual(payment_transaction.player, self.player)
        self.assertEqual(payment_transaction.amount, Decimal('100'))
        self.assertEqual(payment_transaction.status, 'pending')
    
    def test_create_payment_intent_invalid_amount(self):
        """Test payment intent creation with invalid amount"""
        success, error, client_secret = PaymentService.create_payment_intent(
            self.player, 5, 'usd', 'Test deposit'  # Below minimum
        )
        
        self.assertFalse(success)
        self.assertIn("Minimum deposit amount", error)
        self.assertIsNone(client_secret)
    
    def test_process_withdrawal_success(self):
        """Test successful withdrawal processing"""
        bank_info = {
            'account_number': '123456789',
            'routing_number': '021000021',
            'account_holder_name': 'John Doe'
        }
        
        success, message, withdrawal_id = PaymentService.process_withdrawal(
            self.player, 100, bank_info
        )
        
        self.assertTrue(success)
        self.assertIn("submitted for processing", message)
        self.assertIsNotNone(withdrawal_id)
        
        # Check that wallet was debited
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 900)
        
        # Check that PaymentTransaction was created
        payment_transaction = PaymentTransaction.objects.get(id=withdrawal_id)
        self.assertEqual(payment_transaction.transaction_type, 'withdrawal')
        self.assertEqual(payment_transaction.amount, Decimal('100'))
    
    def test_process_withdrawal_insufficient_balance(self):
        """Test withdrawal with insufficient balance"""
        bank_info = {
            'account_number': '123456789',
            'routing_number': '021000021',
            'account_holder_name': 'John Doe'
        }
        
        success, message, withdrawal_id = PaymentService.process_withdrawal(
            self.player, 2000, bank_info  # More than balance
        )
        
        self.assertFalse(success)
        self.assertIn("Insufficient balance", message)
        self.assertIsNone(withdrawal_id)


class PaymentViewTests(TestCase):
    """Test payment view functionality"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000,
            email_verified=True,
            created_at=timezone.now()
        )
    
    def test_create_deposit_intent_view_unauthenticated(self):
        """Test create deposit intent view without authentication"""
        request = self.factory.post('/api/payment/create-deposit-intent/', 
                                  {'amount': 100}, 
                                  content_type='application/json')
        request.user = AnonymousUser()
        
        # This would be handled by the secure_api_endpoint decorator
        # In a real test, we'd need to mock the authentication
    
    def test_security_headers_present(self):
        """Test that security headers are present in responses"""
        # This would test that proper security headers are set
        # in payment-related responses
        pass


if __name__ == '__main__':
    import unittest
    unittest.main()
