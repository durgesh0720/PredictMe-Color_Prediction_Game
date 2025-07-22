"""
Views for the Color Prediction Game main functionality.

This module contains views for:
- Main game interface and room management
- Player statistics and game history
- Utility functions for validation
- Debug and admin redirect functionality
"""

from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Sum
import re
import logging

from .models import Player, GameRound, Bet
from .security import InputValidator, add_security_headers
from .decorators import secure_api_endpoint
from .responsible_gambling import responsible_gambling
from .monitoring import monitoring

logger = logging.getLogger(__name__)



def admin_redirect(request):
    """Redirect old admin URLs to new control panel"""
    return render(request, 'admin_redirect.html')


def debug_session(request):
    """Debug session information"""
    if not settings.DEBUG:
        return JsonResponse({'error': 'Debug mode only'})

    session_data = {
        'session_key': request.session.session_key,
        'session_data': dict(request.session),
        'is_authenticated': 'admin_id' in request.session,
    }

    return JsonResponse(session_data)


def test_chrome(request):
    """Test page for Chrome compatibility debugging"""
    if not settings.DEBUG:
        return JsonResponse({'error': 'Debug mode only'})

    return render(request, 'test_chrome.html')


def minimal_login(request):
    """Minimal login page for Chrome debugging"""
    if not settings.DEBUG:
        return JsonResponse({'error': 'Debug mode only'})

    # Import here to avoid circular imports
    from .auth_views import login_view

    if request.method == 'POST':
        # Use the same login logic but with minimal template
        response = login_view(request)
        if hasattr(response, 'status_code') and response.status_code == 302:
            # Login successful, redirect
            return response
        # Login failed, re-render minimal template with errors

    return render(request, 'minimal_login.html')


# Validation functions moved to security.py for better organization and reusability


def index(request):
    """
    Main landing page with room selection.

    Displays the game lobby with available rooms and user authentication status.
    Handles session validation and provides context for authenticated users.
    """
    # Only allow GET requests for the index page
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    current_user = None

    # Validate user session if authenticated
    if request.session.get('is_authenticated'):
        user_id = request.session.get('user_id')
        if user_id:
            try:
                current_user = Player.objects.select_related().get(
                    id=user_id,
                    is_active=True
                )
                logger.debug(f"Authenticated user {current_user.username} accessing index")
            except Player.DoesNotExist:
                logger.warning(f"Invalid user session for user_id {user_id}, flushing session")
                request.session.flush()
                messages.warning(request, 'Your session has expired. Please log in again.')

    # Get recent game statistics for display
    try:
        recent_rounds = GameRound.objects.filter(
            ended=True
        ).select_related().order_by('-start_time')[:5]

        total_players = Player.objects.filter(is_active=True).count()
        active_games = GameRound.objects.filter(ended=False).count()
    except Exception as e:
        logger.error(f"Error fetching game statistics: {e}")
        recent_rounds = []
        total_players = 0
        active_games = 0

    context = {
        'current_user': current_user,
        'is_authenticated': bool(current_user),
        'recent_rounds': recent_rounds,
        'total_players': total_players,
        'active_games': active_games,
    }

    response = render(request, "index.html", context)
    return add_security_headers(response)


def room(request, room_name):
    """
    Game room page - requires authentication.

    Provides access to the main game interface for authenticated users.
    Validates room name and user session before allowing access.
    """
    # Validate room name format
    if not re.match(r'^[a-zA-Z0-9_-]+$', room_name):
        logger.warning(f"Invalid room name format: {room_name}")
        messages.error(request, 'Invalid room name.')
        return redirect('index')

    # Force redirect to main room if accessing other rooms
    if room_name != 'main':
        logger.info(f"Redirecting from room {room_name} to main room")
        return redirect('room', room_name='main')

    # Check authentication
    if not request.session.get('is_authenticated'):
        logger.info(f"Unauthenticated access attempt to main room")
        messages.warning(request, 'Please log in to access the game room.')
        return redirect('login')

    # Validate user session
    user_id = request.session.get('user_id')
    try:
        player = Player.objects.select_related().get(id=user_id, is_active=True)
        logger.info(f"User {player.username} accessing main room")
    except Player.DoesNotExist:
        logger.warning(f"Invalid user session for user_id {user_id} accessing main room")
        request.session.flush()
        messages.error(request, 'Your account is no longer active. Please log in again.')
        return redirect('login')

    # Get current game round - only from main room
    try:
        current_round = GameRound.objects.filter(
            room='main',  # Force main room
            ended=False
        ).first()

        recent_rounds = GameRound.objects.filter(
            room='main',  # Force main room
            ended=True
        ).order_by('-start_time')[:10]

    except Exception as e:
        logger.error(f"Error fetching game data for main room: {e}")
        current_round = None
        recent_rounds = []

    context = {
        'room_name': 'main',  # Always use main room
        'player': player,
        'current_user': player,
        'current_round': current_round,
        'recent_rounds': recent_rounds,
    }

    response = render(request, "room.html", context)
    return add_security_headers(response)


