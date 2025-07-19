"""
Celery tasks for scheduled notifications and background processing
"""

import logging
from datetime import timedelta
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.core.cache import cache

# Try to import Celery, fall back to regular functions if not available
try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except ImportError:
    # Celery not available, create dummy decorator
    def shared_task(func):
        return func
    CELERY_AVAILABLE = False

from .models import Player, Notification, Bet, Transaction
from .notification_service import (
    notify_system_announcement, notify_wallet_transaction,
    notify_security_alert, NotificationService
)

logger = logging.getLogger(__name__)


@shared_task
def send_daily_summary_notifications():
    """
    Send daily summary notifications to active users
    """
    try:
        active_players = Player.objects.filter(
            is_active=True,
            email_verified=True,
            last_login__gte=timezone.now() - timedelta(days=1)
        )
        
        sent_count = 0
        
        for player in active_players:
            # Check if user wants daily summaries
            cache_key = f"daily_summary_enabled_{player.id}"
            if cache.get(cache_key) == False:
                continue
            
            # Calculate daily stats
            yesterday = timezone.now() - timedelta(days=1)
            
            daily_bets = Bet.objects.filter(
                player=player,
                created_at__gte=yesterday
            )
            
            if daily_bets.exists():
                total_bets = daily_bets.count()
                total_wagered = daily_bets.aggregate(Sum('amount'))['amount__sum'] or 0
                wins = daily_bets.filter(correct=True).count()
                total_winnings = daily_bets.filter(correct=True).aggregate(Sum('payout'))['payout__sum'] or 0
                
                win_rate = round((wins / total_bets) * 100, 1) if total_bets > 0 else 0
                net_result = total_winnings - total_wagered
                
                message = f"""
                Yesterday's gaming activity:
                🎮 Games: {total_bets}
                💰 Wagered: ${total_wagered}
                🎯 Win rate: {win_rate}%
                🏆 Winnings: ${total_winnings}
                📊 Net: ${net_result:+}
                """
                
                notify_system_announcement(
                    user=player,
                    title='📈 Daily Gaming Summary',
                    message=message.strip(),
                    priority='low'
                )
                
                sent_count += 1
        
        logger.info(f"Daily summary notifications sent to {sent_count} users")
        return f"Sent {sent_count} daily summaries"
        
    except Exception as e:
        logger.error(f"Error sending daily summary notifications: {e}")
        return f"Error: {str(e)}"


@shared_task
def cleanup_old_notifications():
    """
    Clean up old notifications to prevent database bloat
    """
    try:
        # Delete notifications older than 30 days
        cutoff_date = timezone.now() - timedelta(days=30)
        
        old_notifications = Notification.objects.filter(
            created_at__lt=cutoff_date
        )
        
        deleted_count = old_notifications.count()
        old_notifications.delete()
        
        logger.info(f"Cleaned up {deleted_count} old notifications")
        return f"Deleted {deleted_count} old notifications"
        
    except Exception as e:
        logger.error(f"Error cleaning up notifications: {e}")
        return f"Error: {str(e)}"


@shared_task
def send_inactive_user_reminders():
    """
    Send reminder notifications to inactive users
    """
    try:
        # Find users who haven't logged in for 7 days
        inactive_cutoff = timezone.now() - timedelta(days=7)
        
        inactive_users = Player.objects.filter(
            is_active=True,
            email_verified=True,
            last_login__lt=inactive_cutoff
        ).exclude(
            last_login__isnull=True
        )
        
        sent_count = 0
        
        for user in inactive_users:
            # Check if we've already sent a reminder recently
            cache_key = f"inactive_reminder_sent_{user.id}"
            if cache.get(cache_key):
                continue
            
            days_inactive = (timezone.now() - user.last_login).days
            
            message = f"""
            We miss you! It's been {days_inactive} days since your last visit.
            
            🎮 New games and features are waiting for you
            💰 Your balance: ${user.balance}
            🎯 Come back and continue your winning streak!
            
            Login now to see what's new!
            """
            
            notify_system_announcement(
                user=user,
                title='🎮 We Miss You! Come Back and Play',
                message=message.strip(),
                priority='normal'
            )
            
            # Set cache to prevent spam (send max once per week)
            cache.set(cache_key, True, 604800)  # 7 days
            sent_count += 1
        
        logger.info(f"Inactive user reminders sent to {sent_count} users")
        return f"Sent {sent_count} inactive user reminders"
        
    except Exception as e:
        logger.error(f"Error sending inactive user reminders: {e}")
        return f"Error: {str(e)}"


