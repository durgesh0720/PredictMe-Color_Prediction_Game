"""
Django signals for automatic notification handling
Ensures notifications are sent consistently for various events
"""

import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.utils import timezone
from django.core.cache import cache

from .models import (
    Player, Transaction, Bet, GameRound, 
    Notification, OTPVerification
)
from .notification_service import (
    notify_game_result, notify_wallet_transaction, 
    notify_account_activity, notify_security_alert,
    notify_system_announcement
)

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Transaction)
def handle_transaction_notification(sender, instance, created, **kwargs):
    """
    Send notification when a transaction is created (with rate limiting)
    """
    if not created:
        return

    try:
        # Skip bet transactions as they're handled separately
        if instance.transaction_type == 'bet':
            return

        # Skip win transactions as they're handled by game result signals
        if instance.transaction_type == 'win':
            return

        # Rate limit transaction notifications (max 1 per minute per user)
        cache_key = f"transaction_notification_{instance.player.id}"
        if cache.get(cache_key):
            logger.info(f"Transaction notification rate limited for {instance.player.username}")
            return

        # Send wallet transaction notification
        notify_wallet_transaction(
            user=instance.player,
            transaction_type=instance.transaction_type,
            amount=abs(instance.amount),  # Use absolute value
            new_balance=instance.balance_after
        )

        # Set rate limit (1 minute)
        cache.set(cache_key, True, 60)

        logger.info(f"Transaction notification sent for {instance.player.username}: {instance.transaction_type}")

    except Exception as e:
        logger.error(f"Error sending transaction notification: {e}")


@receiver(post_save, sender=Bet)
def handle_bet_creation_and_monitoring(sender, instance, created, **kwargs):
    """
    Handle bet creation and monitor for suspicious patterns
    """
    if created:
        # Monitor for suspicious betting patterns
        try:
            detect_suspicious_betting_patterns(instance)
        except Exception as e:
            logger.error(f"Error detecting suspicious betting patterns: {e}")
        return

    # Handle bet result notifications for processed bets
    try:
        # Only send notification if the bet has been processed (has a result)
        if not hasattr(instance, 'correct') or instance.correct is None:
            return

        # Check if we've already sent a notification for this bet
        cache_key = f"bet_notification_sent_{instance.id}"
        if cache.get(cache_key):
            return

        # Determine result and amount
        if instance.correct:
            result = 'win'
            amount = instance.payout

            # Check for big wins
            BIG_WIN_THRESHOLD = 500
            if amount >= BIG_WIN_THRESHOLD:
                send_big_win_notification(instance.player, amount, instance.round)
        else:
            result = 'loss'
            amount = instance.amount

        # Send game result notification
        notify_game_result(
            user=instance.player,
            game_round=instance.round,
            bet_result=result,
            amount=amount
        )

        # Mark notification as sent to avoid duplicates
        cache.set(cache_key, True, 3600)  # Cache for 1 hour

        logger.info(f"Bet result notification sent for {instance.player.username}: {result}")

    except Exception as e:
        logger.error(f"Error sending bet result notification: {e}")