def join_room(request):
    """
    Handle room joining - requires authentication.

    Validates user authentication and room name before redirecting to game room.
    """
    # Check authentication
    if not request.session.get('is_authenticated'):
        logger.info("Unauthenticated room join attempt")
        messages.warning(request, 'Please log in to join a game room.')
        return redirect('login')

    # Validate user session
    user_id = request.session.get('user_id')
    try:
        player = Player.objects.select_related().get(id=user_id, is_active=True)
    except Player.DoesNotExist:
        logger.warning(f"Invalid user session for user_id {user_id} during room join")
        request.session.flush()
        messages.error(request, 'Your account is no longer active. Please log in again.')
        return redirect('login')

    if request.method == "POST":
        room_name = InputValidator.sanitize_input(
            request.POST.get('room_name', 'main'),
            max_length=50
        ).strip()

        # Validate room name format
        if not re.match(r'^[a-zA-Z0-9_-]+$', room_name) or len(room_name) < 1:
            logger.warning(f"Invalid room name '{room_name}' from user {player.username}")
            room_name = 'main'

        logger.info(f"User {player.username} joining room {room_name}")
        return redirect('room', room_name=room_name)

    return redirect('index')



@secure_api_endpoint(
    authentication_required=False,  # Public API for player stats
    allowed_methods=['GET'],
    rate_limit_per_minute=30,
    rate_limit_per_hour=500
)
def player_stats(request, username):
    """
    Get player statistics API endpoint.

    Returns comprehensive player statistics including recent bets and performance metrics.
    """
    # Validate username format
    is_valid, clean_username = InputValidator.validate_username(username)
    if not is_valid:
        logger.warning(f"Invalid username format in stats request: {username}")
        return JsonResponse({'error': 'Invalid username format'}, status=400)

    try:
        # Use optimized query with select_related
        player = Player.objects.select_related().get(
            username=clean_username,
            is_active=True
        )

        # Get recent bets with optimized query
        recent_bets = Bet.objects.filter(
            player=player
        ).select_related('round').order_by('-created_at')[:10]

        # Calculate additional statistics
        total_wagered = Bet.objects.filter(player=player).aggregate(
            total=Sum('amount')
        )['total'] or 0

        total_winnings = Bet.objects.filter(
            player=player,
            correct=True
        ).aggregate(total=Sum('payout'))['total'] or 0

        stats = {
            'username': player.username,
            'balance': player.balance,
            'score': player.score,
            'total_bets': player.total_bets,
            'total_wins': player.total_wins,
            'win_rate': player.win_rate,
            'total_wagered': total_wagered,
            'total_winnings': total_winnings,
            'net_profit': total_winnings - total_wagered,
            'recent_bets': [
                {
                    'color': bet.color,
                    'amount': bet.amount,
                    'correct': bet.correct,
                    'round_id': bet.round.period_id if bet.round else None,
                    'created_at': bet.created_at.isoformat(),
                } for bet in recent_bets
            ]
        }

        response = JsonResponse(stats)
        return add_security_headers(response)

    except Player.DoesNotExist:
        logger.info(f"Player stats requested for non-existent user: {clean_username}")
        return JsonResponse({'error': 'Player not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching player stats for {clean_username}: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


def game_history(request):
    """
    Display recent game rounds with pagination and filtering.

    Shows completed game rounds with results and betting statistics.
    """
    try:
        # Get filter parameters
        game_type = request.GET.get('game_type', 'all')

        # Build query
        rounds_query = GameRound.objects.filter(
            ended=True,
            result_number__isnull=False
        ).select_related().prefetch_related('bet_set')

        # Apply game type filter
        if game_type != 'all' and game_type in ['parity', 'sapre', 'bcone', 'noki']:
            rounds_query = rounds_query.filter(game_type=game_type)

        # Order by most recent
        rounds_query = rounds_query.order_by('-start_time')

        # Pagination
        paginator = Paginator(rounds_query, 20)
        page_number = request.GET.get('page')
        rounds = paginator.get_page(page_number)

        context = {
            'rounds': rounds,
            'game_type': game_type,
            'available_games': ['parity', 'sapre', 'bcone', 'noki'],
        }

        response = render(request, 'game_history.html', context)
        return add_security_headers(response)

    except Exception as e:
        logger.error(f"Error fetching game history: {e}")
        messages.error(request, 'Error loading game history.')
        return redirect('index')


def upload_avatar(request):
    """
    Handle avatar upload for authenticated users.

    Validates file type, size, and user authentication before processing upload.
    """
    # Check authentication
    if not request.session.get('is_authenticated'):
        messages.warning(request, 'Please log in to upload an avatar.')
        return redirect('login')

    user_id = request.session.get('user_id')
    try:
        player = Player.objects.get(id=user_id, is_active=True)
    except Player.DoesNotExist:
        request.session.flush()
        messages.error(request, 'Your account is no longer active. Please log in again.')
        return redirect('login')

    if request.method == "POST":
        avatar = request.FILES.get('avatar')

        if avatar:
            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            if avatar.content_type not in allowed_types:
                messages.error(request, 'Please upload a valid image file (JPEG, PNG, GIF, or WebP).')
                return render(request, 'upload_avatar.html', {'player': player})

            # Validate file size (max 5MB)
            if avatar.size > 5 * 1024 * 1024:
                messages.error(request, 'Image file too large. Please upload an image smaller than 5MB.')
                return render(request, 'upload_avatar.html', {'player': player})

            try:
                player.avatar = avatar
                player.save()
                logger.info(f"Avatar uploaded successfully for user {player.username}")
                messages.success(request, 'Avatar uploaded successfully!')
                return redirect('user_profile')
            except Exception as e:
                logger.error(f"Error uploading avatar for user {player.username}: {e}")
                messages.error(request, 'Error uploading avatar. Please try again.')
        else:
            messages.error(request, 'Please select an image file to upload.')

    response = render(request, 'upload_avatar.html', {'player': player})
    return add_security_headers(response)





@secure_api_endpoint(
    authentication_required=True,  # Require authentication for bet history
    allowed_methods=['GET'],
    rate_limit_per_minute=20,
    rate_limit_per_hour=200
)
def player_bet_history(request, username):
    """
    Get player's betting history API endpoint.

    Returns paginated betting history with comprehensive bet details and statistics.
    """
    # Validate username format
    is_valid, clean_username = InputValidator.validate_username(username)
    if not is_valid:
        logger.warning(f"Invalid username format in bet history request: {username}")
        return JsonResponse({'error': 'Invalid username format'}, status=400)

    try:
        player = Player.objects.select_related().get(
            username=clean_username,
            is_active=True
        )

        # Get and validate pagination parameters
        try:
            page = max(1, int(request.GET.get('page', 1)))
            limit = min(100, max(1, int(request.GET.get('limit', 20))))  # Max 100 per page
        except (ValueError, TypeError):
            page = 1
            limit = 20

        offset = (page - 1) * limit

        # Get player's bets with optimized query
        bets = Bet.objects.filter(
            player=player
        ).select_related('round', 'player').order_by('-created_at')[offset:offset + limit]

        # Build bet history with comprehensive data
        bet_history = []
        for bet in bets:
            bet_data = {
                'id': bet.id,
                'period_id': bet.round.period_id if bet.round else None,
                'game_type': bet.round.game_type if bet.round else None,
                'bet_type': bet.bet_type,
                'color': bet.color,
                'number': bet.number,
                'amount': bet.amount,
                'correct': bet.correct,
                'payout': bet.payout,
                'profit_loss': bet.payout - bet.amount if bet.correct else -bet.amount,
                'result_number': bet.round.result_number if bet.round else None,
                'result_color': bet.round.result_color_from_number if bet.round else None,
                'round_ended': bet.round.ended if bet.round else False,
                'created_at': bet.created_at.isoformat(),
            }
            bet_history.append(bet_data)

        # Get total count for pagination
        total_count = Bet.objects.filter(player=player).count()

        # Calculate comprehensive statistics
        total_wagered = Bet.objects.filter(player=player).aggregate(
            total=Sum('amount')
        )['total'] or 0

        total_winnings = Bet.objects.filter(
            player=player,
            correct=True
        ).aggregate(total=Sum('payout'))['total'] or 0

        response_data = {
            'bets': bet_history,
            'player_stats': {
                'username': player.username,
                'balance': player.balance,
                'total_bets': player.total_bets,
                'total_wins': player.total_wins,
                'win_rate': player.win_rate,
                'total_wagered': total_wagered,
                'total_winnings': total_winnings,
                'net_profit': total_winnings - total_wagered,
            },
            'pagination': {
                'page': page,
                'limit': limit,
                'total': total_count,
                'total_pages': (total_count + limit - 1) // limit,
                'has_next': offset + limit < total_count,
                'has_previous': page > 1,
            }
        }

        response = JsonResponse(response_data)
        return add_security_headers(response)

    except Player.DoesNotExist:
        logger.info(f"Bet history requested for non-existent user: {clean_username}")
        return JsonResponse({'error': 'Player not found'}, status=404)
    except Exception as e:
        logger.error(f"Error fetching bet history for {clean_username}: {e}")
        return JsonResponse({'error': 'Internal server error'}, status=500)

def test_razorpay_simple(request):
    """Simple Razorpay test page without authentication"""
    from django.http import FileResponse
    import os

    file_path = os.path.join(settings.BASE_DIR, 'static', 'test_razorpay_simple.html')
    return FileResponse(open(file_path, 'rb'), content_type='text/html')


@secure_api_endpoint(
    authentication_required=True,
    allowed_methods=['GET'],
    rate_limit_per_minute=30,
    rate_limit_per_hour=300
)
def current_user_recent_bets(request):
    """Get recent bets for the current authenticated user"""
    try:
        # Check if user is authenticated via session
        if not request.session.get('is_authenticated'):
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)

        user_id = request.session.get('user_id')
        if not user_id:
            return JsonResponse({
                'success': False,
                'error': 'User ID not found in session'
            }, status=401)

        try:
            player = Player.objects.get(id=user_id, is_active=True)
        except Player.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': 'Player not found'
            }, status=404)

        # Get recent bets (last 10)
        recent_bets = Bet.objects.filter(
            player=player
        ).select_related('round').order_by('-created_at')[:10]

        # Format bet data
        bets_data = []
        for bet in recent_bets:
            bet_data = {
                'id': bet.id,
                'amount': bet.amount,
                'color': bet.color,
                'number': bet.number,
                'correct': bet.correct,
                'payout': bet.payout,
                'created_at': bet.created_at.isoformat(),
                'round_id': bet.round.period_id if bet.round else None,
                'round_ended': bet.round.ended if bet.round else False,
                'round_result': {
                    'number': bet.round.result_number,
                    'color': bet.round.result_color
                } if bet.round and bet.round.ended else None
            }
            bets_data.append(bet_data)

        response_data = {
            'success': True,
            'bets': bets_data,
            'player': {
                'username': player.username,
                'balance': player.balance,
                'total_bets': player.total_bets,
                'total_wins': player.total_wins
            }
        }

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error fetching recent bets for user: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)