@shared_task
def send_low_balance_reminders():
    """
    Send reminders to users with low balances
    """
    try:
        LOW_BALANCE_THRESHOLD = 50
        
        low_balance_users = Player.objects.filter(
            is_active=True,
            email_verified=True,
            balance__lte=LOW_BALANCE_THRESHOLD,
            balance__gt=0  # Don't remind users with zero balance
        )
        
        sent_count = 0
        
        for user in low_balance_users:
            # Check if we've already sent a reminder recently
            cache_key = f"low_balance_reminder_{user.id}"
            if cache.get(cache_key):
                continue
            
            message = f"""
            Your balance is running low: ${user.balance}
            
            💰 Add money to your wallet to continue playing
            🎮 Don't miss out on winning opportunities
            🚀 Top up now and get back in the game!
            """
            
            notify_wallet_transaction(
                user=user,
                transaction_type='low_balance_reminder',
                amount=user.balance,
                new_balance=user.balance
            )
            
            # Set cache to prevent spam (send max once per day)
            cache.set(cache_key, True, 86400)  # 24 hours
            sent_count += 1
        
        logger.info(f"Low balance reminders sent to {sent_count} users")
        return f"Sent {sent_count} low balance reminders"
        
    except Exception as e:
        logger.error(f"Error sending low balance reminders: {e}")
        return f"Error: {str(e)}"


@shared_task
def monitor_system_health():
    """
    Monitor system health and send alerts if needed
    """
    try:
        alerts = []
        
        # Check for high number of failed notifications
        recent_failed = Notification.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1),
            status='failed'
        ).count()
        
        if recent_failed > 10:
            alerts.append(f"High number of failed notifications: {recent_failed} in the last hour")
        
        # Check for unusual betting patterns
        recent_bets = Bet.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        # Get average bets per hour for comparison
        avg_bets = cache.get('avg_bets_per_hour', 100)
        
        if recent_bets > avg_bets * 3:  # 3x normal activity
            alerts.append(f"Unusual betting activity: {recent_bets} bets in the last hour (avg: {avg_bets})")
        
        # Update average for next check
        cache.set('avg_bets_per_hour', recent_bets, 3600)
        
        # Send alerts to admins if any issues found
        if alerts:
            # Here you would send alerts to admin users
            # For now, just log them
            for alert in alerts:
                logger.warning(f"System health alert: {alert}")
        
        return f"System health check complete. {len(alerts)} alerts found."
        
    except Exception as e:
        logger.error(f"Error in system health monitoring: {e}")
        return f"Error: {str(e)}"


@shared_task
def send_promotional_notifications():
    """
    Send promotional notifications to eligible users
    """
    try:
        # Find active users who haven't played in the last 24 hours
        eligible_users = Player.objects.filter(
            is_active=True,
            email_verified=True,
            last_login__gte=timezone.now() - timedelta(days=3)  # Active in last 3 days
        ).exclude(
            id__in=Bet.objects.filter(
                created_at__gte=timezone.now() - timedelta(hours=24)
            ).values_list('player_id', flat=True)
        )
        
        sent_count = 0
        
        for user in eligible_users:
            # Check if user wants promotional notifications
            cache_key = f"promo_notifications_enabled_{user.id}"
            if cache.get(cache_key) == False:
                continue
            
            # Check if we've sent a promo recently
            recent_promo_key = f"recent_promo_sent_{user.id}"
            if cache.get(recent_promo_key):
                continue
            
            message = f"""
            🎉 Special offer just for you!
            
            💰 Your current balance: ${user.balance}
            🎮 Play now and get bonus rewards
            🏆 Limited time offer - don't miss out!
            
            Start playing to unlock exclusive bonuses!
            """
            
            notify_system_announcement(
                user=user,
                title='🎉 Special Bonus Offer Available!',
                message=message.strip(),
                priority='normal'
            )
            
            # Set cache to prevent spam (send max once per 3 days)
            cache.set(recent_promo_key, True, 259200)  # 3 days
            sent_count += 1
        
        logger.info(f"Promotional notifications sent to {sent_count} users")
        return f"Sent {sent_count} promotional notifications"
        
    except Exception as e:
        logger.error(f"Error sending promotional notifications: {e}")
        return f"Error: {str(e)}"


# Utility function to run tasks manually if Celery is not available
def run_scheduled_tasks():
    """
    Run all scheduled tasks manually (for development or when Celery is not available)
    """
    if not CELERY_AVAILABLE:
        logger.info("Running scheduled tasks manually (Celery not available)")
        
        try:
            cleanup_old_notifications()
            send_low_balance_reminders()
            monitor_system_health()
            logger.info("Manual scheduled tasks completed")
        except Exception as e:
            logger.error(f"Error running manual scheduled tasks: {e}")
    else:
        logger.info("Celery is available, tasks should be scheduled with Celery Beat")
