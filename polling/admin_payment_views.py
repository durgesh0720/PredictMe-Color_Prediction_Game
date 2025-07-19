"""
Admin views for payment management
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import PaymentTransaction, Player, Transaction
import json
# Import admin_required decorator from admin_views
def admin_required(view_func):
    """Decorator to require admin authentication"""
    def wrapper(request, *args, **kwargs):
        if 'admin_id' not in request.session:
            from django.shortcuts import redirect
            return redirect('admin_login')

        # Get admin object and attach to request
        from .models import Admin
        try:
            admin = Admin.objects.get(id=request.session['admin_id'])
            request.admin = admin
        except Admin.DoesNotExist:
            from django.shortcuts import redirect
            return redirect('admin_login')

        return view_func(request, *args, **kwargs)
    return wrapper

@admin_required
def withdrawal_management(request):
    """Admin withdrawal management page"""
    from django.core.paginator import Paginator
    from django.db.models import Q, Count, Sum
    from .models import WithdrawalRequest

    # Get filter parameters
    status_filter = request.GET.get('status', '')
    player_filter = request.GET.get('player', '')
    min_amount = request.GET.get('min_amount', '')
    date_from = request.GET.get('date_from', '')

    # Base queryset
    withdrawals = WithdrawalRequest.objects.select_related('player').all()

    # Apply filters
    if status_filter:
        withdrawals = withdrawals.filter(status=status_filter)

    if player_filter:
        withdrawals = withdrawals.filter(
            Q(player__username__icontains=player_filter) |
            Q(player__email__icontains=player_filter)
        )

    if min_amount:
        try:
            withdrawals = withdrawals.filter(amount__gte=float(min_amount))
        except ValueError:
            pass

    if date_from:
        try:
            from datetime import datetime
            date_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
            withdrawals = withdrawals.filter(created_at__date__gte=date_obj)
        except ValueError:
            pass

    # Order by most recent first
    withdrawals = withdrawals.order_by('-created_at')

    # Pagination
    paginator = Paginator(withdrawals, 20)
    page_number = request.GET.get('page')
    withdrawal_requests = paginator.get_page(page_number)

    # Statistics
    today = timezone.now().date()

    pending_stats = WithdrawalRequest.objects.filter(status='pending').aggregate(
        count=Count('id'),
        amount=Sum('amount')
    )

    approved_today = WithdrawalRequest.objects.filter(
        status='approved',
        updated_at__date=today
    ).count()

    rejected_today = WithdrawalRequest.objects.filter(
        status='rejected',
        updated_at__date=today
    ).count()

    context = {
        'withdrawal_requests': withdrawal_requests,
        'pending_count': pending_stats['count'] or 0,
        'pending_amount': pending_stats['amount'] or 0,
        'approved_today': approved_today,
        'rejected_today': rejected_today,
    }

    return render(request, 'admin/modern_withdrawal_management.html', context)

@admin_required
def withdrawal_detail(request, withdrawal_id):
    """Get withdrawal request details for modal"""
    try:
        from .models import WithdrawalRequest
        withdrawal = WithdrawalRequest.objects.select_related('player').get(id=withdrawal_id)

        html_content = f"""
        <div class="withdrawal-detail">
            <div class="detail-section">
                <h4>Player Information</h4>
                <p><strong>Username:</strong> {withdrawal.player.username}</p>
                <p><strong>Email:</strong> {withdrawal.player.email}</p>
                <p><strong>Phone:</strong> {withdrawal.player.phone_number or 'Not provided'}</p>
            </div>

            <div class="detail-section">
                <h4>Withdrawal Details</h4>
                <p><strong>Amount:</strong> ₹{withdrawal.amount}</p>
                <p><strong>Status:</strong> {withdrawal.get_status_display()}</p>
                <p><strong>Requested:</strong> {withdrawal.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                {f'<p><strong>Processed:</strong> {withdrawal.updated_at.strftime("%B %d, %Y at %I:%M %p")}</p>' if withdrawal.status != 'pending' else ''}
            </div>

            <div class="detail-section">
                <h4>Bank Details</h4>
                <p><strong>Bank Name:</strong> {withdrawal.bank_name}</p>
                <p><strong>Account Holder:</strong> {withdrawal.account_holder_name}</p>
                <p><strong>Account Number:</strong> ****{withdrawal.bank_account_number[-4:]}</p>
                <p><strong>IFSC Code:</strong> {withdrawal.bank_ifsc_code}</p>
            </div>

            {f'<div class="detail-section"><h4>Admin Notes</h4><p>{withdrawal.admin_notes}</p></div>' if withdrawal.admin_notes else ''}
        </div>

        <style>
        .withdrawal-detail .detail-section {{
            margin-bottom: 1.5rem;
            padding: 1rem;
            background: #f8fafc;
            border-radius: 8px;
        }}
        .withdrawal-detail h4 {{
            margin: 0 0 1rem 0;
            color: #1e293b;
            font-size: 1.1rem;
        }}
        .withdrawal-detail p {{
            margin: 0.5rem 0;
            color: #64748b;
        }}
        </style>
        """

        return JsonResponse({
            'success': True,
            'html': html_content
        })

    except WithdrawalRequest.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Withdrawal request not found'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error loading withdrawal details: {str(e)}'
        })

@admin_required
def payment_admin_dashboard(request):
    """Admin dashboard for payment overview"""
    # Get date range (last 30 days by default)
    end_date = timezone.now()
    start_date = end_date - timedelta(days=30)
    
    # Payment statistics
    total_deposits = PaymentTransaction.objects.filter(
        transaction_type='deposit',
        status='completed',
        created_at__gte=start_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    total_withdrawals = PaymentTransaction.objects.filter(
        transaction_type='withdrawal',
        status='completed',
        created_at__gte=start_date
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    pending_withdrawals = PaymentTransaction.objects.filter(
        transaction_type='withdrawal',
        status__in=['pending', 'processing']
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Transaction counts
    deposit_count = PaymentTransaction.objects.filter(
        transaction_type='deposit',
        status='completed',
        created_at__gte=start_date
    ).count()
    
    withdrawal_count = PaymentTransaction.objects.filter(
        transaction_type='withdrawal',
        status='completed',
        created_at__gte=start_date
    ).count()
    
    # Flagged transactions
    flagged_transactions = PaymentTransaction.objects.filter(
        is_flagged=True,
        created_at__gte=start_date
    ).count()
    
    # Recent transactions
    recent_transactions = PaymentTransaction.objects.filter(
        created_at__gte=start_date
    ).order_by('-created_at')[:20]
    
    # Pending withdrawals for review
    pending_withdrawals_list = PaymentTransaction.objects.filter(
        transaction_type='withdrawal',
        status__in=['pending', 'processing']
    ).order_by('-created_at')[:10]
    
    context = {
        'total_deposits': total_deposits,
        'total_withdrawals': total_withdrawals,
        'pending_withdrawals': pending_withdrawals,
        'deposit_count': deposit_count,
        'withdrawal_count': withdrawal_count,
        'flagged_transactions': flagged_transactions,
        'recent_transactions': recent_transactions,
        'pending_withdrawals_list': pending_withdrawals_list,
        'date_range': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
    }
    
    return render(request, 'admin/payment_dashboard.html', context)

@admin_required
def payment_transactions_list(request):
    """List all payment transactions with filters"""
    # Get filter parameters
    transaction_type = request.GET.get('type', 'all')
    status = request.GET.get('status', 'all')
    flagged = request.GET.get('flagged', 'all')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Build query
    transactions = PaymentTransaction.objects.all()
    
    # Apply filters
    if transaction_type != 'all':
        transactions = transactions.filter(transaction_type=transaction_type)
    
    if status != 'all':
        transactions = transactions.filter(status=status)
    
    if flagged == 'true':
        transactions = transactions.filter(is_flagged=True)
    elif flagged == 'false':
        transactions = transactions.filter(is_flagged=False)
    
    if date_from:
        transactions = transactions.filter(created_at__date__gte=date_from)
    
    if date_to:
        transactions = transactions.filter(created_at__date__lte=date_to)
    
    # Order by most recent
    transactions = transactions.order_by('-created_at')
    
    # Pagination (simple limit for now)
    transactions = transactions[:100]
    
    context = {
        'transactions': transactions,
        'transaction_type': transaction_type,
        'status': status,
        'flagged': flagged,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'admin/payment_transactions.html', context)

@admin_required
def approve_withdrawal(request, withdrawal_id):
    """Approve a withdrawal request with real money transfer"""
    if request.method == 'POST':
        try:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Attempting to approve withdrawal: {withdrawal_id}")
            # Try to find withdrawal request first (new system)
            try:
                from .models import WithdrawalRequest
                withdrawal_request = WithdrawalRequest.objects.get(
                    id=withdrawal_id,
                    status='pending'
                )

                # Try Razorpay integration first, fallback to manual approval
                try:
                    success, message = withdrawal_request.approve_with_razorpay(
                        admin=request.admin,
                        notes=f"Approved by admin {request.admin.username}"
                    )

                    if success:
                        return JsonResponse({
                            'success': True,
                            'message': f'✅ {message}',
                            'transfer_type': 'automatic',
                            'amount': float(withdrawal_request.amount)
                        })
                    else:
                        # Fallback to manual approval if Razorpay fails
                        withdrawal_request.approve(
                            admin=request.admin,
                            notes=f"Manually approved by admin {request.admin.username}. Razorpay error: {message}"
                        )
                        return JsonResponse({
                            'success': True,
                            'message': f'⚠️ Withdrawal approved manually. Razorpay error: {message}. Please process ₹{withdrawal_request.amount} payment manually.',
                            'transfer_type': 'manual',
                            'amount': float(withdrawal_request.amount)
                        })

                except Exception as e:
                    # Fallback to manual approval if Razorpay integration fails completely
                    withdrawal_request.approve(
                        admin=request.admin,
                        notes=f"Manually approved by admin {request.admin.username}. Razorpay integration error: {str(e)}"
                    )
                    return JsonResponse({
                        'success': True,
                        'message': f'⚠️ Withdrawal approved manually due to payment gateway error. Please process ₹{withdrawal_request.amount} payment manually.',
                        'transfer_type': 'manual',
                        'amount': float(withdrawal_request.amount),
                        'error': str(e)
                    })

            except WithdrawalRequest.DoesNotExist:
                # Fallback to legacy PaymentTransaction
                transaction = PaymentTransaction.objects.get(
                    id=withdrawal_id,
                    transaction_type='withdrawal',
                    status__in=['pending', 'processing']
                )

                # Update status to completed
                transaction.status = 'completed'
                transaction.completed_at = timezone.now()
                transaction.admin_notes = f"Approved by admin {request.admin.username}"
                transaction.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Withdrawal of ₹{transaction.amount} approved successfully'
                })

        except Exception as e:
            import logging
            import traceback
            logger = logging.getLogger(__name__)
            logger.error(f"Error approving withdrawal {withdrawal_id}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return JsonResponse({
                'success': False,
                'message': f'Error approving withdrawal: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@admin_required
def complete_withdrawal(request, withdrawal_id):
    """Mark a withdrawal as completed after manual bank transfer"""
    if request.method == 'POST':
        try:
            import json
            data = json.loads(request.body) if request.body else {}
            bank_reference = data.get('bank_reference', '')
            notes = data.get('notes', '')

            from .models import WithdrawalRequest
            withdrawal_request = WithdrawalRequest.objects.get(
                id=withdrawal_id,
                status='approved'
            )

            success = withdrawal_request.mark_transfer_completed(
                admin=request.admin,
                bank_reference=bank_reference,
                notes=notes
            )

            if success:
                return JsonResponse({
                    'success': True,
                    'message': f'✅ Withdrawal marked as completed. ₹{withdrawal_request.amount} transfer confirmed.'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Failed to mark withdrawal as completed'
                })

        except WithdrawalRequest.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Withdrawal request not found or not in approved status'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error completing withdrawal: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@admin_required
def razorpay_test_dashboard(request):
    """Razorpay test dashboard for monitoring test transactions"""
    from django.conf import settings
    from django.db.models import Count, Sum
    from .models import PaymentTransaction, WithdrawalRequest
    from datetime import datetime, timedelta

    # Get test mode status
    razorpay_mode = 'test' if 'test' in getattr(settings, 'RAZORPAY_KEY_ID', '') else 'live'

    # Get test statistics
    today = timezone.now().date()
    test_payments = PaymentTransaction.objects.filter(
        created_at__date=today,
        transaction_type='deposit'
    )

    test_withdrawals = WithdrawalRequest.objects.filter(
        created_at__date=today
    )

    pending_withdrawals = WithdrawalRequest.objects.filter(
        status='pending'
    )

    context = {
        'razorpay_mode': razorpay_mode,
        'razorpay_key_id': getattr(settings, 'RAZORPAY_KEY_ID', ''),
        'razorpay_account_number': getattr(settings, 'RAZORPAY_ACCOUNT_NUMBER', ''),
        'test_payments_count': test_payments.count(),
        'test_payments_total': test_payments.aggregate(Sum('amount'))['amount__sum'] or 0,
        'test_withdrawals_count': test_withdrawals.count(),
        'pending_withdrawals_count': pending_withdrawals.count(),
        'webhook_url': f"{request.scheme}://{request.get_host()}/webhooks/razorpay/",
    }

    return render(request, 'admin/razorpay_test_dashboard.html', context)

@admin_required
def test_razorpay_connection(request):
    """Test Razorpay API connection"""
    if request.method == 'POST':
        try:
            import razorpay
            from django.conf import settings

            # Test connection
            client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # Try to fetch account details (this will fail gracefully in test mode)
            try:
                # Test API call
                orders = client.order.all({'count': 1})
                mode = 'test' if 'test' in settings.RAZORPAY_KEY_ID else 'live'

                return JsonResponse({
                    'success': True,
                    'message': f'Connection successful!\n\nMode: {mode.title()}\nKey ID: {settings.RAZORPAY_KEY_ID[:10]}...\nAPI is responding correctly.'
                })
            except Exception as api_error:
                # Even if API call fails, connection might be working
                return JsonResponse({
                    'success': True,
                    'message': f'Connection established but API returned: {str(api_error)}\n\nThis is normal in test mode.'
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Connection failed: {str(e)}\n\nCheck your API keys in .env file.'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@admin_required
def reject_withdrawal(request, withdrawal_id):
    """Reject a withdrawal request and refund to wallet"""
    if request.method == 'POST':
        try:
            # Get rejection reason from request
            data = json.loads(request.body) if request.body else {}
            rejection_reason = data.get('reason', 'Rejected by admin')

            # Try to find withdrawal request first (new system)
            try:
                from .models import WithdrawalRequest
                withdrawal_request = WithdrawalRequest.objects.get(
                    id=withdrawal_id,
                    status='pending'
                )

                # Reject withdrawal with automatic refund
                success = withdrawal_request.reject(
                    admin=request.admin,
                    reason=rejection_reason
                )

                if success:
                    return JsonResponse({
                        'success': True,
                        'message': f'Withdrawal rejected and ₹{withdrawal_request.amount} refunded to user wallet'
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Failed to reject withdrawal'
                    })

            except WithdrawalRequest.DoesNotExist:
                # Fallback to legacy PaymentTransaction
                transaction = PaymentTransaction.objects.get(
                    id=withdrawal_id,
                    transaction_type='withdrawal',
                    status__in=['pending', 'processing']
                )

                # Refund amount to player wallet
                player = transaction.player
                player.credit_wallet(
                    amount=transaction.amount,
                    transaction_type='refund',
                    description=f'Withdrawal rejection refund - {rejection_reason}',
                    involves_real_money=False
                )

                # Update transaction status
                transaction.status = 'failed'
                transaction.error_message = rejection_reason
                transaction.admin_notes = f"Rejected by admin {request.admin.username}"
                transaction.save()

                return JsonResponse({
                    'success': True,
                    'message': f'Withdrawal rejected and ₹{transaction.amount} refunded to wallet'
                })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error rejecting withdrawal: {str(e)}'
            })

    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@admin_required
def payment_statistics(request):
    """Get payment statistics for charts"""
    # Get date range
    days = int(request.GET.get('days', 30))
    end_date = timezone.now()
    start_date = end_date - timedelta(days=days)
    
    # Daily statistics
    daily_stats = []
    current_date = start_date.date()
    
    while current_date <= end_date.date():
        day_deposits = PaymentTransaction.objects.filter(
            transaction_type='deposit',
            status='completed',
            created_at__date=current_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        day_withdrawals = PaymentTransaction.objects.filter(
            transaction_type='withdrawal',
            status='completed',
            created_at__date=current_date
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        daily_stats.append({
            'date': current_date.strftime('%Y-%m-%d'),
            'deposits': float(day_deposits),
            'withdrawals': float(day_withdrawals),
            'net': float(day_deposits - day_withdrawals)
        })
        
        current_date += timedelta(days=1)
    
    # Status distribution
    status_stats = PaymentTransaction.objects.filter(
        created_at__gte=start_date
    ).values('status').annotate(count=Count('id')).order_by('status')
    
    # Type distribution
    type_stats = PaymentTransaction.objects.filter(
        created_at__gte=start_date
    ).values('transaction_type').annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    ).order_by('transaction_type')
    
    return JsonResponse({
        'daily_stats': daily_stats,
        'status_stats': list(status_stats),
        'type_stats': list(type_stats)
    })

@admin_required
def player_payment_history(request, player_id):
    """Get payment history for a specific player"""
    try:
        player = Player.objects.get(id=player_id)
        
        # Get payment transactions
        payments = PaymentTransaction.objects.filter(
            player=player
        ).order_by('-created_at')[:50]
        
        # Get wallet transactions
        wallet_transactions = Transaction.objects.filter(
            player=player
        ).order_by('-created_at')[:50]
        
        # Calculate totals
        total_deposits = PaymentTransaction.objects.filter(
            player=player,
            transaction_type='deposit',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_withdrawals = PaymentTransaction.objects.filter(
            player=player,
            transaction_type='withdrawal',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        context = {
            'player': player,
            'payments': payments,
            'wallet_transactions': wallet_transactions,
            'total_deposits': total_deposits,
            'total_withdrawals': total_withdrawals,
        }
        
        return render(request, 'admin/player_payment_history.html', context)
        
    except Player.DoesNotExist:
        return render(request, 'admin/error.html', {
            'error_message': 'Player not found'
        })
