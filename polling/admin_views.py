from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import logging
import re
from datetime import datetime, timedelta

from .models import Player, GameRound, Bet, Admin, GameControl, Transaction, AdminLog, AdminColorSelection, MasterWalletTransaction
from .wallet_utils import get_master_wallet_balance, get_master_wallet_statistics, get_master_wallet_transactions
from .decorators import secure_api_endpoint
from .security import get_client_ip
from .brevo_email_service import BrevoEmailService

# Import timing constants to ensure consistency with game logic
ROUND_DURATION = 50  # Same as consumers.py
BETTING_DURATION = 40  # Same as consumers.py

logger = logging.getLogger(__name__)


def get_real_bets_queryset():
    """
    Get a queryset of real player bets, excluding test/dummy bets.
    This helper function filters out bets from test users.
    """
    return Bet.objects.exclude(
        Q(player__username__startswith='testuser') |  # Exclude testuser1, testuser2, etc.
        Q(player__username__in=['Alice', 'Bob', 'Charlie', 'Diana', 'Eve']) |  # Exclude test players
        Q(player__username__icontains='test') |  # Exclude any username containing 'test'
        Q(player__username__icontains='dummy') |  # Exclude any username containing 'dummy'
        Q(player__username__icontains='bot') |  # Exclude any username containing 'bot'
        Q(player__username__icontains='demo')  # Exclude any username containing 'demo'
    )


def get_test_players_queryset():
    """
    Get a queryset of test/dummy players that should be excluded from real statistics.
    """
    return Player.objects.filter(
        Q(username__startswith='testuser') |  # testuser1, testuser2, etc.
        Q(username__in=['Alice', 'Bob', 'Charlie', 'Diana', 'Eve']) |  # Test players
        Q(username__icontains='test') |  # Any username containing 'test'
        Q(username__icontains='dummy') |  # Any username containing 'dummy'
        Q(username__icontains='bot') |  # Any username containing 'bot'
        Q(username__icontains='demo')  # Any username containing 'demo'
    )


def admin_login(request):
    """Admin login page"""
    # Check if already logged in
    if 'admin_id' in request.session:
        try:
            admin = Admin.objects.get(id=request.session['admin_id'], is_active=True)
            return redirect('admin_dashboard')
        except Admin.DoesNotExist:
            request.session.flush()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        logger.info(f"Login attempt: username='{username}', has_password={bool(password)}")

        if not username or not password:
            messages.error(request, 'Please provide both username and password')
            return render(request, 'admin/modern_login.html')

        try:
            admin = Admin.objects.get(username=username, is_active=True)
            if admin.check_password(password):
                # Set admin session with timestamps
                request.session['admin_id'] = admin.id
                request.session['admin_username'] = admin.username
                request.session['admin_login_time'] = timezone.now().isoformat()
                request.session['admin_last_activity'] = timezone.now().isoformat()
                admin.last_login = timezone.now()
                admin.save()

                # Log the login
                AdminLog.objects.create(
                    admin=admin,
                    action='LOGIN',
                    description=f'Admin {username} logged in',
                    ip_address=get_client_ip(request)
                )

                logger.info(f"Admin login successful: {admin.username} from {get_client_ip(request)}")
                return redirect('admin_dashboard')
            else:
                logger.warning(f"Failed login attempt for admin: {username} from {get_client_ip(request)}")
                messages.error(request, 'Invalid credentials')
        except Admin.DoesNotExist:
            logger.warning(f"Failed login attempt for non-existent admin: {username} from {get_client_ip(request)}")
            messages.error(request, 'Invalid credentials')
        except Exception as e:
            logger.error(f"Error during admin login: {e}")
            messages.error(request, 'An error occurred during login')
    
    return render(request, 'admin/modern_login.html')


def admin_logout(request):
    """Admin logout"""
    if 'admin_id' in request.session:
        try:
            admin = Admin.objects.get(id=request.session['admin_id'])
            AdminLog.objects.create(
                admin=admin,
                action='LOGOUT',
                description=f'Admin {admin.username} logged out',
                ip_address=get_client_ip(request)
            )
        except Admin.DoesNotExist:
            pass

    # Clear all session data
    request.session.flush()
    messages.success(request, 'You have been logged out successfully.')

    return redirect('admin_login')


def admin_required(view_func):
    """Decorator to require admin authentication with session timeout"""
    def wrapper(request, *args, **kwargs):
        if 'admin_id' not in request.session:
            return redirect('admin_login')

        # Verify admin still exists and is active
        try:
            admin = Admin.objects.get(id=request.session['admin_id'], is_active=True)
            request.admin = admin  # Add admin to request
        except Admin.DoesNotExist:
            request.session.flush()
            messages.error(request, 'Your admin account is no longer active. Please log in again.')
            return redirect('admin_login')

        # Admin sessions never expire - unlimited time
        # (Commented out session timeout for admin users)
        # admin_login_time = request.session.get('admin_login_time')
        # if admin_login_time:
        #     login_time = datetime.fromisoformat(admin_login_time.replace('Z', '+00:00'))
        #     timeout_duration = getattr(settings, 'ADMIN_SESSION_TIMEOUT', 1800)  # 30 minutes default
        #
        #     if (timezone.now() - login_time).total_seconds() > timeout_duration:
        #         # Session expired
        #         request.session.flush()
        #         messages.warning(request, 'Your session has expired. Please log in again.')
        #         return redirect('admin_login')

        try:
            admin = Admin.objects.get(id=request.session['admin_id'], is_active=True)
            request.admin = admin

            # Update last activity time
            request.session['admin_last_activity'] = timezone.now().isoformat()

        except Admin.DoesNotExist:
            request.session.flush()
            return redirect('admin_login')

        return view_func(request, *args, **kwargs)
    return wrapper