def detect_suspicious_betting_patterns(bet_instance):
    """
    Detect suspicious betting patterns and send security alerts
    """
    try:
        player = bet_instance.player

        # Check for rapid betting (more than 10 bets in 5 minutes)
        recent_bets = Bet.objects.filter(
            player=player,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()

        if recent_bets > 10:
            cache_key = f"rapid_betting_alert_{player.id}"
            if not cache.get(cache_key):
                notify_security_alert(
                    user=player,
                    alert_type='rapid_betting',
                    details=f'Unusual betting activity detected: {recent_bets} bets placed in the last 5 minutes. If this wasn\'t you, please secure your account.'
                )
                cache.set(cache_key, True, 1800)  # 30 minutes cooldown

        # Check for unusually large bets (more than 50% of balance)
        if bet_instance.amount > (player.balance * 0.5):
            cache_key = f"large_bet_alert_{player.id}"
            if not cache.get(cache_key):
                notify_security_alert(
                    user=player,
                    alert_type='large_bet',
                    details=f'Large bet detected: ${bet_instance.amount} (more than 50% of your balance). Please ensure this was intentional.'
                )
                cache.set(cache_key, True, 3600)  # 1 hour cooldown

        # Check for consistent pattern betting (same color/number repeatedly)
        recent_same_bets = Bet.objects.filter(
            player=player,
            created_at__gte=timezone.now() - timezone.timedelta(hours=1)
        )

        if bet_instance.bet_type == 'color':
            same_color_count = recent_same_bets.filter(color=bet_instance.color).count()
            if same_color_count > 15:  # More than 15 bets on same color in 1 hour
                cache_key = f"pattern_betting_alert_{player.id}"
                if not cache.get(cache_key):
                    notify_security_alert(
                        user=player,
                        alert_type='pattern_betting',
                        details=f'Repetitive betting pattern detected: {same_color_count} consecutive bets on {bet_instance.color}. Consider varying your strategy.'
                    )
                    cache.set(cache_key, True, 7200)  # 2 hours cooldown

    except Exception as e:
        logger.error(f"Error in suspicious betting pattern detection: {e}")


@receiver(post_save, sender=Player)
def handle_player_account_changes(sender, instance, created, **kwargs):
    """
    Send notifications for player account changes
    """
    try:
        if created:
            # Welcome notification for new users
            notify_account_activity(
                user=instance,
                activity_type='account_created',
                details=f'Welcome to Color Prediction Game! Your account has been created successfully. Start playing and win big!'
            )
            logger.info(f"Welcome notification sent for new user: {instance.username}")
            return
        
        # Check for email verification
        if instance.email_verified:
            # Check if this is a recent change (not already verified)
            cache_key = f"email_verified_{instance.id}"
            if not cache.get(cache_key):
                notify_account_activity(
                    user=instance,
                    activity_type='email_verified',
                    details=f'Your email address {instance.email} has been successfully verified. You now have full access to all features!'
                )
                cache.set(cache_key, True, 86400)  # Cache for 24 hours
                logger.info(f"Email verification notification sent for: {instance.username}")
        
        # Check for profile updates (if certain fields changed)
        if hasattr(instance, '_state') and instance._state.adding is False:
            # This is an update, not a creation
            try:
                old_instance = Player.objects.get(pk=instance.pk)
                
                # Check if important profile fields changed
                profile_fields = ['first_name', 'last_name', 'phone_number', 'avatar']
                changed_fields = []
                
                for field in profile_fields:
                    if getattr(old_instance, field) != getattr(instance, field):
                        changed_fields.append(field.replace('_', ' ').title())
                
                if changed_fields:
                    notify_account_activity(
                        user=instance,
                        activity_type='profile_updated',
                        details=f'Your profile has been updated. Changed fields: {", ".join(changed_fields)}'
                    )
                    logger.info(f"Profile update notification sent for: {instance.username}")
                    
            except Player.DoesNotExist:
                pass  # Old instance not found, skip comparison
        
    except Exception as e:
        logger.error(f"Error sending player account notification: {e}")


@receiver(post_save, sender=OTPVerification)
def handle_otp_verification(sender, instance, created, **kwargs):
    """
    Send notification when OTP is generated or verified
    """
    if not created:
        return
    
    try:
        # Find the player associated with this email
        try:
            player = Player.objects.get(email=instance.email)
        except Player.DoesNotExist:
            return  # No player found for this email
        
        # Send security notification for OTP generation
        notify_security_alert(
            user=player,
            alert_type='otp_generated',
            details=f'A verification code has been sent to your email {instance.email}. If you didn\'t request this, please secure your account.'
        )
        
        logger.info(f"OTP generation notification sent for: {player.username}")
        
    except Exception as e:
        logger.error(f"Error sending OTP notification: {e}")


@receiver(post_save, sender=GameRound)
def handle_game_round_completion(sender, instance, created, **kwargs):
    """
    Send notifications when game rounds are completed
    """
    if created or not instance.ended:
        return  # Only process when round is completed
    
    try:
        # Check if we've already processed this round
        cache_key = f"round_completed_{instance.id}"
        if cache.get(cache_key):
            return
        
        # Get all bets for this round
        bets = Bet.objects.filter(round=instance)
        
        # Send notifications to all players who participated
        for bet in bets:
            try:
                # Determine if the bet won
                if bet.bet_type == 'color':
                    won = bet.color == instance.result_color
                elif bet.bet_type == 'number':
                    won = bet.number == instance.result_number
                else:
                    continue
                
                # Calculate amount
                if won:
                    if bet.bet_type == 'color':
                        amount = int(bet.amount * 2.5)  # Color multiplier
                    else:
                        amount = bet.amount * 9  # Number multiplier
                    result = 'win'
                else:
                    amount = bet.amount
                    result = 'loss'
                
                # Send notification
                notify_game_result(
                    user=bet.player,
                    game_round=instance,
                    bet_result=result,
                    amount=amount
                )
                
            except Exception as e:
                logger.error(f"Error sending game result notification for bet {bet.id}: {e}")
        
        # Mark round as processed
        cache.set(cache_key, True, 3600)  # Cache for 1 hour
        
        logger.info(f"Game round completion notifications sent for round {instance.period_id}")
        
    except Exception as e:
        logger.error(f"Error processing game round completion notifications: {e}")


def send_low_balance_notification(player):
    """
    Send low balance notification if balance is below threshold
    """
    try:
        LOW_BALANCE_THRESHOLD = 100  # $100 threshold
        
        if player.balance <= LOW_BALANCE_THRESHOLD:
            # Check if we've already sent a low balance notification recently
            cache_key = f"low_balance_notification_{player.id}"
            if cache.get(cache_key):
                return
            
            notify_wallet_transaction(
                user=player,
                transaction_type='low_balance',
                amount=player.balance,
                new_balance=player.balance
            )
            
            # Cache to prevent spam (send max once per hour)
            cache.set(cache_key, True, 3600)
            
            logger.info(f"Low balance notification sent for: {player.username}")
            
    except Exception as e:
        logger.error(f"Error sending low balance notification: {e}")


@receiver(pre_save, sender=Player)
def check_balance_changes(sender, instance, **kwargs):
    """
    Check for balance changes and send low balance notifications
    """
    try:
        if instance.pk:  # Only for existing players
            try:
                old_instance = Player.objects.get(pk=instance.pk)
                
                # If balance decreased and is now low, send notification
                if instance.balance < old_instance.balance:
                    send_low_balance_notification(instance)
                    
            except Player.DoesNotExist:
                pass
                
    except Exception as e:
        logger.error(f"Error checking balance changes: {e}")


def send_big_win_notification(player, amount, game_round):
    """
    Send notification for big wins
    """
    try:
        BIG_WIN_THRESHOLD = 500  # $500 threshold for big wins
        
        if amount >= BIG_WIN_THRESHOLD:
            notify_game_result(
                user=player,
                game_round=game_round,
                bet_result='big_win',
                amount=amount
            )
            
            logger.info(f"Big win notification sent for: {player.username} - ${amount}")
            
    except Exception as e:
        logger.error(f"Error sending big win notification: {e}")


# Custom signal for login events
@receiver(user_logged_in)
def handle_user_login(sender, request, user, **kwargs):
    """
    Send notification when user logs in (if we had Django's User model)
    Since we use custom Player model, this is handled in auth_views.py
    """
    pass


def monitor_login_attempts(player, request, success=True):
    """
    Monitor login attempts and send security alerts for suspicious activity
    """
    try:
        from .security import get_client_ip
        client_ip = get_client_ip(request)

        # Track login attempts per IP
        cache_key = f"login_attempts_{client_ip}"
        attempts = cache.get(cache_key, 0)

        if success:
            # Reset attempts on successful login
            cache.delete(cache_key)

            # Check for new device/location login
            last_ip_key = f"last_login_ip_{player.id}"
            last_ip = cache.get(last_ip_key)

            if last_ip and last_ip != client_ip:
                # New IP detected
                notify_security_alert(
                    user=player,
                    alert_type='new_device',
                    details=f'Login detected from new IP address: {client_ip}. If this wasn\'t you, please secure your account immediately.'
                )

            # Update last login IP
            cache.set(last_ip_key, client_ip, 86400 * 30)  # 30 days

        else:
            # Failed login attempt
            attempts += 1
            cache.set(cache_key, attempts, 3600)  # 1 hour

            # Alert after 5 failed attempts
            if attempts >= 5:
                notify_security_alert(
                    user=player,
                    alert_type='failed_login_attempts',
                    details=f'Multiple failed login attempts detected from IP {client_ip}. If this wasn\'t you, your account may be under attack.'
                )

    except Exception as e:
        logger.error(f"Error monitoring login attempts: {e}")


def send_weekly_summary_notifications():
    """
    Send weekly summary notifications to active users
    """
    try:
        from django.db.models import Sum, Count

        active_players = Player.objects.filter(
            is_active=True,
            email_verified=True,
            last_login__gte=timezone.now() - timezone.timedelta(days=7)
        )

        for player in active_players:
            # Calculate weekly stats
            week_ago = timezone.now() - timezone.timedelta(days=7)

            weekly_bets = Bet.objects.filter(
                player=player,
                created_at__gte=week_ago
            )

            total_bets = weekly_bets.count()
            total_wagered = weekly_bets.aggregate(Sum('amount'))['amount__sum'] or 0
            wins = weekly_bets.filter(correct=True).count()
            total_winnings = weekly_bets.filter(correct=True).aggregate(Sum('payout'))['payout__sum'] or 0

            if total_bets > 0:  # Only send if user was active
                win_rate = round((wins / total_bets) * 100, 1)
                net_result = total_winnings - total_wagered

                message = f"""
                Your weekly gaming summary:
                • Games played: {total_bets}
                • Total wagered: ${total_wagered}
                • Win rate: {win_rate}%
                • Total winnings: ${total_winnings}
                • Net result: ${net_result:+}

                Keep playing and good luck!
                """

                notify_system_announcement(
                    user=player,
                    title='📊 Your Weekly Gaming Summary',
                    message=message.strip(),
                    priority='low'
                )

        logger.info(f"Weekly summary notifications sent to {active_players.count()} users")

    except Exception as e:
        logger.error(f"Error sending weekly summary notifications: {e}")


def send_maintenance_notification():
    """
    Utility function to send maintenance notifications to all users
    """
    try:
        active_players = Player.objects.filter(is_active=True, email_verified=True)
        
        for player in active_players:
            notify_system_announcement(
                user=player,
                title='Scheduled Maintenance',
                message='The game will be under maintenance from 2:00 AM to 4:00 AM UTC. Please complete your current games before this time.',
                priority='high'
            )
        
        logger.info(f"Maintenance notifications sent to {active_players.count()} users")
        
    except Exception as e:
        logger.error(f"Error sending maintenance notifications: {e}")


def send_new_feature_notification(feature_name, description):
    """
    Utility function to send new feature notifications
    """
    try:
        active_players = Player.objects.filter(is_active=True, email_verified=True)
        
        for player in active_players:
            notify_system_announcement(
                user=player,
                title=f'New Feature: {feature_name}',
                message=description,
                priority='normal'
            )
        
        logger.info(f"New feature notifications sent to {active_players.count()} users")
        
    except Exception as e:
        logger.error(f"Error sending new feature notifications: {e}")


# Signal for suspicious activity detection
def send_security_alert_for_suspicious_activity(player, activity_type, details):
    """
    Send security alert for suspicious activities
    """
    try:
        notify_security_alert(
            user=player,
            alert_type=activity_type,
            details=details
        )
        
        logger.warning(f"Security alert sent for {player.username}: {activity_type}")
        
    except Exception as e:
        logger.error(f"Error sending security alert: {e}")


# Cleanup old notifications signal
@receiver(post_save, sender=Notification)
def cleanup_old_notifications(sender, instance, created, **kwargs):
    """
    Clean up old notifications to prevent database bloat
    """
    if not created:
        return
    
    try:
        # Keep only last 100 notifications per user
        user_notifications = Notification.objects.filter(
            user=instance.user
        ).order_by('-created_at')
        
        if user_notifications.count() > 100:
            old_notifications = user_notifications[100:]
            old_notification_ids = [n.id for n in old_notifications]
            Notification.objects.filter(id__in=old_notification_ids).delete()
            
            logger.info(f"Cleaned up old notifications for user: {instance.user.username}")
            
    except Exception as e:
        logger.error(f"Error cleaning up old notifications: {e}")