@secure_api_endpoint(
    authentication_required=True,
    allowed_methods=['GET'],
    rate_limit_per_minute=20,
    rate_limit_per_hour=200
)
def responsible_gambling_status(request):
    """Get responsible gambling status for the current player"""
    try:
        if not hasattr(request, 'player') or not request.player:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)

        player = request.player

        # Get session statistics
        session_stats = responsible_gambling.get_session_stats(str(player.id))

        # Get daily statistics
        from django.utils import timezone
        today = timezone.now().date()

        daily_bets = Bet.objects.filter(
            player=player,
            created_at__date=today
        ).aggregate(
            total_amount=Sum('amount'),
            count=Count('id')
        )

        daily_winnings = player.transaction_set.filter(
            transaction_type='win',
            created_at__date=today
        ).aggregate(total=Sum('amount'))['total'] or 0

        daily_losses = max(0, (daily_bets['total_amount'] or 0) - daily_winnings)

        # Calculate time until cooling-off ends
        cooling_off_remaining = 0
        if session_stats.get('cooling_off_until'):
            import time
            cooling_off_remaining = max(0, session_stats['cooling_off_until'] - time.time())

        response_data = {
            'success': True,
            'session': {
                'active': session_stats.get('active', False),
                'duration_minutes': session_stats.get('session_duration', 0) / 60,
                'total_bets': session_stats.get('total_bets', 0),
                'total_losses': session_stats.get('total_losses', 0),
                'warnings_sent': session_stats.get('warnings_sent', 0),
                'cooling_off_remaining_hours': cooling_off_remaining / 3600
            },
            'daily': {
                'total_bets': daily_bets['total_amount'] or 0,
                'total_losses': daily_losses,
                'bet_count': daily_bets['count'] or 0,
                'total_winnings': daily_winnings
            },
            'limits': session_stats.get('limits', {}),
            'recommendations': []
        }

        # Add recommendations based on current status
        if session_stats.get('active'):
            session_duration_hours = session_stats.get('session_duration', 0) / 3600
            if session_duration_hours > 1:
                response_data['recommendations'].append("Consider taking a break - you've been playing for over an hour.")

            if session_stats.get('warnings_sent', 0) > 0:
                response_data['recommendations'].append("You're approaching your gambling limits. Please gamble responsibly.")

        if cooling_off_remaining > 0:
            response_data['recommendations'].append(f"Cooling-off period active for {cooling_off_remaining/3600:.1f} more hours.")

        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error getting responsible gambling status: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to retrieve gambling status'
        }, status=500)


