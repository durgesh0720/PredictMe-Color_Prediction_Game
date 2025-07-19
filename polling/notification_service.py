"""
Comprehensive Notification Service for Color Prediction Game
Handles email notifications, in-app notifications, and user preferences
"""

import logging
from typing import Dict, List, Optional, Union
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import (
    Player, Notification, NotificationType, 
    UserNotificationPreference
)

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Central service for handling all types of notifications
    """
    
    def __init__(self):
        self.channel_layer = get_channel_layer()
    
    def create_notification(
        self,
        user: Player,
        notification_type_name: str,
        title: str,
        message: str,
        html_message: str = "",
        priority: str = "normal",
        extra_data: Dict = None,
        expires_in_hours: int = None
    ) -> Optional[Notification]:
        """
        Create a new notification for a user
        
        Args:
            user: The user to notify
            notification_type_name: Name of the notification type
            title: Notification title
            message: Plain text message
            html_message: HTML formatted message (optional)
            priority: Notification priority (low, normal, high, urgent)
            extra_data: Additional data to store with notification
            expires_in_hours: Hours until notification expires (optional)
        
        Returns:
            Created Notification object or None if failed
        """
        try:
            # Get notification type
            notification_type = NotificationType.objects.get(
                name=notification_type_name,
                is_active=True
            )
            
            # Check user preferences
            preference = self.get_user_preference(user, notification_type)
            if not preference or not preference.is_enabled:
                logger.info(f"Notification {notification_type_name} disabled for user {user.username}")
                return None
            
            # Calculate expiration
            expires_at = None
            if expires_in_hours:
                expires_at = timezone.now() + timezone.timedelta(hours=expires_in_hours)
            
            # Create notification
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                html_message=html_message or self.generate_html_message(title, message),
                priority=priority,
                extra_data=extra_data or {},
                expires_at=expires_at
            )
            
            # Send notification based on user preferences
            self.deliver_notification(notification, preference)
            
            logger.info(f"Created notification {notification.id} for user {user.username}")
            return notification
            
        except NotificationType.DoesNotExist:
            logger.error(f"Notification type '{notification_type_name}' not found")
            return None
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            return None
    
    def deliver_notification(self, notification: Notification, preference: UserNotificationPreference):
        """
        Deliver notification based on user preferences
        """
        delivery_method = preference.delivery_method

        try:
            # Only send email for specific notification types (OTP, password reset, security)
            email_notification_types = ['password_changed', 'security_alert', 'login_alert', 'email_verified']

            # Send email if enabled AND it's a critical notification type
            if (delivery_method in ['email', 'both'] and
                preference.notification_type.email_enabled and
                preference.notification_type.name in email_notification_types):
                self.send_email_notification(notification)

            # Always send in-app notification if enabled
            if delivery_method in ['in_app', 'both'] and preference.notification_type.in_app_enabled:
                self.send_in_app_notification(notification)

        except Exception as e:
            logger.error(f"Error delivering notification {notification.id}: {e}")
            notification.status = 'failed'
            notification.save()
    
    def send_email_notification(self, notification: Notification):
        """
        Send email notification
        """
        try:
            user = notification.user
            
            # Rate limiting check - more lenient for important notifications
            rate_limit_key = f"email_notification_{user.id}"
            recent_emails = cache.get(rate_limit_key, 0)

            # Different limits based on notification priority
            max_emails = 20 if notification.priority in ['high', 'urgent'] else 15

            if recent_emails >= max_emails:  # Max emails per hour
                logger.warning(f"Email rate limit exceeded for user {user.username} ({recent_emails}/{max_emails})")
                # Still mark as delivered for in-app, just skip email
                notification.in_app_delivered = True
                notification.in_app_delivered_at = timezone.now()
                notification.status = 'delivered'
                notification.save()
                return False
            
            # Prepare email content
            subject = f"🎮 {notification.title}"
            
            # Use HTML message if available, otherwise generate from plain text
            html_content = notification.html_message or self.generate_html_email(notification)
            
            # Send email using Gmail rotation system
            from .email_service import EmailService

            success = EmailService.send_email_with_rotation(
                subject=subject,
                message=notification.message,
                recipient_email=user.email,
                html_message=html_content
            )
            
            if success:
                # Update notification status
                notification.email_sent = True
                notification.email_sent_at = timezone.now()
                notification.status = 'sent'
                notification.save()
                
                # Update rate limiting
                cache.set(rate_limit_key, recent_emails + 1, 3600)  # 1 hour
                
                logger.info(f"Email notification sent to {user.email}")
                return True
            else:
                logger.error(f"Failed to send email to {user.email}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
            notification.status = 'failed'
            notification.save()
            return False
    
    def send_in_app_notification(self, notification: Notification):
        """
        Send real-time in-app notification via WebSocket
        """
        try:
            user = notification.user
            
            # Prepare notification data
            notification_data = {
                'type': 'notification',
                'notification': {
                    'id': notification.id,
                    'title': notification.title,
                    'message': notification.message,
                    'priority': notification.priority,
                    'category': notification.notification_type.category,
                    'created_at': notification.created_at.isoformat(),
                    'extra_data': notification.extra_data,
                }
            }
            
            # Send to user's WebSocket group
            user_group = f"user_{user.id}"
            
            if self.channel_layer:
                async_to_sync(self.channel_layer.group_send)(
                    user_group,
                    {
                        'type': 'send_notification',
                        'notification_data': notification_data
                    }
                )
                
                # Update notification status
                notification.in_app_delivered = True
                notification.in_app_delivered_at = timezone.now()
                if notification.status == 'pending':
                    notification.status = 'delivered'
                notification.save()
                
                logger.info(f"In-app notification sent to user {user.username}")
                return True
            else:
                logger.warning("Channel layer not available for WebSocket notifications")
                return False
                
        except Exception as e:
            logger.error(f"Error sending in-app notification: {e}")
            return False
    
    def get_user_preference(self, user: Player, notification_type: NotificationType) -> Optional[UserNotificationPreference]:
        """
        Get user preference for a notification type, create default if not exists
        """
        try:
            preference = UserNotificationPreference.objects.get(
                user=user,
                notification_type=notification_type
            )
            return preference
        except UserNotificationPreference.DoesNotExist:
            # Create default preference
            return UserNotificationPreference.objects.create(
                user=user,
                notification_type=notification_type,
                delivery_method='both' if notification_type.default_enabled else 'none',
                is_enabled=notification_type.default_enabled
            )
    
    def generate_html_message(self, title: str, message: str) -> str:
        """
        Generate basic HTML message from plain text
        """
        return f"""
        <div style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h3 style="color: #333;">{title}</h3>
            <p style="color: #666;">{message}</p>
        </div>
        """
    
    def generate_html_email(self, notification: Notification) -> str:
        """
        Generate HTML email content for notification
        """
        context = {
            'notification': notification,
            'user': notification.user,
            'site_name': 'Color Prediction Game',
        }
        
        try:
            # Try to use specific template for notification type
            template_name = f'notifications/email/{notification.notification_type.category}.html'
            return render_to_string(template_name, context)
        except:
            # Fall back to generic template
            try:
                return render_to_string('notifications/email/generic.html', context)
            except:
                # Final fallback to simple HTML
                return self.generate_html_message(notification.title, notification.message)


# Convenience functions for common notification types
def notify_game_result(user: Player, game_round, bet_result: str, amount):
    """Send game result notification"""
    service = NotificationService()

    # Convert Decimal to float for JSON serialization
    amount_float = float(amount) if hasattr(amount, '__float__') else amount

    if bet_result == 'win':
        title = f"🎉 Congratulations! You Won!"
        message = f"You won ₹{amount_float} in game round #{game_round.id}. Your winning color was {game_round.result_color}!"
    else:
        title = f"😔 Better Luck Next Time"
        message = f"You lost ₹{amount_float} in game round #{game_round.id}. The winning color was {game_round.result_color}."
    
    return service.create_notification(
        user=user,
        notification_type_name='game_result',
        title=title,
        message=message,
        priority='normal',
        extra_data={
            'game_round_id': game_round.id,
            'result': bet_result,
            'amount': amount,
            'winning_color': game_round.result_color
        }
    )


def notify_wallet_transaction(user: Player, transaction_type: str, amount, new_balance):
    """Send wallet transaction notification"""
    service = NotificationService()

    # Convert Decimal to float for JSON serialization
    amount_float = float(amount) if hasattr(amount, '__float__') else amount
    balance_float = float(new_balance) if hasattr(new_balance, '__float__') else new_balance

    if transaction_type == 'deposit':
        title = f"💰 Money Added to Wallet"
        message = f"₹{amount_float} has been added to your wallet. New balance: ₹{balance_float}"
    elif transaction_type == 'withdrawal':
        title = f"💸 Money Withdrawn"
        message = f"₹{amount_float} has been withdrawn from your wallet. New balance: ₹{balance_float}"
    else:
        title = f"💳 Wallet Transaction"
        message = f"Transaction of ₹{amount_float} completed. New balance: ₹{balance_float}"

    return service.create_notification(
        user=user,
        notification_type_name='wallet_transaction',
        title=title,
        message=message,
        priority='normal',
        extra_data={
            'transaction_type': transaction_type,
            'amount': amount_float,
            'new_balance': balance_float
        }
    )


def notify_account_activity(user: Player, activity_type: str, details: str):
    """Send account activity notification"""
    service = NotificationService()

    title_map = {
        'login': '🔐 Account Login',
        'password_change': '🔒 Password Changed',
        'email_verified': '✅ Email Verified',
        'profile_updated': '👤 Profile Updated',
    }

    title = title_map.get(activity_type, '📱 Account Activity')

    return service.create_notification(
        user=user,
        notification_type_name='account_activity',
        title=title,
        message=details,
        priority='normal',
        extra_data={'activity_type': activity_type}
    )


def notify_system_announcement(user: Player, title: str, message: str, priority: str = 'normal'):
    """Send system announcement notification"""
    service = NotificationService()

    return service.create_notification(
        user=user,
        notification_type_name='system_announcement',
        title=f"📢 {title}",
        message=message,
        priority=priority,
        extra_data={'announcement': True}
    )


def notify_security_alert(user: Player, alert_type: str, details: str):
    """Send security alert notification"""
    service = NotificationService()

    title_map = {
        'suspicious_login': '🚨 Suspicious Login Detected',
        'password_reset': '🔐 Password Reset Request',
        'account_locked': '🔒 Account Temporarily Locked',
        'new_device': '📱 New Device Login',
    }

    title = title_map.get(alert_type, '🔒 Security Alert')

    return service.create_notification(
        user=user,
        notification_type_name='security_alert',
        title=title,
        message=details,
        priority='high',
        extra_data={'alert_type': alert_type}
    )