@admin_required
def admin_dashboard(request):
    """Main admin dashboard"""
    # Get statistics
    total_players = Player.objects.count()
    active_players = Player.objects.filter(
        bet__created_at__gte=timezone.now() - timedelta(days=1)
    ).distinct().count()
    
    total_bets_today = get_real_bets_queryset().filter(
        created_at__gte=timezone.now().replace(hour=0, minute=0, second=0)
    ).count()

    total_amount_today = get_real_bets_queryset().filter(
        created_at__gte=timezone.now().replace(hour=0, minute=0, second=0)
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Recent game rounds
    recent_rounds = GameRound.objects.filter(ended=True).order_by('-start_time')[:10]
    
    # Game controls
    game_controls = GameControl.objects.all()
    
    # Recent admin logs
    recent_logs = AdminLog.objects.select_related('admin').order_by('-created_at')[:10]
    
    context = {
        'total_players': total_players,
        'active_players': active_players,
        'total_bets_today': total_bets_today,
        'total_amount_today': total_amount_today,
        'recent_rounds': recent_rounds,
        'game_controls': game_controls,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'admin/modern_dashboard.html', context)


@admin_required
def game_control(request):
    """Game control interface"""
    if request.method == 'POST':
        action = request.POST.get('action')
        game_type = request.POST.get('game_type', 'parity')
        
        control, _ = GameControl.objects.get_or_create(
            game_type=game_type,
            defaults={'is_active': True, 'auto_result': True}
        )
        
        if action == 'start_game':
            control.is_active = True
            control.save()
            
            AdminLog.objects.create(
                admin=request.admin,
                action='START_GAME',
                description=f'Started {game_type} game',
                ip_address=get_client_ip(request)
            )
            messages.success(request, f'{game_type} game started')
            
        elif action == 'stop_game':
            control.is_active = False
            control.save()
            
            AdminLog.objects.create(
                admin=request.admin,
                action='STOP_GAME',
                description=f'Stopped {game_type} game',
                ip_address=get_client_ip(request)
            )
            messages.success(request, f'{game_type} game stopped')
            
        elif action == 'set_manual_result':
            result_number = int(request.POST.get('result_number', 0))
            control.auto_result = False
            control.manual_result_number = result_number
            control.save()
            
            AdminLog.objects.create(
                admin=request.admin,
                action='SET_MANUAL_RESULT',
                description=f'Set manual result {result_number} for {game_type}',
                ip_address=get_client_ip(request)
            )
            messages.success(request, f'Manual result {result_number} set for {game_type}')
            
        elif action == 'enable_auto_result':
            control.auto_result = True
            control.manual_result_number = None
            control.save()
            
            AdminLog.objects.create(
                admin=request.admin,
                action='ENABLE_AUTO_RESULT',
                description=f'Enabled auto result for {game_type}',
                ip_address=get_client_ip(request)
            )
            messages.success(request, f'Auto result enabled for {game_type}')
    
    # Get all game controls
    game_controls = GameControl.objects.all()

    # Get current active rounds
    active_rounds = GameRound.objects.filter(ended=False)

    # Get current game type from request
    current_game_type = request.GET.get('game_type', 'parity')

    # Get current control for the selected game type
    current_control = None
    try:
        current_control = GameControl.objects.get(game_type=current_game_type)
    except GameControl.DoesNotExist:
        pass

    context = {
        'game_controls': game_controls,
        'active_rounds': active_rounds,
        'game_types': ['parity', 'sapre', 'bcone', 'noki'],
        'current_game_type': current_game_type,
        'current_control': current_control,
    }
    
    return render(request, 'admin/modern_game_control.html', context)


@admin_required
def user_management(request):
    """User management interface"""
    # Get search parameters
    search = request.GET.get('search', '')
    page = int(request.GET.get('page', 1))
    limit = 20
    offset = (page - 1) * limit
    
    # Build query
    players_query = Player.objects.all()
    if search:
        players_query = players_query.filter(
            Q(username__icontains=search) | Q(id__icontains=search)
        )
    
    # Get players with pagination
    players = players_query.order_by('-created_at')[offset:offset + limit]
    total_players = players_query.count()
    
    # Calculate pagination
    has_next = offset + limit < total_players
    has_prev = page > 1
    
    context = {
        'players': players,
        'search': search,
        'page': page,
        'has_next': has_next,
        'has_prev': has_prev,
        'total_players': total_players,
    }
    
    return render(request, 'admin/modern_user_management.html', context)


@admin_required
def player_detail(request, player_id):
    """Player detail and management"""
    player = get_object_or_404(Player, id=player_id)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'adjust_balance':
            amount = int(request.POST.get('amount', 0))
            description = request.POST.get('description', '')

            # Use the new wallet system for balance adjustment
            if amount > 0:
                # Credit wallet
                player.credit_wallet(
                    amount=amount,
                    transaction_type='admin_adjust',
                    description=description,
                    admin=request.admin
                )
            elif amount < 0:
                # Debit wallet
                success = player.debit_wallet(
                    amount=abs(amount),
                    transaction_type='admin_adjust',
                    description=description,
                    admin=request.admin
                )
                if not success:
                    messages.error(request, 'Insufficient balance for debit')
                    return redirect('admin_player_detail', player_id=player.id)

            AdminLog.objects.create(
                admin=request.admin,
                action='ADJUST_BALANCE',
                description=f'Adjusted {player.username} balance by {amount}: {description}',
                ip_address=get_client_ip(request)
            )

            messages.success(request, f'Balance adjusted by {amount}')
    
    # Get player's recent bets
    recent_bets = Bet.objects.filter(player=player).select_related('round').order_by('-created_at')[:20]
    
    # Get player's transactions
    transactions = Transaction.objects.filter(player=player).order_by('-created_at')[:20]
    
    context = {
        'player': player,
        'recent_bets': recent_bets,
        'transactions': transactions,
    }
    
    return render(request, 'admin/modern_player_detail.html', context)


@admin_required
def financial_management(request):
    """Financial management interface"""
    # Get date range
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')

    if not start_date:
        start_date = timezone.now().replace(hour=0, minute=0, second=0)
    else:
        start_date = datetime.strptime(start_date, '%Y-%m-%d')

    if not end_date:
        end_date = timezone.now()
    else:
        end_date = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)

    # Get financial statistics
    total_deposits = Transaction.objects.filter(
        transaction_type='deposit',
        created_at__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_withdrawals = Transaction.objects.filter(
        transaction_type='withdrawal',
        created_at__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_bets = Transaction.objects.filter(
        transaction_type='bet',
        created_at__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_wins = Transaction.objects.filter(
        transaction_type='win',
        created_at__range=[start_date, end_date]
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Recent transactions
    recent_transactions = Transaction.objects.select_related('player', 'admin').order_by('-created_at')[:50]

    context = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'total_deposits': total_deposits,
        'total_withdrawals': abs(total_withdrawals),
        'total_bets': abs(total_bets),
        'total_wins': total_wins,
        'net_profit': abs(total_bets) - total_wins,
        'recent_transactions': recent_transactions,
    }

    return render(request, 'admin/modern_financial_management.html', context)


@admin_required
def game_reports(request):
    """Game reports and analytics"""
    # Get date range
    days = int(request.GET.get('days', 7))
    start_date = timezone.now() - timedelta(days=days)

    # Game statistics by type
    game_stats = {}
    for game_type in ['parity', 'sapre', 'bcone', 'noki']:
        rounds = GameRound.objects.filter(
            game_type=game_type,
            ended=True,
            start_time__gte=start_date
        )

        bets = get_real_bets_queryset().filter(
            round__game_type=game_type,
            created_at__gte=start_date
        )

        game_stats[game_type] = {
            'total_rounds': rounds.count(),
            'total_bets': bets.count(),
            'total_amount': bets.aggregate(total=Sum('amount'))['total'] or 0,
            'total_wins': bets.filter(correct=True).count(),
            'win_rate': bets.filter(correct=True).count() / max(bets.count(), 1) * 100,
        }

    # Popular bet colors/numbers (real players only)
    color_stats = get_real_bets_queryset().filter(
        bet_type='color',
        created_at__gte=start_date
    ).values('color').annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    ).order_by('-count')

    number_stats = get_real_bets_queryset().filter(
        bet_type='number',
        created_at__gte=start_date
    ).values('number').annotate(
        count=Count('id'),
        total_amount=Sum('amount')
    ).order_by('-count')

    # Top players by betting volume
    top_players = Player.objects.annotate(
        bet_volume=Sum('bet__amount', filter=Q(bet__created_at__gte=start_date))
    ).filter(bet_volume__isnull=False).order_by('-bet_volume')[:10]

    context = {
        'days': days,
        'game_stats': game_stats,
        'color_stats': color_stats,
        'number_stats': number_stats,
        'top_players': top_players,
    }

    return render(request, 'admin/modern_game_reports.html', context)


@secure_api_endpoint(
    admin_required=True,
    require_json=True,
    required_fields=['round_id', 'result'],
    allowed_methods=['POST'],
    rate_limit_per_minute=20
)
def manual_round_result(request):
    """Set manual result for a specific round"""
    try:
        data = request.json
        round_id = data.get('round_id')
        result_number = data.get('result_number')

        round_obj = get_object_or_404(GameRound, id=round_id)

        # Set the result
        round_obj.result_number = result_number
        round_obj.result_color = round_obj.result_color_from_number
        round_obj.ended = True
        round_obj.save()

        # Process all bets for this round (including test bets for processing)
        bets = Bet.objects.filter(round=round_obj)
        for bet in bets:
            bet.check_win(result_number, round_obj.result_color)

            # Update player stats
            if bet.correct:
                bet.player.total_wins += 1
                # Credit wallet for winning (this will handle balance update and transaction logging)
                bet.player.credit_wallet(
                    amount=bet.payout,
                    transaction_type='win',
                    description=f'Won bet on {bet.color or bet.number} for round {round_obj.period_id}',
                    bet=bet
                )
                bet.player.score += bet.payout
            bet.player.total_bets += 1
            bet.player.save()

        AdminLog.objects.create(
            admin=request.admin,
            action='MANUAL_ROUND_RESULT',
            description=f'Set manual result {result_number} for round {round_id}',
            ip_address=get_client_ip(request)
        )

        return JsonResponse({'success': True, 'message': 'Result set successfully'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def admin_logs(request):
    """View admin activity logs"""
    # Get pagination parameters
    page = int(request.GET.get('page', 1))
    limit = 50
    offset = (page - 1) * limit

    # Get logs
    logs = AdminLog.objects.select_related('admin').order_by('-created_at')[offset:offset + limit]
    total_logs = AdminLog.objects.count()

    # Calculate pagination
    has_next = offset + limit < total_logs
    has_prev = page > 1

    context = {
        'logs': logs,
        'page': page,
        'has_next': has_next,
        'has_prev': has_prev,
        'total_logs': total_logs,
    }

    return render(request, 'admin/modern_admin_logs.html', context)


@admin_required
def admin_game_control_live(request):
    """Real-time admin game control interface"""
    # Get all active game controls
    game_controls = GameControl.objects.all()

    # Get current active rounds with detailed information
    # Prioritize rounds with bets or recent rounds
    from datetime import timedelta
    recent_time = timezone.now() - timedelta(minutes=10)

    active_rounds = GameRound.objects.filter(ended=False).filter(
        Q(bet__isnull=False) | Q(start_time__gte=recent_time)
    ).distinct().order_by('-start_time')

    # Prepare detailed round information
    rounds_data = []
    for round_obj in active_rounds:
        # Get real player bets for this round (exclude test bets)
        bets = get_real_bets_queryset().filter(round=round_obj)

        # Calculate color statistics
        color_stats = {}
        colors = ['red', 'green', 'violet', 'blue']

        for color in colors:
            color_bets = bets.filter(color=color)
            color_stats[color] = {
                'count': color_bets.count(),
                'amount': sum(bet.amount for bet in color_bets),
                'users': color_bets.values('player__username').distinct().count()
            }

        # Calculate time remaining using consistent constants
        time_remaining = max(0, ROUND_DURATION - (timezone.now() - round_obj.start_time).total_seconds())

        rounds_data.append({
            'round': round_obj,
            'color_stats': color_stats,
            'total_bets': bets.count(),
            'total_amount': sum(bet.amount for bet in bets),
            'time_remaining': int(time_remaining),
            'can_select': time_remaining > 0,  # Admin can select anytime during the round (0-50s)
        })

    # Get recent admin selections
    recent_selections = AdminColorSelection.objects.select_related('round', 'admin').order_by('-selection_time')[:20]

    # Debug logging
    logger.info(f"Active rounds count: {active_rounds.count()}")
    logger.info(f"Rounds data count: {len(rounds_data)}")
    for i, round_data in enumerate(rounds_data[:3]):  # Log first 3 rounds
        logger.info(f"Round {i}: {round_data['round'].period_id}, bets: {round_data['total_bets']}, amount: {round_data['total_amount']}")

    context = {
        'game_controls': game_controls,
        'active_rounds': active_rounds,
        'rounds_data': rounds_data,
        'recent_selections': recent_selections,
        'game_types': ['parity', 'sapre', 'bcone', 'noki'],
    }

    return render(request, 'admin/modern_game_control_live.html', context)


@secure_api_endpoint(
    admin_required=True,
    require_json=True,
    required_fields=['round_id', 'color'],  # Changed to match what the function expects
    allowed_methods=['POST'],
    rate_limit_per_minute=30
)
def admin_select_color(request):
    """API endpoint for admin to select winning color"""
    try:
        data = request.json
        round_id = data.get('round_id')
        selected_color = data.get('color')  # green, red, violet, blue

        if not round_id or not selected_color:
            return JsonResponse({'success': False, 'error': 'Missing round_id or color'})

        if selected_color not in ['green', 'red', 'violet', 'blue']:
            return JsonResponse({'success': False, 'error': 'Invalid color'})

        # Get the round
        try:
            round_obj = GameRound.objects.get(id=round_id, ended=False)
        except GameRound.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Round not found or already ended'})

        # Admin can select color anytime during the round (0-50 seconds)
        time_elapsed = (timezone.now() - round_obj.start_time).total_seconds()
        if time_elapsed >= ROUND_DURATION:  # After round has ended
            return JsonResponse({'success': False, 'error': 'Round has ended, cannot change result'})

        # Create or update admin selection
        selection, created = AdminColorSelection.objects.get_or_create(
            round=round_obj,
            defaults={
                'admin': request.admin,
                'selected_color': selected_color,
                'is_auto_selected': False
            }
        )

        if not created:
            selection.admin = request.admin
            selection.selected_color = selected_color
            selection.is_auto_selected = False
            selection.save()

        # Log the action
        AdminLog.objects.create(
            admin=request.admin,
            action='SELECT_COLOR',
            description=f'Selected {selected_color} for round {round_obj.period_id}',
            ip_address=get_client_ip(request)
        )

        # Broadcast color selection via WebSocket to both admin and user groups
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                # Broadcast to admin control panel
                async_to_sync(channel_layer.group_send)(
                    "admin_game_control",
                    {
                        'type': 'color_selected_event',
                        'round_id': str(round_id),
                        'color': selected_color,
                        'admin_username': request.admin.username,
                        'selection_time': selection.selection_time.isoformat(),
                        'persist_until_round_end': True,
                        'time_remaining': int(ROUND_DURATION - time_elapsed)
                    }
                )

                # Broadcast to user game interface (main room)
                async_to_sync(channel_layer.group_send)(
                    "game_main",
                    {
                        'type': 'admin_color_selected',
                        'round_id': str(round_id),
                        'color': selected_color,
                        'time_remaining': int(ROUND_DURATION - time_elapsed),
                        'admin_selection': True
                    }
                )

                logger.info(f"Broadcasted color selection {selected_color} for round {round_id} to both admin and user groups")
            except Exception as e:
                logger.error(f"Failed to broadcast color selection event: {e}")

        # Trigger immediate round ending since admin has made selection
        try:
            # Send immediate round end signal to the game consumer
            async_to_sync(channel_layer.group_send)(
                "game_main",
                {
                    'type': 'admin_force_round_end',
                    'round_id': str(round_id),
                    'admin_selected_color': selected_color,
                    'timestamp': timezone.now().timestamp()
                }
            )
            logger.info(f"Sent force round end signal for round {round_id}")
        except Exception as e:
            logger.error(f"Failed to send force round end signal: {e}")

        return JsonResponse({
            'success': True,
            'message': f'Selected {selected_color} for round {round_obj.period_id}',
            'round_id': round_id,
            'color': selected_color,
            'round_ending': True
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@admin_required
def admin_game_status(request):
    """API endpoint to get current game status for admin"""
    try:
        # Get all active rounds with betting statistics
        active_rounds = []

        for round_obj in GameRound.objects.filter(ended=False):
            # Get real player betting statistics for this round (exclude test bets)
            bets = get_real_bets_queryset().filter(round=round_obj, bet_type='color')

            color_stats = {
                'green': bets.filter(color='green').count(),
                'red': bets.filter(color='red').count(),
                'violet': bets.filter(color='violet').count(),
            }

            # Find minimum selected color
            min_color = min(color_stats.items(), key=lambda x: x[1])[0] if any(color_stats.values()) else 'green'

            # Check if admin has selected a color
            admin_selection = AdminColorSelection.objects.filter(round=round_obj).first()

            # Calculate time remaining using consistent constants
            time_elapsed = (timezone.now() - round_obj.start_time).total_seconds()
            time_remaining = max(0, ROUND_DURATION - time_elapsed)  # 50 seconds total

            active_rounds.append({
                'id': round_obj.id,
                'period_id': round_obj.period_id,
                'game_type': round_obj.game_type,
                'start_time': round_obj.start_time.isoformat(),
                'time_remaining': int(time_remaining),
                'color_stats': color_stats,
                'min_selected_color': min_color,
                'admin_selected_color': admin_selection.selected_color if admin_selection else None,
                'admin_selected_by': admin_selection.admin.username if admin_selection and admin_selection.admin else None,
            })

        return JsonResponse({
            'success': True,
            'active_rounds': active_rounds,
            'timestamp': timezone.now().isoformat()
        })

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def get_minimum_selected_color(round_obj):
    """Get the color with minimum real player bets for a round (exclude test bets)"""
    bets = get_real_bets_queryset().filter(round=round_obj, bet_type='color')

    color_counts = {
        'green': bets.filter(color='green').count(),
        'red': bets.filter(color='red').count(),
        'violet': bets.filter(color='violet').count(),
    }

    # Return the color with minimum bets
    if any(color_counts.values()):
        return min(color_counts.items(), key=lambda x: x[1])[0]
    else:
        return 'green'  # Default if no bets


# Removed duplicate get_client_ip function - using the one from security.py


@admin_required
def master_wallet_dashboard(request):
    """Master wallet dashboard showing balance and statistics"""
    # Get master wallet statistics
    stats = get_master_wallet_statistics()

    # Get recent transactions
    recent_transactions = get_master_wallet_transactions(limit=20)

    # Get daily earnings for the last 7 days
    end_date = timezone.now().date()
    start_date = end_date - timedelta(days=6)

    daily_earnings = []
    for i in range(7):
        date = start_date + timedelta(days=i)
        day_start = timezone.make_aware(datetime.combine(date, datetime.min.time()))
        day_end = timezone.make_aware(datetime.combine(date, datetime.max.time()))

        earnings = MasterWalletTransaction.objects.filter(
            transaction_type='house_earning',
            created_at__range=[day_start, day_end]
        ).aggregate(total=Sum('amount'))['total'] or 0

        daily_earnings.append({
            'date': date.strftime('%m/%d'),
            'earnings': earnings
        })

    context = {
        'stats': stats,
        'recent_transactions': recent_transactions,
        'daily_earnings': daily_earnings,
    }

    return render(request, 'admin/modern_master_wallet.html', context)


@admin_required
def master_wallet_transactions(request):
    """Master wallet transaction history with filtering"""
    # Get filter parameters
    transaction_type = request.GET.get('type', 'all')
    date_range = request.GET.get('date_range', '30')  # days

    # Build query
    transactions_query = MasterWalletTransaction.objects.all()

    # Apply filters
    if transaction_type != 'all':
        transactions_query = transactions_query.filter(transaction_type=transaction_type)

    if date_range != 'all':
        days = int(date_range)
        cutoff_date = timezone.now() - timedelta(days=days)
        transactions_query = transactions_query.filter(created_at__gte=cutoff_date)

    # Order by most recent
    transactions_query = transactions_query.order_by('-created_at')

    # Pagination
    from django.core.paginator import Paginator
    paginator = Paginator(transactions_query, 50)  # 50 transactions per page
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)

    # Calculate statistics for filtered data
    total_earnings = transactions_query.filter(
        transaction_type='house_earning'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_payouts = transactions_query.filter(
        transaction_type='house_payout'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'transactions': transactions,
        'total_earnings': total_earnings,
        'total_payouts': abs(total_payouts),  # Make positive for display
        'net_profit': total_earnings + total_payouts,  # total_payouts is negative
        'transaction_type': transaction_type,
        'date_range': date_range,
        'current_balance': get_master_wallet_balance(),
    }

    return render(request, 'admin/modern_master_wallet_transactions.html', context)


@admin_required
def live_betting_stats(request):
    """API endpoint for live betting statistics"""
    from django.db.models import Sum, Count

    # Get current active rounds from database
    active_rounds = GameRound.objects.filter(ended=False)

    # Initialize stats for all colors
    stats = {
        'red': {'amount': 0, 'count': 0, 'users': 0},
        'green': {'amount': 0, 'count': 0, 'users': 0},
        'violet': {'amount': 0, 'count': 0, 'users': 0},
        'blue': {'amount': 0, 'count': 0, 'users': 0}
    }

    # Get betting data from database for active rounds
    if active_rounds.exists():
        for round_obj in active_rounds:
            # Get bets for this round grouped by color
            round_bets = Bet.objects.filter(round=round_obj, bet_type='color')

            for color in stats.keys():
                color_bets = round_bets.filter(color=color)
                color_stats = color_bets.aggregate(
                    total_amount=Sum('amount'),
                    total_count=Count('id'),
                    unique_users=Count('player', distinct=True)
                )

                stats[color]['amount'] += color_stats['total_amount'] or 0
                stats[color]['count'] += color_stats['total_count'] or 0
                stats[color]['users'] += color_stats['unique_users'] or 0

    # Return in the format expected by the frontend
    return JsonResponse(stats)


@admin_required
def live_game_control_stats(request):
    """API endpoint for live game control statistics with detailed round information"""
    from django.db.models import Sum, Count
    from django.core.cache import cache

    # Check cache first (3 second cache for stats)
    cache_key = 'admin_live_stats'
    cached_data = cache.get(cache_key)
    if cached_data:
        return JsonResponse(cached_data)

    # Get all active rounds and recently ended rounds - Only from main room
    from datetime import timedelta
    recent_time = timezone.now() - timedelta(minutes=10)

    # Get active rounds (not ended) - Only main room
    active_rounds = GameRound.objects.filter(
        room='main',  # Only main room
        ended=False
    ).filter(
        Q(bet__isnull=False) | Q(start_time__gte=recent_time)
    ).distinct()

    # Get recently ended rounds (last 10 minutes based on start_time) - Only main room
    ended_rounds = GameRound.objects.filter(
        room='main',  # Only main room
        ended=True,
        start_time__gte=recent_time
    ).filter(
        Q(bet__isnull=False) | Q(start_time__gte=recent_time)
    ).distinct()

    # Combine and order by start time (newest first)
    all_rounds = (active_rounds | ended_rounds).order_by('-start_time')

    rounds_stats = []
    total_players = 0
    total_amount = 0

    for round_obj in all_rounds:
        # Get real player bets for this round (exclude test/dummy bets)
        bets = get_real_bets_queryset().filter(round=round_obj)

        # Calculate color statistics
        color_stats = {}
        colors = ['red', 'green', 'violet', 'blue']

        round_total_amount = 0
        round_total_players = set()

        for color in colors:
            color_bets = bets.filter(color=color)
            amount = sum(bet.amount for bet in color_bets)
            count = color_bets.count()
            users = color_bets.values('player__username').distinct().count()

            color_stats[color] = {
                'count': count,
                'amount': amount,
                'users': users
            }

            round_total_amount += amount
            # Add players to set to avoid duplicates
            for bet in color_bets:
                round_total_players.add(bet.player.username)

        # Calculate time remaining using consistent constants
        time_remaining = max(0, ROUND_DURATION - (timezone.now() - round_obj.start_time).total_seconds())

        rounds_stats.append({
            'round_id': round_obj.id,
            'period_id': round_obj.period_id,
            'room': round_obj.room,
            'color_stats': color_stats,
            'total_bets': bets.count(),
            'total_amount': round_total_amount,
            'total_players': len(round_total_players),
            'time_remaining': int(time_remaining),
            'can_select': time_remaining > 0,  # Admin can select anytime during the round (0-50s)
        })

        total_amount += round_total_amount
        total_players += len(round_total_players)

    response_data = {
        'rounds': rounds_stats,
        'summary': {
            'total_rounds': len(active_rounds),
            'total_players': total_players,
            'total_amount': total_amount,
        }
    }

    # Cache the response for 3 seconds to reduce database load
    cache.set(cache_key, response_data, 3)

    return JsonResponse(response_data)


@secure_api_endpoint(
    authentication_required=True,
    admin_required=True,
    rate_limit_per_minute=30,  # Limit to 30 submissions per minute
    rate_limit_per_hour=200,   # Limit to 200 submissions per hour
    require_json=True,
    required_fields=['round_id', 'color'],
    allowed_methods=['POST'],
    csrf_required=True  # Require CSRF protection
)
def submit_game_result(request):
    """API endpoint for submitting game results with enhanced security"""
    try:
        import json
        import re
        from django.core.exceptions import ValidationError

        # Validate request headers for additional security
        if not request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Invalid request headers'
            }, status=400)

        # Parse and validate JSON data (already validated by decorator)
        data = json.loads(request.body)
        round_id = data.get('round_id', '').strip()
        selected_color = data.get('color', '').strip().lower()

        # Enhanced input validation
        if not round_id or not selected_color:
            return JsonResponse({
                'success': False,
                'message': 'Round ID and color are required'
            }, status=400)

        # Validate round_id format (prevent injection)
        if not re.match(r'^[a-zA-Z0-9-_]+$', str(round_id)):
            return JsonResponse({
                'success': False,
                'message': 'Invalid round ID format'
            }, status=400)

        # Validate color input
        valid_colors = ['red', 'green', 'violet', 'blue']
        if selected_color not in valid_colors:
            return JsonResponse({
                'success': False,
                'message': f'Invalid color. Must be one of: {", ".join(valid_colors)}'
            }, status=400)

        # Validate timestamp to prevent replay attacks
        timestamp = data.get('timestamp')
        if timestamp:
            import time
            current_time = int(time.time() * 1000)  # Current time in milliseconds
            if abs(current_time - timestamp) > 30000:  # 30 second window
                return JsonResponse({
                    'success': False,
                    'message': 'Request timestamp is too old'
                }, status=400)

        # Get the round with secure query (prevent SQL injection)
        try:
            # Use select_for_update to prevent race conditions
            game_round = GameRound.objects.select_for_update().get(
                id=round_id,
                ended=False
            )
        except GameRound.DoesNotExist:
            # Check if round exists but is ended (secure query)
            try:
                ended_round = GameRound.objects.only('period_id').get(
                    id=round_id,
                    ended=True
                )
                return JsonResponse({
                    'success': False,
                    'message': f'Round {ended_round.period_id} has already ended'
                }, status=409)  # Conflict status
            except GameRound.DoesNotExist:
                # Check if there are any active rounds
                active_count = GameRound.objects.filter(ended=False).count()
                if active_count == 0:
                    return JsonResponse({
                        'success': False,
                        'message': 'No active rounds found. Please wait for a new round to start or create test rounds.',
                        'suggestion': 'Create test rounds from admin panel'
                    }, status=404)
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Round not found'
                    }, status=404)
        except Exception as e:
            logger.error(f"Database error in submit_game_result: {e}")
            return JsonResponse({
                'success': False,
                'message': 'Database error occurred'
            }, status=500)

        # Admin can select color anytime during the betting period (0-40 seconds)
        time_elapsed = (timezone.now() - game_round.start_time).total_seconds()
        if time_elapsed >= ROUND_DURATION:  # After round has ended
            return JsonResponse({'success': False, 'message': 'Round has ended, cannot change result'})

        # Validate color
        valid_colors = ['red', 'green', 'violet', 'blue']
        if selected_color not in valid_colors:
            return JsonResponse({'success': False, 'message': 'Invalid color selected'})

        # Map color to number (consistent with consumers.py)
        color_to_number = {
            'red': 2,      # red numbers: 2, 8
            'green': 1,    # green numbers: 1, 3, 7, 9
            'violet': 0,   # violet numbers: 0, 5
            'blue': 4      # blue numbers: 4, 6
        }

        selected_number = color_to_number[selected_color]

        # Create admin selection record using existing AdminColorSelection model
        from .models import AdminColorSelection

        # Try to get or create admin selection for this round
        admin_selection, created = AdminColorSelection.objects.get_or_create(
            round=game_round,
            defaults={
                'selected_color': selected_color,
                'selection_time': timezone.now(),
                'is_auto_selected': False
            }
        )

        # If already exists, update it
        if not created:
            admin_selection.selected_color = selected_color
            admin_selection.selection_time = timezone.now()
            admin_selection.is_auto_selected = False
            admin_selection.save()

        # End the round with the selected result
        game_round.result = selected_number
        game_round.ended = True
        game_round.end_time = timezone.now()
        game_round.save()

        # Process bets and calculate winnings (including test bets for processing)
        from .models import Bet
        bets = Bet.objects.filter(round=game_round)

        for bet in bets:
            if bet.color == selected_color:
                # Winner - use consistent 2.5x payout for all colors (same as other parts of the system)
                payout = int(bet.amount * 2.5)

                # Credit wallet for winning (this will handle balance update and transaction logging)
                bet.player.credit_wallet(
                    amount=payout,
                    transaction_type='win',
                    description=f'Win from {game_round.room} round {game_round.period_id}',
                    bet=bet
                )

                bet.result = 'win'
                bet.payout = payout  # Set payout for consistency
            else:
                bet.result = 'loss'

            bet.save()

        # Broadcast round ended event via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        if channel_layer:
            try:
                async_to_sync(channel_layer.group_send)(
                    "admin_game_control",
                    {
                        'type': 'round_ended_event',
                        'round_id': str(round_id),
                        'period_id': game_round.period_id,
                        'result_color': selected_color,
                        'result_number': selected_number
                    }
                )
            except Exception as e:
                logger.error(f"Failed to broadcast round ended event: {e}")

        # Create a new round immediately after ending the current one
        try:
            new_round = GameRound.objects.create(
                room='main',  # Only main room
                start_time=timezone.now(),
                ended=False
            )
            logger.info(f"Auto-created new round after result submission: {new_round.period_id}")
            new_round_created = True
            new_round_id = new_round.id

            # Broadcast new round started event via WebSocket
            if channel_layer:
                try:
                    async_to_sync(channel_layer.group_send)(
                        "admin_game_control",
                        {
                            'type': 'new_round_started_event',
                            'round_id': str(new_round_id),
                            'period_id': new_round.period_id
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to broadcast new round started event: {e}")

        except Exception as e:
            logger.error(f"Failed to auto-create new round: {e}")
            new_round_created = False
            new_round_id = None

        return JsonResponse({
            'success': True,
            'message': f'Result submitted successfully. {selected_color.title()} wins!',
            'result': {
                'color': selected_color,
                'number': selected_number,
                'round_id': round_id
            },
            'new_round_created': new_round_created,
            'new_round_id': new_round_id
        })

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})


@admin_required
def get_game_timer_info(request):
    """API endpoint for getting current game timer information"""
    from django.db.models import Q
    from django.core.cache import cache

    # No caching for admin timer info - real-time updates for unlimited admin access
    # cache_key = 'admin_timer_info'
    # cached_data = cache.get(cache_key)
    # if cached_data:
    #     return JsonResponse(cached_data)

    # Get active rounds
    active_rounds = GameRound.objects.filter(ended=False)

    # Safety net: If no active rounds exist, create one
    if not active_rounds.exists():
        try:
            new_round = GameRound.objects.create(
                room='main',
                start_time=timezone.now(),
                ended=False
            )
            logger.info(f"Safety net: Created new round {new_round.period_id} - no active rounds found")
            active_rounds = GameRound.objects.filter(ended=False)
        except Exception as e:
            logger.error(f"Failed to create safety net round: {e}")

    timer_info = []
    for round_obj in active_rounds:
        time_elapsed = (timezone.now() - round_obj.start_time).total_seconds()
        # Use consistent timing constants - SAME AS USER INTERFACE
        time_remaining = max(0, ROUND_DURATION - time_elapsed)

        timer_info.append({
            'round_id': round_obj.id,
            'room': round_obj.room,
            'period_id': round_obj.period_id,
            'time_remaining': int(time_remaining),
            'time_elapsed': int(time_elapsed),
            'can_select': time_elapsed < ROUND_DURATION,  # Admin can select anytime during the round (0-50s)
            'status': 'active' if time_remaining > 0 else 'ended'
        })

    response_data = {
        'success': True,
        'timers': timer_info,
        'server_time': timezone.now().isoformat()
    }

    # No caching for real-time admin access
    # cache.set(cache_key, response_data, 0.5)

    return JsonResponse(response_data)


@secure_api_endpoint(
    authentication_required=True,
    admin_required=True,
    rate_limit_per_minute=5,   # Very limited - only 5 test round creations per minute
    rate_limit_per_hour=20,    # Only 20 per hour
    require_json=False,        # No JSON body required
    required_fields=None,
    allowed_methods=['POST'],
    csrf_required=True
)
def create_test_rounds(request):
    """API endpoint to create test rounds for testing with enhanced security"""
    try:
        from datetime import timedelta
        from .models import Player, Bet
        from django.db import transaction

        # Validate request headers
        if not request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'message': 'Invalid request headers'
            }, status=400)

        # Check if admin has permission to create test rounds
        if not request.admin.is_superuser:
            # Log unauthorized attempt
            logger.warning(f"Non-superuser admin {request.admin.username} attempted to create test rounds")
            return JsonResponse({
                'success': False,
                'message': 'Insufficient permissions to create test rounds'
            }, status=403)

        # Use database transaction for atomicity
        with transaction.atomic():
            # Create test players if they don't exist (with validation)
            players = []
            for i in range(5):
                username = f"testuser{i+1}"

                # Validate username format
                if not re.match(r'^[a-zA-Z0-9_]+$', username):
                    continue

                player, created = Player.objects.get_or_create(
                    username=username,
                    defaults={
                        'balance': 1000,
                        'email': f"{username}@test.local",
                        'is_active': True
                    }
                )
                players.append(player)

        # Create only one active round for main room
        # End any existing active rounds first
        GameRound.objects.filter(ended=False).update(ended=True)

        # Create single active round for main room only
        round_obj = GameRound.objects.create(
            room='main',  # Only main room
            game_type='parity',  # Default game type
            start_time=timezone.now() - timedelta(seconds=35),  # In selection window
            ended=False
        )
        created_rounds = [round_obj]

        # Add test bets to the single round
        colors = ['green', 'red', 'violet']
        for i, player in enumerate(players):
            color = colors[i % len(colors)]
            Bet.objects.create(
                player=player,
                round=round_obj,
                bet_type='color',
                color=color,
                amount=50
            )

        return JsonResponse({
            'success': True,
            'message': f'Created {len(created_rounds)} test rounds with bets',
            'rounds': [{'id': r.id, 'type': r.game_type, 'period': r.period_id} for r in created_rounds]
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error creating test rounds: {str(e)}'})


# Removed duplicate modern_dashboard and test_modern functions
# The main admin_dashboard function already handles the modern dashboard functionality


@admin_required
def test_data_management(request):
    """Admin page to manage test data and view real vs test statistics"""

    # Get test players
    test_players = get_test_players_queryset()
    test_player_count = test_players.count()

    # Get real players (exclude test players)
    real_players = Player.objects.exclude(
        Q(username__startswith='testuser') |
        Q(username__in=['Alice', 'Bob', 'Charlie', 'Diana', 'Eve']) |
        Q(username__icontains='test') |
        Q(username__icontains='dummy') |
        Q(username__icontains='bot') |
        Q(username__icontains='demo')
    )
    real_player_count = real_players.count()

    # Get bet statistics
    total_bets = Bet.objects.count()
    real_bets = get_real_bets_queryset().count()
    test_bets = total_bets - real_bets

    # Get today's statistics
    today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

    total_bets_today = Bet.objects.filter(created_at__gte=today_start).count()
    real_bets_today = get_real_bets_queryset().filter(created_at__gte=today_start).count()
    test_bets_today = total_bets_today - real_bets_today

    # Get amount statistics
    total_amount = Bet.objects.aggregate(total=Sum('amount'))['total'] or 0
    real_amount = get_real_bets_queryset().aggregate(total=Sum('amount'))['total'] or 0
    test_amount = total_amount - real_amount

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'delete_test_players':
            # Delete test players and their bets
            test_bet_count = Bet.objects.filter(player__in=test_players).count()
            Bet.objects.filter(player__in=test_players).delete()
            deleted_players = test_players.count()
            test_players.delete()

            messages.success(request, f'Deleted {deleted_players} test players and {test_bet_count} test bets.')
            return redirect('test_data_management')

        elif action == 'delete_test_bets_only':
            # Delete only test bets, keep test players
            test_bet_count = Bet.objects.filter(player__in=test_players).count()
            Bet.objects.filter(player__in=test_players).delete()

            messages.success(request, f'Deleted {test_bet_count} test bets. Test players kept.')
            return redirect('test_data_management')

    context = {
        'test_players': test_players[:20],  # Show first 20 for display
        'test_player_count': test_player_count,
        'real_player_count': real_player_count,
        'total_bets': total_bets,
        'real_bets': real_bets,
        'test_bets': test_bets,
        'total_bets_today': total_bets_today,
        'real_bets_today': real_bets_today,
        'test_bets_today': test_bets_today,
        'total_amount': total_amount,
        'real_amount': real_amount,
        'test_amount': test_amount,
    }

    return render(request, 'admin/test_data_management.html', context)


@secure_api_endpoint(
    admin_required=True,
    allowed_methods=['DELETE'],
    rate_limit_per_minute=10
)
def delete_user(request, user_id):
    """API endpoint to delete a user (admin only)"""
    try:
        player = get_object_or_404(Player, id=user_id)

        # Log the deletion action
        AdminLog.objects.create(
            admin=request.admin,
            action='delete_user',
            description=f'Deleted user: {player.username} (ID: {player.id})',
            ip_address=get_client_ip(request)
        )

        # Store username for response
        username = player.username

        # Delete the player
        player.delete()

        return JsonResponse({
            'success': True,
            'message': f'User {username} deleted successfully'
        })

    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@admin_required
def email_service_status(request):
    """Get email service status and fallback OTPs"""
    status = BrevoEmailService.check_email_service_status()

    # Get fallback OTPs if any (for development/testing)
    from django.core.cache import cache
    fallback_otps = []

    # Only show fallback OTPs if limit reached
    if status['limit_reached']:
        keys = cache.keys('fallback_otp_*')
        for key in keys:
            email = key.replace('fallback_otp_', '')
            otp = cache.get(key)
            if otp:
                fallback_otps.append({
                    'email': email,
                    'otp': otp
                })

    return render(request, 'admin/email_service_status.html', {
        'status': status,
        'fallback_otps': fallback_otps,
        'page_title': 'Email Service Status'
    })