@secure_api_endpoint
def set_gambling_limits(request):
    """Allow players to set their own gambling limits"""
    try:
        if not hasattr(request, 'player') or not request.player:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)

        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'error': 'POST method required'
            }, status=405)

        import json
        data = json.loads(request.body)
        player = request.player

        # Validate input
        validator = InputValidator()

        daily_loss_limit = validator.validate_amount(data.get('daily_loss_limit'))
        daily_bet_limit = validator.validate_amount(data.get('daily_bet_limit'))
        session_loss_limit = validator.validate_amount(data.get('session_loss_limit'))
        session_time_hours = validator.validate_positive_integer(data.get('session_time_hours', 2))

        if not all([daily_loss_limit, daily_bet_limit, session_loss_limit]):
            return JsonResponse({
                'success': False,
                'error': 'Invalid limit values'
            }, status=400)

        # Create custom limits for the player
        from .responsible_gambling import BettingLimits
        custom_limits = BettingLimits(
            daily_loss_limit=daily_loss_limit,
            daily_bet_limit=daily_bet_limit,
            session_loss_limit=session_loss_limit,
            session_time_limit=session_time_hours * 3600,  # Convert to seconds
            max_bet_amount=min(2000, daily_bet_limit // 10),  # Max 10% of daily limit per bet
            min_bet_amount=100  # ₹1 minimum
        )

        responsible_gambling.set_player_limits(str(player.id), custom_limits)

        logger.info(f"Updated gambling limits for player {player.username}")

        return JsonResponse({
            'success': True,
            'message': 'Gambling limits updated successfully',
            'limits': {
                'daily_loss_limit': daily_loss_limit,
                'daily_bet_limit': daily_bet_limit,
                'session_loss_limit': session_loss_limit,
                'session_time_hours': session_time_hours
            }
        })

    except Exception as e:
        logger.error(f"Error setting gambling limits: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to update gambling limits'
        }, status=500)


