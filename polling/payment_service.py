"""
Payment Service for handling Razorpay payments and wallet operations
"""
import razorpay
import logging
import json
import hmac
import hashlib
from decimal import Decimal
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from django.db import models
from .models import Player, Transaction, PaymentTransaction
from .security import get_client_ip
from .fraud_detection import FraudDetectionService
from .payment_validation import PaymentValidationService

logger = logging.getLogger(__name__)

# Configure Razorpay
razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

class PaymentService:
    """Service for handling payment operations with Razorpay"""

    @staticmethod
    def create_order(player, amount, currency='INR', description=None, request=None):
        """
        Create a Razorpay Order for deposit
        Returns (success, order_or_error, order_data)
        """
        try:
            # Comprehensive validation
            is_valid, validation_errors = PaymentValidationService.comprehensive_payment_validation(
                player, amount, 'deposit'
            )

            if not is_valid:
                return False, "; ".join(validation_errors), None

            # Fraud detection
            risk_score, risk_factors = FraudDetectionService.calculate_fraud_score(
                player, amount, 'deposit', request
            )

            should_flag, flag_reason = FraudDetectionService.should_flag_transaction(
                risk_score, risk_factors
            )

            # Log fraud detection
            FraudDetectionService.log_fraud_detection(
                player, 'deposit', amount, risk_score, risk_factors, should_flag
            )

            # Block high-risk transactions
            if risk_score >= FraudDetectionService.CRITICAL_RISK:
                return False, "Transaction blocked due to security concerns. Please contact support.", None

            # Convert amount to paise (smallest currency unit for INR)
            amount_paise = int(amount * 100)

            # Create Razorpay order
            order_data = {
                'amount': amount_paise,
                'currency': currency,
                'receipt': f'order_{player.id}_{int(timezone.now().timestamp())}',
                'notes': {
                    'player_id': str(player.id),
                    'player_username': player.username,
                    'description': description or f'Wallet deposit for {player.username}',
                    'timestamp': timezone.now().isoformat()
                }
            }

            order = razorpay_client.order.create(data=order_data)

            # Create payment transaction record
            payment_transaction = PaymentTransaction.objects.create(
                player=player,
                razorpay_order_id=order['id'],
                amount=amount,
                currency=currency,
                transaction_type='deposit',
                status='pending',
                description=description or f'Wallet deposit of ₹{amount}',
                fraud_score=risk_score,
                is_flagged=should_flag,
                ip_address=get_client_ip(request) if request else None,
                user_agent=request.META.get('HTTP_USER_AGENT', '') if request else ''
            )

            logger.info(f"Razorpay order created for player {player.username}: {order['id']}")

            return True, order, order

        except Exception as e:
            if 'razorpay' in str(type(e)).lower():
                logger.error(f"Razorpay error creating order: {e}")
                return False, f"Payment processing error: {str(e)}", None
            else:
                logger.error(f"Error creating order: {e}")
                return False, "An error occurred while processing your request", None
    
    @staticmethod
    def verify_payment(razorpay_order_id, razorpay_payment_id, razorpay_signature, request=None):
        """
        Verify Razorpay payment and credit user wallet
        Returns (success, message, amount_credited)
        """
        try:
            with transaction.atomic():
                # Get payment transaction
                payment_transaction = PaymentTransaction.objects.select_for_update().get(
                    razorpay_order_id=razorpay_order_id
                )

                if payment_transaction.status != 'pending':
                    return False, "Payment already processed", 0

                # Verify payment signature
                params_dict = {
                    'razorpay_order_id': razorpay_order_id,
                    'razorpay_payment_id': razorpay_payment_id,
                    'razorpay_signature': razorpay_signature
                }

                try:
                    razorpay_client.utility.verify_payment_signature(params_dict)
                    signature_valid = True
                except razorpay.errors.SignatureVerificationError:
                    signature_valid = False

                if signature_valid:
                    # Fetch payment details from Razorpay
                    payment_details = razorpay_client.payment.fetch(razorpay_payment_id)

                    if payment_details['status'] == 'captured':
                        # Credit user wallet
                        player = payment_transaction.player
                        amount = payment_transaction.amount

                        try:
                            # Credit wallet with real money tracking
                            player.credit_wallet(
                                amount=amount,
                                transaction_type='deposit',
                                description=f'Razorpay deposit - Payment ID: {razorpay_payment_id}',
                                involves_real_money=True,
                                payment_transaction_id=str(payment_transaction.id)
                            )
                        except Exception as wallet_error:
                            logger.error(f"Error crediting wallet: {wallet_error}")

                            # Fallback: Update balance directly if credit_wallet fails
                            try:
                                player.balance += amount
                                player.save()

                                # Create basic transaction record
                                Transaction.objects.create(
                                    player=player,
                                    transaction_type='deposit',
                                    amount=amount,
                                    balance_before=player.balance - amount,
                                    balance_after=player.balance,
                                    description=f'Razorpay deposit (direct) - Payment ID: {razorpay_payment_id}'
                                )

                                logger.info(f"Used fallback method to credit wallet for player {player.username}: ₹{amount}")
                            except Exception as fallback_error:
                                logger.error(f"Fallback wallet credit also failed: {fallback_error}")
                                return False, "Failed to credit your wallet. Please contact support.", 0

                        # Update payment transaction
                        payment_transaction.status = 'completed'
                        payment_transaction.completed_at = timezone.now()
                        payment_transaction.razorpay_payment_id = razorpay_payment_id
                        payment_transaction.razorpay_signature = razorpay_signature
                        if request:
                            payment_transaction.ip_address = get_client_ip(request)
                        payment_transaction.save()

                        logger.info(f"Payment verified for player {player.username}: ₹{amount}")

                        return True, f"Successfully deposited ₹{amount} to your wallet", amount

                    else:
                        payment_transaction.status = 'failed'
                        payment_transaction.error_message = f'Payment status: {payment_details["status"]}'
                        payment_transaction.save()
                        return False, f"Payment failed with status: {payment_details['status']}", 0

                else:
                    payment_transaction.status = 'failed'
                    payment_transaction.error_message = 'Invalid payment signature'
                    payment_transaction.save()
                    return False, "Payment verification failed", 0
                    
        except PaymentTransaction.DoesNotExist:
            logger.error(f"Payment transaction not found: {razorpay_order_id}")
            return False, "Payment transaction not found", 0
        except Exception as e:
            if 'razorpay' in str(type(e)).lower():
                logger.error(f"Razorpay error verifying payment: {e}")
                return False, f"Payment verification error: {str(e)}", 0
        except Exception as e:
            logger.error(f"Error verifying payment: {e}")
            return False, "An error occurred while verifying payment", 0
    
    @staticmethod
    def process_withdrawal(player, amount, bank_account_info=None, request=None):
        """
        Process withdrawal request
        Returns (success, message, withdrawal_id)
        """
        try:
            # Comprehensive validation
            is_valid, validation_errors = PaymentValidationService.comprehensive_payment_validation(
                player, amount, 'withdrawal', bank_account_info=bank_account_info
            )

            if not is_valid:
                return False, "; ".join(validation_errors), None

            # Fraud detection for withdrawals
            risk_score, risk_factors = FraudDetectionService.calculate_fraud_score(
                player, amount, 'withdrawal', request
            )

            should_flag, flag_reason = FraudDetectionService.should_flag_transaction(
                risk_score, risk_factors
            )

            # Log fraud detection
            FraudDetectionService.log_fraud_detection(
                player, 'withdrawal', amount, risk_score, risk_factors, should_flag
            )

            # Block high-risk withdrawals
            if risk_score >= FraudDetectionService.CRITICAL_RISK:
                return False, "Withdrawal blocked due to security concerns. Please contact support.", None
            
            with transaction.atomic():
                # Create withdrawal request using new real money system
                try:
                    withdrawal_request = player.request_withdrawal(
                        amount=amount,
                        bank_account_number=bank_account_info.get('account_number', ''),
                        bank_ifsc_code=bank_account_info.get('routing_number', ''),
                        bank_name=bank_account_info.get('bank_name', 'Not specified'),
                        account_holder_name=bank_account_info.get('account_holder_name', '')
                    )

                    # Create legacy PaymentTransaction for backward compatibility
                    withdrawal_transaction = PaymentTransaction.objects.create(
                        player=player,
                        amount=amount,
                        transaction_type='withdrawal',
                        status='pending' if not should_flag else 'processing',
                        description=f'Withdrawal request of ₹{amount}',
                        bank_account_info=json.dumps(bank_account_info) if bank_account_info else None,
                        fraud_score=risk_score,
                        is_flagged=should_flag,
                        ip_address=get_client_ip(request) if request else None,
                        user_agent=request.META.get('HTTP_USER_AGENT', '') if request else '',
                        admin_notes=flag_reason if should_flag else ''
                    )

                    logger.info(f"Withdrawal request created for player {player.username}: ₹{amount}")

                    return True, f"Withdrawal request of ₹{amount} submitted for admin approval. Processing time: 24-48 hours.", str(withdrawal_request.id)

                except ValueError as e:
                    return False, str(e), None
                
        except Exception as e:
            logger.error(f"Error processing withdrawal: {e}")
            return False, "An error occurred while processing withdrawal", None
    
    @staticmethod
    def _check_daily_deposit_limit(player, amount):
        """Check if deposit amount exceeds daily limit"""
        today = timezone.now().date()
        daily_deposits = PaymentTransaction.objects.filter(
            player=player,
            transaction_type='deposit',
            status='completed',
            created_at__date=today
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        max_daily_limit = getattr(settings, 'MAX_DAILY_DEPOSIT_LIMIT', 50000)
        
        if daily_deposits + amount > max_daily_limit:
            return False, f"Daily deposit limit of ${max_daily_limit} would be exceeded"
        
        return True, None
    
    @staticmethod
    def _check_daily_withdrawal_limit(player, amount):
        """Check if withdrawal amount exceeds daily limit"""
        today = timezone.now().date()
        daily_withdrawals = PaymentTransaction.objects.filter(
            player=player,
            transaction_type='withdrawal',
            status__in=['completed', 'pending'],
            created_at__date=today
        ).aggregate(total=models.Sum('amount'))['total'] or 0
        
        max_daily_limit = getattr(settings, 'MAX_DAILY_WITHDRAWAL_LIMIT', 25000)
        
        if daily_withdrawals + amount > max_daily_limit:
            return False, f"Daily withdrawal limit of ${max_daily_limit} would be exceeded"
        
        return True, None
    
    @staticmethod
    def handle_webhook(payload, sig_header):
        """
        Handle Razorpay webhook events
        Returns (success, message)
        """
        try:
            # Verify webhook signature
            expected_signature = hmac.new(
                settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()

            if not hmac.compare_digest(expected_signature, sig_header):
                logger.error("Invalid webhook signature")
                return False, "Invalid signature"

            # Parse webhook payload
            event = json.loads(payload.decode('utf-8'))

            if event['event'] == 'payment.captured':
                payment_data = event['payload']['payment']['entity']
                order_id = payment_data['order_id']
                payment_id = payment_data['id']

                try:
                    payment_transaction = PaymentTransaction.objects.get(
                        razorpay_order_id=order_id
                    )

                    if payment_transaction.status == 'pending':
                        # Update payment transaction
                        payment_transaction.status = 'completed'
                        payment_transaction.completed_at = timezone.now()
                        payment_transaction.razorpay_payment_id = payment_id
                        payment_transaction.save()

                        # Credit user wallet with real money tracking
                        payment_transaction.player.credit_wallet(
                            amount=payment_transaction.amount,
                            transaction_type='deposit',
                            description=f'Razorpay webhook deposit - Payment ID: {payment_id}',
                            involves_real_money=True,
                            payment_transaction_id=str(payment_transaction.id)
                        )

                        logger.info(f"Webhook processed payment.captured: {payment_id}")

                except PaymentTransaction.DoesNotExist:
                    logger.error(f"Payment transaction not found for order: {order_id}")

            elif event['event'] == 'payment.failed':
                payment_data = event['payload']['payment']['entity']
                order_id = payment_data['order_id']

                try:
                    payment_transaction = PaymentTransaction.objects.get(
                        razorpay_order_id=order_id
                    )
                    payment_transaction.status = 'failed'
                    payment_transaction.error_message = payment_data.get('error_description', 'Payment failed')
                    payment_transaction.save()
                    logger.info(f"Payment failed for order: {order_id}")
                except PaymentTransaction.DoesNotExist:
                    logger.error(f"Payment transaction not found for failed payment: {order_id}")

            # Handle payout webhooks for withdrawals
            elif event['event'] in ['payout.processed', 'payout.failed', 'payout.reversed']:
                payout_data = event['payload']['payout']['entity']
                payout_id = payout_data['id']
                payout_status = payout_data['status']

                try:
                    from .models import WithdrawalRequest
                    withdrawal = WithdrawalRequest.objects.get(payment_reference=payout_id)
                    success, message = withdrawal.handle_payout_webhook(event)

                    if success:
                        logger.info(f"Payout webhook processed: {payout_id} - {message}")
                    else:
                        logger.error(f"Payout webhook error: {payout_id} - {message}")

                except WithdrawalRequest.DoesNotExist:
                    logger.error(f"Withdrawal request not found for payout: {payout_id}")

            return True, "Webhook processed successfully"

        except json.JSONDecodeError as e:
            logger.error(f"Invalid webhook payload JSON: {e}")
            return False, "Invalid payload"
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False, "Webhook processing error"
