from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
import json
import re
import logging
from datetime import datetime, timedelta

from .models import Player, Bet, Transaction, GameRound
from .security import InputValidator, PasswordSecurity
from .otp_utils import OTPService
from django.core.paginator import Paginator
from django.db.models import Sum, Count, Q, Max
from django.db import models
from django.contrib.auth.password_validation import validate_password
from .decorators import secure_api_endpoint, api_authentication_required
from .notification_service import notify_account_activity, notify_security_alert

logger = logging.getLogger(__name__)


def register_view(request):
    """User registration view"""
    if request.method == 'POST':
        # Get form data
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()

        # Validation
        errors = []

        # Validate username
        is_valid, result = InputValidator.validate_username(username)
        if not is_valid:
            errors.append(result)
        else:
            username = result
            # Check if username already exists
            if Player.objects.filter(username=username).exists():
                errors.append("Username already exists")

        # Validate email with domain restrictions
        is_valid_email, email_result = InputValidator.validate_email(email)
        if not is_valid_email:
            errors.append(email_result)
        else:
            email = email_result
            # Check if email already exists
            if Player.objects.filter(email=email).exists():
                errors.append("Email already exists")

        # Validate password using comprehensive security validation
        if not password:
            errors.append("Password is required")
        elif password != confirm_password:
            errors.append("Passwords do not match")
        else:
            # Use the comprehensive password validation
            password_errors = PasswordSecurity.validate_password_strength(password)
            if password_errors:
                errors.extend(password_errors)

        # Validate phone number if provided
        if phone_number:
            phone_regex = re.compile(r'^\+?1?\d{9,15}$')
            if not phone_regex.match(phone_number):
                errors.append("Invalid phone number format")

        if errors:
            context = {
                'errors': errors,
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone_number,
            }
            return render(request, 'auth/register.html', context)

        try:
            # Create new player (not verified yet)
            player = Player(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number,
                balance=0,  # No starting balance - users must deposit real money
                email_verified=False,  # Not verified yet
                is_active=True
            )
            player.set_password(password)
            player.save()

            # Send OTP for email verification
            success, message, otp = OTPService.generate_and_send_otp(email, username)

            if success:
                # Store email in session for OTP verification
                request.session['pending_verification_email'] = email
                request.session['pending_user_id'] = player.id

                messages.success(request, f'Account created successfully! Please check your email ({email}) for the verification code.')
                return redirect('verify_otp')
            else:
                # If OTP sending fails, delete the created user and show error
                player.delete()
                errors.append(f"Failed to send verification email: {message}")
                context = {
                    'errors': errors,
                    'username': username,
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'phone_number': phone_number,
                }
                return render(request, 'auth/register.html', context)

        except ValidationError as e:
            errors.append(str(e))
            context = {
                'errors': errors,
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone_number,
            }
            return render(request, 'auth/register.html', context)
        except Exception as e:
            logger.error(f"Registration error: {e}")
            errors.append("An error occurred during registration. Please try again.")
            context = {
                'errors': errors,
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone_number,
            }
            return render(request, 'auth/register.html', context)

    return render(request, 'auth/register.html')


