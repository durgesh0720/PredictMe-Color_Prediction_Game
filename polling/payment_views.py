"""
Payment Views for handling secure payment operations
"""
import json
import logging
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views import View

from .decorators import secure_api_endpoint
from .auth_views import auth_required
from .payment_service import PaymentService
from .models import PaymentTransaction, Transaction
from .security import get_client_ip

logger = logging.getLogger(__name__)


@auth_required
def payment_dashboard(request):
    """Payment dashboard showing deposit/withdrawal options"""
    # Get recent payment transactions
    recent_payments = PaymentTransaction.objects.filter(
        player=request.user
    ).order_by('-created_at')[:10]
    
    # Get recent wallet transactions
    recent_transactions = Transaction.objects.filter(
        player=request.user
    ).order_by('-created_at')[:10]
    
    context = {
        'player': request.user,
        'recent_payments': recent_payments,
        'recent_transactions': recent_transactions,
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'min_deposit': settings.MIN_DEPOSIT_AMOUNT,
        'max_deposit': settings.MAX_DEPOSIT_AMOUNT,
        'min_withdrawal': settings.MIN_WITHDRAWAL_AMOUNT,
        'max_withdrawal': settings.MAX_WITHDRAWAL_AMOUNT,
    }
    
    return render(request, 'payment/dashboard.html', context)


@secure_api_endpoint(
    authentication_required=True,
    require_json=True,
    required_fields=['amount'],
    allowed_methods=['POST'],
    rate_limit_per_minute=5,  # Strict rate limiting for payment operations
    rate_limit_per_hour=20
)
def create_deposit_order(request):
    """Create Razorpay Order for deposit"""
    try:
        data = request.json
        amount = float(data.get('amount', 0))
        description = data.get('description', '')
        currency = data.get('currency', 'INR')

        # Create Razorpay order
        success, result, order_data = PaymentService.create_order(
            player=request.player,
            amount=amount,
            currency=currency,
            description=description,
            request=request
        )

        if success:
            return JsonResponse({
                'success': True,
                'order_id': result['id'],
                'amount': result['amount'],
                'currency': result['currency'],
                'key_id': settings.RAZORPAY_KEY_ID,
                'order_data': result
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result
            })
            
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid deposit request from {request.player.username}: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Invalid amount format'
        })
    except Exception as e:
        logger.error(f"Error creating deposit intent: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while processing your request'
        })


@secure_api_endpoint(
    authentication_required=True,
    require_json=True,
    required_fields=['razorpay_order_id', 'razorpay_payment_id', 'razorpay_signature'],
    allowed_methods=['POST'],
    rate_limit_per_minute=10,
    rate_limit_per_hour=50
)
def verify_payment(request):
    """Verify Razorpay payment after successful payment"""
    try:
        data = request.json
        razorpay_order_id = data.get('razorpay_order_id')
        razorpay_payment_id = data.get('razorpay_payment_id')
        razorpay_signature = data.get('razorpay_signature')

        # Log payment verification attempt
        logger.info(f"Payment verification attempt: Order ID: {razorpay_order_id}, Payment ID: {razorpay_payment_id}")

        # Verify payment
        success, message, amount = PaymentService.verify_payment(
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            request=request
        )

        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'amount': amount,
                'new_balance': request.player.balance
            })
        else:
            return JsonResponse({
                'success': False,
                'message': message
            })
            
    except Exception as e:
        logger.error(f"Error confirming deposit: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while confirming payment'
        })


@secure_api_endpoint(
    authentication_required=True,
    require_json=True,
    required_fields=['amount'],
    allowed_methods=['POST'],
    rate_limit_per_minute=3,  # Very strict rate limiting for withdrawals
    rate_limit_per_hour=10
)
def request_withdrawal(request):
    """Request withdrawal"""
    try:
        data = request.json
        amount = float(data.get('amount', 0))
        bank_account_info = data.get('bank_account_info', {})
        
        # Validate bank account info for withdrawals
        if not bank_account_info.get('account_number') or not bank_account_info.get('routing_number'):
            return JsonResponse({
                'success': False,
                'message': 'Bank account information is required for withdrawals'
            })
        
        # Process withdrawal
        success, message, withdrawal_id = PaymentService.process_withdrawal(
            player=request.player,
            amount=amount,
            bank_account_info=bank_account_info,
            request=request
        )
        
        if success:
            return JsonResponse({
                'success': True,
                'message': message,
                'withdrawal_id': withdrawal_id,
                'new_balance': request.player.balance
            })
        else:
            return JsonResponse({
                'success': False,
                'message': message
            })
            
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid withdrawal request from {request.player.username}: {e}")
        return JsonResponse({
            'success': False,
            'message': 'Invalid amount format'
        })
    except Exception as e:
        logger.error(f"Error processing withdrawal: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while processing withdrawal'
        })


@csrf_exempt
@require_http_methods(["POST"])
def razorpay_webhook(request):
    """Handle Razorpay webhook events"""
    payload = request.body
    sig_header = request.META.get('HTTP_X_RAZORPAY_SIGNATURE')

    if not sig_header:
        logger.warning("Missing Razorpay signature header")
        return HttpResponse(status=400)

    success, message = PaymentService.handle_webhook(payload, sig_header)

    if success:
        return HttpResponse(status=200)
    else:
        logger.error(f"Webhook processing failed: {message}")
        return HttpResponse(status=400)


@auth_required
def payment_history(request):
    """View payment transaction history"""
    # Get filter parameters
    transaction_type = request.GET.get('type', 'all')
    status = request.GET.get('status', 'all')
    
    # Build query
    payments_query = PaymentTransaction.objects.filter(player=request.user)
    
    # Apply filters
    if transaction_type != 'all':
        payments_query = payments_query.filter(transaction_type=transaction_type)
    
    if status != 'all':
        payments_query = payments_query.filter(status=status)
    
    # Order by most recent
    payments = payments_query.order_by('-created_at')[:50]  # Limit to 50 recent transactions
    
    context = {
        'player': request.user,
        'payments': payments,
        'transaction_type': transaction_type,
        'status': status,
    }
    
    return render(request, 'payment/history.html', context)

@auth_required
def test_razorpay(request):
    """Test page for Razorpay integration"""
    context = {
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
    }
    return render(request, 'payment/test_razorpay.html', context)


@secure_api_endpoint(
    authentication_required=True,
    allowed_methods=['GET'],
    rate_limit_per_minute=30,
    rate_limit_per_hour=200
)
def payment_status(request, payment_id):
    """Get payment status"""
    try:
        payment = PaymentTransaction.objects.get(
            id=payment_id,
            player=request.player
        )
        
        return JsonResponse({
            'success': True,
            'payment': {
                'id': payment.id,
                'amount': float(payment.amount),
                'status': payment.status,
                'transaction_type': payment.transaction_type,
                'created_at': payment.created_at.isoformat(),
                'completed_at': payment.completed_at.isoformat() if payment.completed_at else None,
                'description': payment.description,
                'error_message': payment.error_message if payment.status == 'failed' else None
            }
        })
        
    except PaymentTransaction.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Payment not found'
        })
    except Exception as e:
        logger.error(f"Error getting payment status: {e}")
        return JsonResponse({
            'success': False,
            'message': 'An error occurred'
        })
