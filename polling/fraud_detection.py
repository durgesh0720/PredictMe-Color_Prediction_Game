"""
Fraud Detection System for Payment Security
"""
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Q
from django.conf import settings
from .models import PaymentTransaction, Transaction, Player
from .security import get_client_ip

logger = logging.getLogger(__name__)

class FraudDetectionService:
    """Service for detecting fraudulent payment activities"""
    
    # Risk score thresholds
    LOW_RISK = 25
    MEDIUM_RISK = 50
    HIGH_RISK = 75
    CRITICAL_RISK = 90
    
    @staticmethod
    def calculate_fraud_score(player, amount, transaction_type, request=None):
        """
        Calculate fraud risk score (0-100)
        Returns (risk_score, risk_factors)
        """
        risk_score = 0
        risk_factors = []
        
        try:
            # Factor 1: Account age (newer accounts are riskier)
            account_age_days = (timezone.now() - player.created_at).days
            if account_age_days < 1:
                risk_score += 30
                risk_factors.append("Very new account (less than 1 day)")
            elif account_age_days < 7:
                risk_score += 20
                risk_factors.append("New account (less than 1 week)")
            elif account_age_days < 30:
                risk_score += 10
                risk_factors.append("Recent account (less than 1 month)")
            
            # Factor 2: Transaction amount relative to account history
            avg_transaction = FraudDetectionService._get_average_transaction_amount(player)
            if avg_transaction > 0:
                amount_ratio = amount / avg_transaction
                if amount_ratio > 10:
                    risk_score += 25
                    risk_factors.append(f"Transaction amount {amount_ratio:.1f}x higher than average")
                elif amount_ratio > 5:
                    risk_score += 15
                    risk_factors.append(f"Transaction amount {amount_ratio:.1f}x higher than average")
                elif amount_ratio > 3:
                    risk_score += 10
                    risk_factors.append(f"Transaction amount {amount_ratio:.1f}x higher than average")
            
            # Factor 3: Transaction frequency
            recent_transactions = FraudDetectionService._get_recent_transaction_count(player, hours=24)
            if recent_transactions > 10:
                risk_score += 20
                risk_factors.append(f"High transaction frequency: {recent_transactions} in 24h")
            elif recent_transactions > 5:
                risk_score += 10
                risk_factors.append(f"Elevated transaction frequency: {recent_transactions} in 24h")
            
            # Factor 4: Failed payment attempts
            failed_payments = FraudDetectionService._get_failed_payment_count(player, hours=24)
            if failed_payments > 3:
                risk_score += 25
                risk_factors.append(f"Multiple failed payments: {failed_payments} in 24h")
            elif failed_payments > 1:
                risk_score += 15
                risk_factors.append(f"Recent failed payments: {failed_payments} in 24h")
            
            # Factor 5: IP address changes
            if request:
                ip_changes = FraudDetectionService._check_ip_changes(player, request)
                if ip_changes > 3:
                    risk_score += 20
                    risk_factors.append(f"Multiple IP addresses used: {ip_changes} in 24h")
                elif ip_changes > 1:
                    risk_score += 10
                    risk_factors.append(f"IP address changes: {ip_changes} in 24h")
            
            # Factor 6: Large withdrawal after deposit (potential money laundering)
            if transaction_type == 'withdrawal':
                recent_deposits = FraudDetectionService._get_recent_deposits(player, hours=72)
                if recent_deposits > 0 and amount >= recent_deposits * 0.8:
                    risk_score += 30
                    risk_factors.append("Large withdrawal shortly after deposit")
            
            # Factor 7: Email verification status
            if not player.email_verified:
                risk_score += 15
                risk_factors.append("Email not verified")
            
            # Factor 8: Unusual time patterns
            current_hour = timezone.now().hour
            if current_hour < 6 or current_hour > 23:  # Late night/early morning
                risk_score += 5
                risk_factors.append("Transaction during unusual hours")
            
            # Factor 9: Account balance patterns
            if transaction_type == 'deposit':
                if player.balance == 0 and amount > 1000:
                    risk_score += 15
                    risk_factors.append("Large first deposit on empty account")
            
            # Cap the risk score at 100
            risk_score = min(risk_score, 100)
            
            return risk_score, risk_factors
            
        except Exception as e:
            logger.error(f"Error calculating fraud score: {e}")
            return 50, ["Error calculating risk score"]  # Default to medium risk
    
    @staticmethod
    def _get_average_transaction_amount(player):
        """Get average transaction amount for player"""
        avg_amount = PaymentTransaction.objects.filter(
            player=player,
            status='completed'
        ).aggregate(avg=Sum('amount'))['avg']
        return float(avg_amount) if avg_amount else 0
    
    @staticmethod
    def _get_recent_transaction_count(player, hours=24):
        """Get count of recent transactions"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        return PaymentTransaction.objects.filter(
            player=player,
            created_at__gte=cutoff_time
        ).count()
    
    @staticmethod
    def _get_failed_payment_count(player, hours=24):
        """Get count of failed payments"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        return PaymentTransaction.objects.filter(
            player=player,
            status='failed',
            created_at__gte=cutoff_time
        ).count()
    
    @staticmethod
    def _check_ip_changes(player, request):
        """Check for IP address changes"""
        current_ip = get_client_ip(request)
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        unique_ips = PaymentTransaction.objects.filter(
            player=player,
            created_at__gte=cutoff_time,
            ip_address__isnull=False
        ).values('ip_address').distinct().count()
        
        return unique_ips
    
    @staticmethod
    def _get_recent_deposits(player, hours=72):
        """Get total recent deposits"""
        cutoff_time = timezone.now() - timedelta(hours=hours)
        total_deposits = PaymentTransaction.objects.filter(
            player=player,
            transaction_type='deposit',
            status='completed',
            created_at__gte=cutoff_time
        ).aggregate(total=Sum('amount'))['total']
        
        return float(total_deposits) if total_deposits else 0
    
    @staticmethod
    def should_flag_transaction(risk_score, risk_factors):
        """Determine if transaction should be flagged for review"""
        if risk_score >= FraudDetectionService.CRITICAL_RISK:
            return True, "Critical risk - requires immediate review"
        elif risk_score >= FraudDetectionService.HIGH_RISK:
            return True, "High risk - requires manual review"
        elif len(risk_factors) >= 5:
            return True, "Multiple risk factors detected"
        
        return False, None
    
    @staticmethod
    def log_fraud_detection(player, transaction_type, amount, risk_score, risk_factors, flagged=False):
        """Log fraud detection results"""
        logger.info(
            f"Fraud detection - Player: {player.username}, "
            f"Type: {transaction_type}, Amount: ₹{amount}, "
            f"Risk Score: {risk_score}, Flagged: {flagged}, "
            f"Factors: {', '.join(risk_factors)}"
        )
        
        # Log to security logger if high risk
        if risk_score >= FraudDetectionService.HIGH_RISK:
            security_logger = logging.getLogger('polling.security')
            security_logger.warning(
                f"High-risk transaction detected - Player: {player.username}, "
                f"Risk Score: {risk_score}, Factors: {risk_factors}"
            )