def verify_otp_view(request):
    """OTP verification view"""
    # Check if there's a pending verification
    pending_email = request.session.get('pending_verification_email')
    pending_user_id = request.session.get('pending_user_id')

    if not pending_email or not pending_user_id:
        messages.error(request, 'No pending verification found. Please register again.')
        return redirect('register')

    if request.method == 'POST':
        otp_code = request.POST.get('otp_code', '').strip()

        if not otp_code:
            messages.error(request, 'Please enter the verification code')
            return render(request, 'auth/verify_otp.html', {'email': pending_email})

        if len(otp_code) != 6 or not otp_code.isdigit():
            messages.error(request, 'Verification code must be 6 digits')
            return render(request, 'auth/verify_otp.html', {'email': pending_email})

        # Verify OTP
        success, message = OTPService.verify_otp(pending_email, otp_code)

        if success:
            try:
                # Get the user and mark as verified
                player = Player.objects.get(id=pending_user_id, email=pending_email)
                player.email_verified = True
                player.save()

                # Send email verification notification
                try:
                    notify_account_activity(
                        player,
                        'email_verified',
                        f'Your email address {player.email} has been successfully verified. You now have full access to all features!'
                    )
                except Exception as e:
                    logger.error(f"Error sending email verification notification: {e}")

                # Log the user in
                request.session['user_id'] = player.id
                request.session['username'] = player.username
                request.session['is_authenticated'] = True
                request.session['login_time'] = timezone.now().isoformat()

                # Clear pending verification data
                del request.session['pending_verification_email']
                del request.session['pending_user_id']

                messages.success(request, f'Email verified successfully! Welcome to Color Prediction Game, {player.display_name}!')
                return redirect('welcome')  # Redirect to welcome page

            except Player.DoesNotExist:
                messages.error(request, 'User account not found. Please register again.')
                return redirect('register')
        else:
            messages.error(request, message)
            return render(request, 'auth/verify_otp.html', {'email': pending_email})

    return render(request, 'auth/verify_otp.html', {'email': pending_email})


