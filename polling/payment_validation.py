"""
Payment Validation Service for comprehensive payment security
"""
import re
import logging
from decimal import Decimal, InvalidOperation
from django.conf import settings
from django.utils import timezone
from django.db import models
from datetime import datetime, timedelta
from .models import Player, PaymentTransaction

logger = logging.getLogger(__name__)

class PaymentValidationService:
    """Service for validating payment operations"""
    
    @staticmethod
    def validate_deposit_amount(amount):
        """
        Validate deposit amount
        Returns (is_valid, error_message)
        """
        try:
            # Convert to decimal for precise validation
            amount_decimal = Decimal(str(amount))
            
            # Check if amount is positive
            if amount_decimal <= 0:
                return False, "Deposit amount must be positive"
            
            # Check minimum amount
            min_amount = getattr(settings, 'MIN_DEPOSIT_AMOUNT', 10)
            if amount_decimal < min_amount:
                return False, f"Minimum deposit amount is ₹{min_amount}"

            # Check maximum amount
            max_amount = getattr(settings, 'MAX_DEPOSIT_AMOUNT', 10000)
            if amount_decimal > max_amount:
                return False, f"Maximum deposit amount is ₹{max_amount}"
            
            # Check for reasonable decimal places (max 2)
            if amount_decimal.as_tuple().exponent < -2:
                return False, "Amount cannot have more than 2 decimal places"
            
            return True, None
            
        except (ValueError, InvalidOperation):
            return False, "Invalid amount format"
    
    @staticmethod
    def validate_withdrawal_amount(player, amount):
        """
        Validate withdrawal amount
        Returns (is_valid, error_message)
        """
        try:
            # Convert to decimal for precise validation
            amount_decimal = Decimal(str(amount))
            
            # Check if amount is positive
            if amount_decimal <= 0:
                return False, "Withdrawal amount must be positive"
            
            # Check minimum amount
            min_amount = getattr(settings, 'MIN_WITHDRAWAL_AMOUNT', 20)
            if amount_decimal < min_amount:
                return False, f"Minimum withdrawal amount is ₹{min_amount}"

            # Check maximum amount
            max_amount = getattr(settings, 'MAX_WITHDRAWAL_AMOUNT', 5000)
            if amount_decimal > max_amount:
                return False, f"Maximum withdrawal amount is ₹{max_amount}"

            # Check if player has sufficient balance
            if amount_decimal > player.balance:
                return False, f"Insufficient balance. Available: ₹{player.balance}"
            
            # Check for reasonable decimal places (max 2)
            if amount_decimal.as_tuple().exponent < -2:
                return False, "Amount cannot have more than 2 decimal places"
            
            return True, None
            
        except (ValueError, InvalidOperation):
            return False, "Invalid amount format"
    
    @staticmethod
    def validate_bank_account_info(bank_info):
        """
        Validate bank account information for withdrawals
        Returns (is_valid, error_message)
        """
        if not isinstance(bank_info, dict):
            return False, "Bank account information must be provided"
        
        # Required fields
        required_fields = ['account_number', 'routing_number', 'account_holder_name']
        for field in required_fields:
            if not bank_info.get(field):
                return False, f"Missing required field: {field}"
        
        # Validate account number (Indian format - 9-18 digits)
        account_number = str(bank_info['account_number']).strip()
        if not re.match(r'^\d{9,18}$', account_number):
            return False, "Account number must be 9-18 digits"

        # Validate IFSC code (Indian format - 11 characters: 4 letters + 7 alphanumeric)
        ifsc_code = str(bank_info['routing_number']).strip().upper()
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', ifsc_code):
            return False, "IFSC code must be 11 characters (e.g., SBIN0001234)"
        
        # Validate account holder name
        account_holder_name = str(bank_info['account_holder_name']).strip()
        if len(account_holder_name) < 2 or len(account_holder_name) > 100:
            return False, "Account holder name must be 2-100 characters"
        
        if not re.match(r'^[a-zA-Z\s\-\.\']+$', account_holder_name):
            return False, "Account holder name contains invalid characters"
        
        return True, None
    
    @staticmethod
    def validate_daily_limits(player, amount, transaction_type):
        """
        Validate daily transaction limits
        Returns (is_valid, error_message)
        """
        today = timezone.now().date()

        # Convert amount to Decimal for consistent calculations
        amount_decimal = Decimal(str(amount))

        if transaction_type == 'deposit':
            # Check daily deposit limit
            daily_deposits = PaymentTransaction.objects.filter(
                player=player,
                transaction_type='deposit',
                status='completed',
                created_at__date=today
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

            max_daily_limit = Decimal(str(getattr(settings, 'MAX_DAILY_DEPOSIT_LIMIT', 50000)))

            if daily_deposits + amount_decimal > max_daily_limit:
                remaining = max_daily_limit - daily_deposits
                return False, f"Daily deposit limit exceeded. Remaining limit: ₹{remaining}"
        
        elif transaction_type == 'withdrawal':
            # Check daily withdrawal limit
            daily_withdrawals = PaymentTransaction.objects.filter(
                player=player,
                transaction_type='withdrawal',
                status__in=['completed', 'pending', 'processing'],
                created_at__date=today
            ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0')

            max_daily_limit = Decimal(str(getattr(settings, 'MAX_DAILY_WITHDRAWAL_LIMIT', 25000)))

            if daily_withdrawals + amount_decimal > max_daily_limit:
                remaining = max_daily_limit - daily_withdrawals
                return False, f"Daily withdrawal limit exceeded. Remaining limit: ₹{remaining}"
        
        return True, None
    
    @staticmethod
    def validate_user_verification_status(player, transaction_type):
        """
        Validate user verification status for transactions
        Returns (is_valid, error_message)
        """
        # Email verification required for all transactions
        if not player.email_verified:
            return False, "Email verification required before making transactions"
        
        # Additional verification for withdrawals
        if transaction_type == 'withdrawal':
            # Check if account is old enough for withdrawals
            account_age_hours = (timezone.now() - player.created_at).total_seconds() / 3600
            min_account_age = getattr(settings, 'MIN_ACCOUNT_AGE_FOR_WITHDRAWAL_HOURS', 24)
            
            if account_age_hours < min_account_age:
                return False, f"Account must be at least {min_account_age} hours old for withdrawals"
            
            # Check if player has made at least one successful deposit
            successful_deposits = PaymentTransaction.objects.filter(
                player=player,
                transaction_type='deposit',
                status='completed'
            ).exists()
            
            if not successful_deposits:
                return False, "At least one successful deposit required before withdrawals"
        
        return True, None
    
    @staticmethod
    def validate_transaction_frequency(player, transaction_type):
        """
        Validate transaction frequency to prevent abuse
        Returns (is_valid, error_message)
        """
        # Check recent transaction count
        recent_cutoff = timezone.now() - timedelta(minutes=10)
        recent_transactions = PaymentTransaction.objects.filter(
            player=player,
            transaction_type=transaction_type,
            created_at__gte=recent_cutoff
        ).count()
        
        max_frequency = {
            'deposit': 3,  # Max 3 deposits per 10 minutes
            'withdrawal': 1  # Max 1 withdrawal per 10 minutes
        }
        
        if recent_transactions >= max_frequency.get(transaction_type, 1):
            return False, f"Too many {transaction_type} attempts. Please wait before trying again."
        
        return True, None
    
    @staticmethod
    def validate_payment_method_security(payment_data):
        """
        Validate payment method security
        Returns (is_valid, error_message)
        """
        # This would integrate with payment processor's fraud detection
        # For now, basic validation
        
        if not payment_data:
            return False, "Payment method information required"
        
        # Add more specific validation based on payment method
        return True, None
    
    @staticmethod
    def comprehensive_payment_validation(player, amount, transaction_type, **kwargs):
        """
        Perform comprehensive payment validation
        Returns (is_valid, error_messages_list)
        """
        errors = []
        
        # Amount validation
        if transaction_type == 'deposit':
            is_valid, error = PaymentValidationService.validate_deposit_amount(amount)
        else:
            is_valid, error = PaymentValidationService.validate_withdrawal_amount(player, amount)
        
        if not is_valid:
            errors.append(error)
        
        # Daily limits validation
        is_valid, error = PaymentValidationService.validate_daily_limits(player, amount, transaction_type)
        if not is_valid:
            errors.append(error)
        
        # User verification validation
        is_valid, error = PaymentValidationService.validate_user_verification_status(player, transaction_type)
        if not is_valid:
            errors.append(error)
        
        # Transaction frequency validation
        is_valid, error = PaymentValidationService.validate_transaction_frequency(player, transaction_type)
        if not is_valid:
            errors.append(error)
        
        # Bank account validation for withdrawals
        if transaction_type == 'withdrawal' and 'bank_account_info' in kwargs:
            is_valid, error = PaymentValidationService.validate_bank_account_info(kwargs['bank_account_info'])
            if not is_valid:
                errors.append(error)
        
        return len(errors) == 0, errors