class TransactionVerificationService:
    """Service for transaction verification and audit"""
    
    @staticmethod
    def verify_transaction_integrity(transaction):
        """Verify transaction integrity"""
        try:
            # Check if balance calculations are correct
            expected_balance = transaction.balance_before
            if transaction.amount > 0:  # Credit
                expected_balance += transaction.amount
            else:  # Debit
                expected_balance += transaction.amount  # amount is already negative
            
            if expected_balance != transaction.balance_after:
                logger.error(
                    f"Transaction integrity error - ID: {transaction.id}, "
                    f"Expected balance: {expected_balance}, "
                    f"Actual balance: {transaction.balance_after}"
                )
                return False, "Balance calculation error"
            
            return True, "Transaction verified"
            
        except Exception as e:
            logger.error(f"Error verifying transaction integrity: {e}")
            return False, "Verification error"
    
    @staticmethod
    def audit_wallet_balance(player):
        """Audit player wallet balance against transaction history"""
        try:
            # Calculate balance from transaction history
            transactions = Transaction.objects.filter(player=player).order_by('created_at')
            calculated_balance = 0
            
            for transaction in transactions:
                calculated_balance += transaction.amount
            
            # Compare with current balance
            if calculated_balance != player.balance:
                logger.error(
                    f"Wallet balance mismatch - Player: {player.username}, "
                    f"Calculated: {calculated_balance}, "
                    f"Current: {player.balance}"
                )
                return False, f"Balance mismatch: calculated {calculated_balance}, current {player.balance}"
            
            return True, "Wallet balance verified"
            
        except Exception as e:
            logger.error(f"Error auditing wallet balance: {e}")
            return False, "Audit error"