def resend_otp_view(request):
    """Resend OTP view with rate limiting"""
    if request.method == 'POST':
        pending_email = request.session.get('pending_verification_email')
        pending_user_id = request.session.get('pending_user_id')

        if not pending_email or not pending_user_id:
            return JsonResponse({'success': False, 'message': 'No pending verification found'})

        # Rate limiting - check if user has requested OTP recently
        last_request_key = f'otp_request_{pending_email}'
        last_request_time = cache.get(last_request_key)

        if last_request_time:
            time_diff = timezone.now() - last_request_time
            if time_diff.total_seconds() < 60:  # 1 minute cooldown
                remaining_seconds = 60 - int(time_diff.total_seconds())
                return JsonResponse({
                    'success': False,
                    'message': f'Please wait {remaining_seconds} seconds before requesting another verification code.'
                })

        try:
            player = Player.objects.get(id=pending_user_id, email=pending_email)
            success, message, otp = OTPService.resend_otp(pending_email, player.username)

            if success:
                # Set rate limiting cache
                cache.set(last_request_key, timezone.now(), 60)  # 1 minute cache
                return JsonResponse({'success': True, 'message': 'Verification code sent successfully!'})
            else:
                return JsonResponse({'success': False, 'message': message})

        except Player.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User account not found'})
        except Exception as e:
            logger.error(f"Error resending OTP for {pending_email}: {e}")
            return JsonResponse({'success': False, 'message': 'An error occurred while sending verification code.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def welcome_view(request):
    """Welcome page after successful registration and verification"""
    # Check if user is authenticated
    if not request.session.get('is_authenticated'):
        return redirect('login')

    user_id = request.session.get('user_id')
    try:
        player = Player.objects.get(id=user_id, is_active=True)

        # Check if email is verified
        if not player.email_verified:
            messages.warning(request, 'Please verify your email to continue.')
            return redirect('verify_otp')

        context = {
            'player': player,
            'is_new_user': True,  # Flag to show welcome content
        }
        return render(request, 'auth/welcome.html', context)

    except Player.DoesNotExist:
        request.session.flush()
        messages.error(request, 'Your account is no longer active. Please log in again.')
        return redirect('login')


def login_view(request):
    """User login view"""
    # Check if user is already logged in
    if request.session.get('is_authenticated'):
        return redirect('user_profile')

    if request.method == 'POST':
        username_or_email = request.POST.get('username_or_email', '').strip()
        password = request.POST.get('password', '')

        if not username_or_email or not password:
            messages.error(request, 'Please provide both username/email and password')
            return render(request, 'auth/login.html', {'username_or_email': username_or_email})

        try:
            # Try to find user by username or email
            player = None
            if '@' in username_or_email:
                # It's an email
                try:
                    player = Player.objects.get(email=username_or_email, is_active=True)
                except Player.DoesNotExist:
                    pass
            else:
                # It's a username
                try:
                    player = Player.objects.get(username=username_or_email, is_active=True)
                except Player.DoesNotExist:
                    pass

            if player and player.check_password(password):
                # Check if email is verified
                if not player.email_verified:
                    # Send new OTP for verification
                    success, message, otp = OTPService.generate_and_send_otp(player.email, player.username)

                    if success:
                        # Store email in session for OTP verification
                        request.session['pending_verification_email'] = player.email
                        request.session['pending_user_id'] = player.id

                        messages.warning(request, f'Your email is not verified. We\'ve sent a verification code to {player.email}.')
                        return redirect('verify_otp')
                    else:
                        messages.error(request, f'Failed to send verification email: {message}')
                        return render(request, 'auth/login.html', {'username_or_email': username_or_email})

                # Successful login with verified email
                request.session['user_id'] = player.id
                request.session['username'] = player.username
                request.session['is_authenticated'] = True
                request.session['login_time'] = timezone.now().isoformat()

                # Update last login
                player.update_last_login()

                # Send login notification
                try:
                    from .security import get_client_ip
                    client_ip = get_client_ip(request)
                    user_agent = request.META.get('HTTP_USER_AGENT', 'Unknown')
                    browser = 'Unknown'
                    if 'Chrome' in user_agent:
                        browser = 'Chrome'
                    elif 'Firefox' in user_agent:
                        browser = 'Firefox'
                    elif 'Safari' in user_agent:
                        browser = 'Safari'
                    elif 'Edge' in user_agent:
                        browser = 'Edge'

                    notify_account_activity(
                        player,
                        'login',
                        f'You logged in from IP {client_ip} using {browser} browser at {timezone.now().strftime("%Y-%m-%d %H:%M:%S")}.'
                    )
                except Exception as e:
                    logger.error(f"Error sending login notification: {e}")

                messages.success(request, f'Welcome back, {player.display_name}!')

                # Redirect to next page if specified, otherwise to profile
                next_page = request.GET.get('next', 'welcome')
                return redirect(next_page)
            else:
                messages.error(request, 'Invalid credentials')

        except Exception as e:
            logger.error(f"Login error: {e}")
            messages.error(request, 'An error occurred during login')

        return render(request, 'auth/login.html', {'username_or_email': username_or_email})

    return render(request, 'auth/login.html')


def logout_view(request):
    """User logout view"""
    if request.session.get('is_authenticated'):
        username = request.session.get('username', 'User')
        request.session.flush()
        messages.success(request, f'Goodbye {username}! You have been logged out successfully.')
    
    return redirect('index')


def auth_required(view_func):
    """Decorator to require user authentication"""
    def wrapper(request, *args, **kwargs):
        if not request.session.get('is_authenticated'):
            messages.warning(request, 'Please log in to access this page.')
            return redirect('login')
        
        # Check if user still exists and is active
        user_id = request.session.get('user_id')
        if user_id:
            try:
                player = Player.objects.get(id=user_id, is_active=True)
                request.user = player  # Add user to request
            except Player.DoesNotExist:
                request.session.flush()
                messages.error(request, 'Your account is no longer active. Please log in again.')
                return redirect('login')
        else:
            request.session.flush()
            return redirect('login')
        
        return view_func(request, *args, **kwargs)
    return wrapper


def get_current_user(request):
    """Get current authenticated user"""
    if not request.session.get('is_authenticated'):
        return None

    user_id = request.session.get('user_id')
    if user_id:
        try:
            return Player.objects.get(id=user_id, is_active=True)
        except Player.DoesNotExist:
            request.session.flush()

    return None


@auth_required
def user_profile(request):
    """User profile view"""
    player = get_current_user(request)
    if not player:
        return redirect('login')

    context = {
        'player': player,
        'title': 'My Profile'
    }
    return render(request, 'auth/profile.html', context)


@auth_required
def edit_profile(request):
    """Edit user profile"""
    player = get_current_user(request)
    if not player:
        return redirect('login')

    if request.method == 'POST':
        # Get form data
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone_number = request.POST.get('phone_number', '').strip()
        bio = request.POST.get('bio', '').strip()
        date_of_birth = request.POST.get('date_of_birth', '').strip()

        errors = []

        # Validate phone number if provided
        if phone_number:
            phone_regex = re.compile(r'^\+?1?\d{9,15}$')
            if not phone_regex.match(phone_number):
                errors.append("Invalid phone number format")

        # Validate date of birth if provided
        if date_of_birth:
            try:
                from datetime import datetime
                birth_date = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
                if birth_date > timezone.now().date():
                    errors.append("Date of birth cannot be in the future")
            except ValueError:
                errors.append("Invalid date format")

        if errors:
            context = {
                'player': player,
                'errors': errors,
                'first_name': first_name,
                'last_name': last_name,
                'phone_number': phone_number,
                'bio': bio,
                'date_of_birth': date_of_birth,
            }
            return render(request, 'auth/edit_profile.html', context)

        try:
            # Update player profile
            player.first_name = first_name
            player.last_name = last_name
            player.phone_number = phone_number
            player.bio = bio
            if date_of_birth:
                player.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()

            player.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_profile')

        except Exception as e:
            logger.error(f"Profile update error: {e}")
            messages.error(request, 'An error occurred while updating your profile.')

    context = {
        'player': player,
        'title': 'Edit Profile'
    }
    return render(request, 'auth/edit_profile.html', context)


@auth_required
def resend_verification_email(request):
    """Resend email verification OTP"""
    if request.method != 'POST':
        messages.error(request, 'Invalid request method.')
        return redirect('user_profile')

    player = get_current_user(request)
    if not player:
        return redirect('login')

    # Check if email is already verified
    if player.email_verified:
        messages.info(request, 'Your email is already verified.')
        return redirect('user_profile')

    # Rate limiting - check if user has requested OTP recently
    last_request_key = f'otp_request_{player.email}'
    last_request_time = cache.get(last_request_key)

    if last_request_time:
        time_diff = timezone.now() - last_request_time
        if time_diff.total_seconds() < 60:  # 1 minute cooldown
            remaining_seconds = 60 - int(time_diff.total_seconds())
            messages.warning(request, f'Please wait {remaining_seconds} seconds before requesting another verification email.')
            return redirect('user_profile')

    try:
        # Send new OTP for verification
        success, message, otp = OTPService.generate_and_send_otp(player.email, player.username)

        if success:
            # Set rate limiting cache
            cache.set(last_request_key, timezone.now(), 60)  # 1 minute cache

            # Store email in session for OTP verification
            request.session['pending_verification_email'] = player.email
            request.session['pending_user_id'] = player.id

            messages.success(request, f'Verification email sent to {player.email}. Please check your inbox.')
            return redirect('verify_otp')
        else:
            messages.error(request, f'Failed to send verification email: {message}')
            return redirect('user_profile')

    except Exception as e:
        logger.error(f"Error resending verification email for {player.email}: {e}")
        messages.error(request, 'An error occurred while sending verification email. Please try again.')
        return redirect('user_profile')


@auth_required
def change_password(request):
    """Change user password"""
    player = get_current_user(request)
    if not player:
        return redirect('login')

    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')

        errors = []

        # Validate current password
        if not current_password:
            errors.append("Current password is required")
        elif not player.check_password(current_password):
            errors.append("Current password is incorrect")

        # Validate new password
        if not new_password:
            errors.append("New password is required")
        elif len(new_password) < 8:
            errors.append("New password must be at least 8 characters long")
        elif new_password != confirm_password:
            errors.append("New passwords do not match")

        if errors:
            context = {
                'player': player,
                'errors': errors,
            }
            return render(request, 'auth/change_password.html', context)

        try:
            player.set_password(new_password)
            player.save()
            messages.success(request, 'Password changed successfully!')
            return redirect('user_profile')

        except ValidationError as e:
            errors.append(str(e))
            context = {
                'player': player,
                'errors': errors,
            }
            return render(request, 'auth/change_password.html', context)
        except Exception as e:
            logger.error(f"Password change error: {e}")
            messages.error(request, 'An error occurred while changing your password.')

    context = {
        'player': player,
        'title': 'Change Password'
    }
    return render(request, 'auth/change_password.html', context)


@auth_required
def upload_avatar(request):
    """Upload user avatar"""
    player = get_current_user(request)
    if not player:
        return redirect('login')

    if request.method == 'POST':
        avatar = request.FILES.get('avatar')

        if avatar:
            # Validate file size (max 5MB)
            if avatar.size > 5 * 1024 * 1024:
                messages.error(request, 'Avatar file size must be less than 5MB.')
                return redirect('edit_profile')

            # Validate file type
            allowed_types = ['image/jpeg', 'image/png', 'image/gif']
            if avatar.content_type not in allowed_types:
                messages.error(request, 'Avatar must be a JPEG, PNG, or GIF image.')
                return redirect('edit_profile')

            try:
                player.avatar = avatar
                player.save()
                messages.success(request, 'Avatar updated successfully!')
            except Exception as e:
                logger.error(f"Avatar upload error: {e}")
                messages.error(request, 'An error occurred while uploading your avatar.')
        else:
            messages.error(request, 'Please select an avatar file.')

    return redirect('edit_profile')


def user_history(request):
    """Enhanced user betting history and statistics with detailed match information"""
    if not request.session.get('is_authenticated'):
        messages.warning(request, 'Please log in to view your history.')
        return redirect('login')

    user_id = request.session.get('user_id')
    try:
        player = Player.objects.get(id=user_id, is_active=True)
    except Player.DoesNotExist:
        request.session.flush()
        messages.error(request, 'Your account is no longer active. Please log in again.')
        return redirect('login')

    # Get filter parameters
    filter_type = request.GET.get('filter', 'all')  # all, wins, losses, pending
    game_type = request.GET.get('game_type', 'all')
    date_range = request.GET.get('date_range', '7')  # days
    color_filter = request.GET.get('color', 'all')  # all, red, green, violet

    # Build query with optimized select_related
    bets_query = Bet.objects.filter(player=player).select_related(
        'round', 'player'
    )

    # Apply filters
    if filter_type == 'wins':
        bets_query = bets_query.filter(correct=True)
    elif filter_type == 'losses':
        bets_query = bets_query.filter(correct=False)
    elif filter_type == 'pending':
        bets_query = bets_query.filter(round__ended=False)

    if game_type != 'all':
        bets_query = bets_query.filter(round__game_type=game_type)

    if color_filter != 'all':
        bets_query = bets_query.filter(color=color_filter)

    if date_range != 'all':
        days = int(date_range)
        cutoff_date = timezone.now() - timedelta(days=days)
        bets_query = bets_query.filter(created_at__gte=cutoff_date)

    # Order by most recent
    bets_query = bets_query.order_by('-created_at')

    # Pagination
    paginator = Paginator(bets_query, 25)  # 25 bets per page
    page_number = request.GET.get('page')
    bets = paginator.get_page(page_number)

    # Calculate comprehensive statistics
    all_bets = Bet.objects.filter(player=player)
    total_bets = all_bets.count()
    total_wins = all_bets.filter(correct=True).count()
    total_losses = all_bets.filter(correct=False).count()
    pending_bets = all_bets.filter(round__ended=False).count()

    total_wagered = all_bets.aggregate(Sum('amount'))['amount__sum'] or 0
    total_winnings = all_bets.filter(correct=True).aggregate(Sum('payout'))['payout__sum'] or 0
    net_profit = total_winnings - total_wagered

    # Win rate
    win_rate = (total_wins / max(total_bets - pending_bets, 1) * 100)

    # Enhanced color statistics with profit/loss
    color_stats = {}
    for color in ['red', 'green', 'violet']:
        color_bets = all_bets.filter(color=color)
        color_wins = color_bets.filter(correct=True).count()
        color_total = color_bets.count()
        color_wagered = color_bets.aggregate(Sum('amount'))['amount__sum'] or 0
        color_winnings = color_bets.filter(correct=True).aggregate(Sum('payout'))['payout__sum'] or 0
        color_profit = color_winnings - color_wagered

        color_stats[color] = {
            'total': color_total,
            'wins': color_wins,
            'losses': color_bets.filter(correct=False).count(),
            'win_rate': (color_wins / color_total * 100) if color_total > 0 else 0,
            'wagered': color_wagered,
            'winnings': color_winnings,
            'profit': color_profit
        }

    # Game type statistics
    game_stats = {}
    for game in ['parity', 'sapre', 'bcone', 'noki']:
        game_bets = all_bets.filter(round__game_type=game)
        game_wins = game_bets.filter(correct=True).count()
        game_total = game_bets.count()
        game_wagered = game_bets.aggregate(Sum('amount'))['amount__sum'] or 0
        game_winnings = game_bets.filter(correct=True).aggregate(Sum('payout'))['payout__sum'] or 0

        game_stats[game] = {
            'total': game_total,
            'wins': game_wins,
            'win_rate': (game_wins / game_total * 100) if game_total > 0 else 0,
            'wagered': game_wagered,
            'winnings': game_winnings,
            'profit': game_winnings - game_wagered
        }

    # Recent performance (last 10 bets)
    recent_bets_queryset = all_bets.filter(round__ended=True).order_by('-created_at')[:10]
    recent_bets = list(recent_bets_queryset)  # Convert to list to avoid slice issues
    recent_wins = sum(1 for bet in recent_bets if bet.correct)
    recent_performance = (recent_wins / len(recent_bets) * 100) if recent_bets else 0

    # Biggest win and loss
    biggest_win = all_bets.filter(correct=True).aggregate(
        max_payout=models.Max('payout')
    )['max_payout'] or 0

    biggest_loss = all_bets.filter(correct=False).aggregate(
        max_loss=models.Max('amount')
    )['max_loss'] or 0

    # Add enhanced bet information for display
    enhanced_bets = []
    for bet in bets:
        bet_info = {
            'bet': bet,
            'profit_loss': bet.payout - bet.amount if bet.correct else -bet.amount,
            'multiplier': round(bet.payout / bet.amount, 2) if bet.amount > 0 and bet.payout > 0 else 0,
            'round_duration': None,
            'admin_selected': False
        }

        # Check if round has ended and calculate duration
        if bet.round.ended:
            # Estimate round duration (you might want to add actual duration field to GameRound model)
            bet_info['round_duration'] = 45  # Default round duration

            # Check if admin manually selected the color and get admin details
            try:
                from .models import AdminColorSelection
                admin_selection = AdminColorSelection.objects.select_related('admin').filter(round=bet.round).first()
                if admin_selection:
                    bet_info['admin_selection'] = {
                        'selected': True,
                        'admin_username': admin_selection.admin.username if admin_selection.admin else 'System',
                        'selected_color': admin_selection.selected_color,
                        'is_auto_selected': admin_selection.is_auto_selected,
                        'selection_time': admin_selection.created_at.strftime('%H:%M:%S') if hasattr(admin_selection, 'created_at') else None
                    }
                    bet_info['admin_selected'] = not admin_selection.is_auto_selected
                else:
                    bet_info['admin_selection'] = {
                        'selected': False,
                        'admin_username': 'System',
                        'selected_color': None,
                        'is_auto_selected': True,
                        'selection_time': None
                    }
                    bet_info['admin_selected'] = False
            except Exception as e:
                bet_info['admin_selection'] = {
                    'selected': False,
                    'admin_username': 'Unknown',
                    'selected_color': None,
                    'is_auto_selected': True,
                    'selection_time': None
                }
                bet_info['admin_selected'] = False

        enhanced_bets.append(bet_info)

    context = {
        'player': player,
        'bets': bets,
        'enhanced_bets': enhanced_bets,
        'total_bets': total_bets,
        'total_wins': total_wins,
        'total_losses': total_losses,
        'pending_bets': pending_bets,
        'total_wagered': total_wagered,
        'total_winnings': total_winnings,
        'net_profit': net_profit,
        'win_rate': win_rate,
        'color_stats': color_stats,
        'game_stats': game_stats,
        'recent_performance': recent_performance,
        'biggest_win': biggest_win,
        'biggest_loss': biggest_loss,
        'filter_type': filter_type,
        'game_type': game_type,
        'date_range': date_range,
        'color_filter': color_filter,
        'available_games': ['parity', 'sapre', 'bcone', 'noki'],
        'available_colors': ['red', 'green', 'violet'],
    }

    return render(request, 'auth/user_history.html', context)


def recent_matches(request):
    """View recent matches with results for quick reference"""
    if not request.session.get('is_authenticated'):
        messages.warning(request, 'Please log in to view recent matches.')
        return redirect('login')

    user_id = request.session.get('user_id')
    try:
        player = Player.objects.get(id=user_id, is_active=True)
    except Player.DoesNotExist:
        request.session.flush()
        messages.error(request, 'Your account is no longer active. Please log in again.')
        return redirect('login')

    # Get recent completed rounds with player's bets
    recent_rounds = GameRound.objects.filter(
        ended=True
    ).select_related().prefetch_related(
        models.Prefetch(
            'bet_set',
            queryset=Bet.objects.filter(player=player).select_related('player'),
            to_attr='player_bets'
        ),
        'bet_set'
    ).order_by('-start_time')[:20]

    # Prepare match data with player participation
    matches_data = []
    for round_obj in recent_rounds:
        player_bets = getattr(round_obj, 'player_bets', [])
        total_bets = round_obj.bet_set.count()
        total_amount = round_obj.bet_set.aggregate(Sum('amount'))['amount__sum'] or 0

        # Color distribution
        color_distribution = {}
        for color in ['red', 'green', 'violet']:
            color_bets = round_obj.bet_set.filter(color=color)
            color_distribution[color] = {
                'count': color_bets.count(),
                'amount': color_bets.aggregate(Sum('amount'))['amount__sum'] or 0
            }

        match_info = {
            'round': round_obj,
            'player_bets': player_bets,
            'player_participated': len(player_bets) > 0,
            'player_won': any(bet.correct for bet in player_bets),
            'player_total_bet': sum(bet.amount for bet in player_bets),
            'player_total_payout': sum(bet.payout for bet in player_bets if bet.correct),
            'total_bets': total_bets,
            'total_amount': total_amount,
            'color_distribution': color_distribution,
            'winning_percentage': {
                'red': (color_distribution['red']['count'] / max(total_bets, 1)) * 100,
                'green': (color_distribution['green']['count'] / max(total_bets, 1)) * 100,
                'violet': (color_distribution['violet']['count'] / max(total_bets, 1)) * 100,
            }
        }
        matches_data.append(match_info)

    context = {
        'player': player,
        'matches_data': matches_data,
    }

    return render(request, 'auth/recent_matches.html', context)


@auth_required
def wallet_management(request):
    """Wallet management - redirect to secure payment dashboard"""
    # Redirect to the new secure payment dashboard
    from django.shortcuts import redirect
    return redirect('payment_dashboard')


@secure_api_endpoint(
    authentication_required=True,
    require_json=True,
    required_fields=['amount'],
    allowed_methods=['POST'],
    rate_limit_per_minute=5,  # Strict rate limiting for payment operations
    rate_limit_per_hour=20
)
def add_money(request):
    """Redirect to secure payment system - DEPRECATED"""
    # This endpoint is deprecated and redirects to the secure payment system
    return JsonResponse({
        'success': False,
        'message': 'This endpoint is deprecated. Please use the secure payment system.',
        'redirect_url': '/payment/dashboard/',
        'deprecated': True
    })


@auth_required
def transaction_history(request):
    """View detailed transaction history"""

    # Get filter parameters
    transaction_type = request.GET.get('type', 'all')
    date_range = request.GET.get('date_range', '30')  # days

    # Build query
    transactions_query = Transaction.objects.filter(player=request.user)

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
    paginator = Paginator(transactions_query, 25)  # 25 transactions per page
    page_number = request.GET.get('page')
    transactions = paginator.get_page(page_number)

    # Calculate statistics
    total_deposits = transactions_query.filter(
        transaction_type='deposit'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    total_withdrawals = transactions_query.filter(
        transaction_type='withdrawal'
    ).aggregate(Sum('amount'))['amount__sum'] or 0

    context = {
        'player': request.user,
        'transactions': transactions,
        'total_deposits': total_deposits,
        'total_withdrawals': abs(total_withdrawals),  # Make positive for display
        'transaction_type': transaction_type,
        'date_range': date_range,
    }

    return render(request, 'auth/transaction_history.html', context)