@secure_api_endpoint
def trigger_cooling_off(request):
    """Allow players to trigger a cooling-off period"""
    try:
        if not hasattr(request, 'player') or not request.player:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)

        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'error': 'POST method required'
            }, status=405)

        import json
        data = json.loads(request.body)
        player = request.player

        # Validate duration (1-168 hours, default 24)
        duration_hours = min(168, max(1, int(data.get('duration_hours', 24))))

        responsible_gambling.force_cooling_off(str(player.id), duration_hours)

        logger.info(f"Player {player.username} triggered cooling-off period for {duration_hours} hours")

        return JsonResponse({
            'success': True,
            'message': f'Cooling-off period activated for {duration_hours} hours',
            'duration_hours': duration_hours
        })

    except Exception as e:
        logger.error(f"Error triggering cooling-off: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to activate cooling-off period'
        }, status=500)


@secure_api_endpoint
def system_monitoring_dashboard(request):
    """Get system monitoring dashboard data (admin only)"""
    try:
        # Check if user is admin
        if not hasattr(request, 'player') or not request.player:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)

        # For now, allow any authenticated user - in production, add admin check
        # if not request.player.is_admin:
        #     return JsonResponse({
        #         'success': False,
        #         'error': 'Admin access required'
        #     }, status=403)

        dashboard_data = monitoring.get_dashboard_data()

        return JsonResponse({
            'success': True,
            'data': dashboard_data
        })

    except Exception as e:
        logger.error(f"Error getting monitoring dashboard: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to retrieve monitoring data'
        }, status=500)


@secure_api_endpoint
def resolve_alert(request):
    """Resolve a system alert (admin only)"""
    try:
        if not hasattr(request, 'player') or not request.player:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)

        if request.method != 'POST':
            return JsonResponse({
                'success': False,
                'error': 'POST method required'
            }, status=405)

        import json
        data = json.loads(request.body)
        alert_id = data.get('alert_id')

        if not alert_id:
            return JsonResponse({
                'success': False,
                'error': 'Alert ID required'
            }, status=400)

        monitoring.resolve_alert(alert_id)

        return JsonResponse({
            'success': True,
            'message': f'Alert {alert_id} resolved'
        })

    except Exception as e:
        logger.error(f"Error resolving alert: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Unable to resolve alert'
        }, status=500)
