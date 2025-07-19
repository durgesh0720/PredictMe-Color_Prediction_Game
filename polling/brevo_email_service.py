"""
Brevo (formerly Sendinblue) Email Service for Color Prediction Game
Handles OTP verification, password reset, and welcome emails using Brevo SMTP
"""

import logging
from typing import Optional, Tuple
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache

logger = logging.getLogger(__name__)


class BrevoEmailService:
    """
    Email service for sending authentication-related emails using Brevo SMTP
    """

    @staticmethod
    def _get_brevo_connection():
        """
        Get Brevo SMTP connection
        
        Returns:
            connection object or None if configuration is missing
        """
        if not settings.EMAIL_HOST_USER or not settings.EMAIL_HOST_PASSWORD:
            logger.error("Brevo SMTP credentials not configured")
            return None
            
        try:
            from django.core.mail import get_connection
            
            connection = get_connection(
                backend=settings.EMAIL_BACKEND,
                host=settings.EMAIL_HOST,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_HOST_USER,
                password=settings.EMAIL_HOST_PASSWORD,
                use_tls=settings.EMAIL_USE_TLS,
                fail_silently=False,
            )
            return connection
        except Exception as e:
            logger.error(f"Failed to create Brevo connection: {e}")
            return None

    @staticmethod
    def send_otp_email(email: str, otp_code: str, purpose: str = "verification") -> bool:
        """
        Send OTP verification email using Brevo SMTP

        Args:
            email: Recipient email address
            otp_code: 6-digit OTP code
            purpose: Purpose of OTP (verification, password_reset, etc.)

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            logger.info(f"Sending OTP email to {email} for {purpose} via Brevo")

            # Get Brevo connection
            connection = BrevoEmailService._get_brevo_connection()
            if not connection:
                logger.error("Failed to get Brevo connection")
                return False

            # Prepare email content
            if purpose == "verification":
                subject = "🔐 Email Verification Code - Color Prediction Game"
                template_name = "emails/otp_verification.html"
            elif purpose == "password_reset":
                subject = "🔑 Password Reset Code - Color Prediction Game"
                template_name = "emails/password_reset_otp.html"
            else:
                subject = "🔐 Verification Code - Color Prediction Game"
                template_name = "emails/otp_verification.html"

            # Context for email template
            context = {
                'otp_code': otp_code,
                'email': email,
                'expires_in': 10,  # OTP expires in 10 minutes
                'site_name': 'Color Prediction Game',
                'purpose': purpose
            }

            # Generate HTML content
            try:
                html_message = render_to_string(template_name, context)
            except Exception as e:
                logger.warning(f"Failed to render HTML template {template_name}: {e}")
                html_message = None

            # Plain text message
            plain_message = f"""
Color Prediction Game - {purpose.title()} Code

Hello,

Your verification code is: {otp_code}

This code will expire in 10 minutes.

Security Notice:
- Never share this code with anyone
- If you didn't request this code, please ignore this email

Color Prediction Game Team
            """.strip()

            # Send email using Brevo SMTP
            from django.core.mail import EmailMultiAlternatives

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
                connection=connection
            )

            # Attach HTML version if available
            if html_message:
                msg.attach_alternative(html_message, "text/html")

            # Send email
            result = msg.send()

            if result:
                logger.info(f"OTP email sent successfully to {email} via Brevo")
                
                # Track email sending for monitoring
                daily_key = f"brevo_emails_sent_{timezone.now().strftime('%Y-%m-%d')}"
                daily_count = cache.get(daily_key, 0)
                cache.set(daily_key, daily_count + 1, 86400)  # 24 hours
                
                return True
            else:
                logger.error(f"Failed to send OTP email to {email} via Brevo")
                return False

        except Exception as e:
            logger.error(f"Error sending OTP email to {email} via Brevo: {e}")
            return False

    @staticmethod
    def send_password_reset_email(email: str, otp_code: str) -> bool:
        """
        Send password reset email with OTP code

        Args:
            email: Recipient email address
            otp_code: 6-digit OTP code for password reset

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        return BrevoEmailService.send_otp_email(email, otp_code, "password_reset")

    @staticmethod
    def send_welcome_email(email: str, username: str) -> bool:
        """
        Send welcome email to new users

        Args:
            email: Recipient email address
            username: User's username

        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            logger.info(f"Sending welcome email to {email} via Brevo")

            # Get Brevo connection
            connection = BrevoEmailService._get_brevo_connection()
            if not connection:
                logger.error("Failed to get Brevo connection for welcome email")
                return False

            # Prepare email content
            subject = "🎮 Welcome to Color Prediction Game!"
            
            # Context for email template
            context = {
                'username': username,
                'email': email,
                'site_name': 'Color Prediction Game',
                'login_url': f"{getattr(settings, 'SITE_URL', 'http://localhost:8000')}/auth/login/"
            }
            
            # Generate HTML content
            try:
                html_message = render_to_string("emails/welcome.html", context)
            except Exception as e:
                logger.warning(f"Failed to render welcome HTML template: {e}")
                html_message = None
            
            # Plain text message
            plain_message = f"""
Welcome to Color Prediction Game, {username}!

Your account has been successfully created and verified.

You can now:
- Place bets on color predictions
- Manage your wallet and deposits
- Track your gaming statistics
- Win real money prizes

Login at: {context['login_url']}

Thank you for joining Color Prediction Game!

Color Prediction Game Team
            """.strip()

            # Send email using Brevo SMTP
            from django.core.mail import EmailMultiAlternatives

            # Create email message
            msg = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
                connection=connection
            )

            # Attach HTML version if available
            if html_message:
                msg.attach_alternative(html_message, "text/html")

            # Send email
            result = msg.send()

            if result:
                logger.info(f"Welcome email sent successfully to {email} via Brevo")
                
                # Track email sending for monitoring
                daily_key = f"brevo_emails_sent_{timezone.now().strftime('%Y-%m-%d')}"
                daily_count = cache.get(daily_key, 0)
                cache.set(daily_key, daily_count + 1, 86400)  # 24 hours
                
                return True
            else:
                logger.error(f"Failed to send welcome email to {email} via Brevo")
                return False

        except Exception as e:
            logger.error(f"Error sending welcome email to {email} via Brevo: {e}")
            return False

    @staticmethod
    def test_brevo_connection() -> bool:
        """
        Test Brevo SMTP connection

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            connection = BrevoEmailService._get_brevo_connection()
            if connection:
                # Try to open connection
                connection.open()
                connection.close()
                logger.info("Brevo SMTP connection test successful")
                return True
            else:
                logger.error("Brevo SMTP connection test failed - no connection")
                return False
        except Exception as e:
            logger.error(f"Brevo SMTP connection test failed: {e}")
            return False

    @staticmethod
    def get_daily_email_count() -> int:
        """
        Get the number of emails sent today via Brevo

        Returns:
            int: Number of emails sent today
        """
        daily_key = f"brevo_emails_sent_{timezone.now().strftime('%Y-%m-%d')}"
        return cache.get(daily_key, 0)

    @staticmethod
    def check_email_service_status() -> dict:
        """
        Check the status of Brevo email service

        Returns:
            dict: Status information about Brevo email service
        """
        try:
            # Get daily email count
            daily_count = BrevoEmailService.get_daily_email_count()

            # Test connection
            connection_ok = BrevoEmailService.test_brevo_connection()

            # Brevo free plan limits
            daily_limit = 300  # Free plan: 300 emails/day
            monthly_limit = 9000  # Free plan: 9,000 emails/month

            # Calculate remaining emails
            emails_remaining = max(0, daily_limit - daily_count)
            limit_reached = daily_count >= daily_limit

            status = {
                'brevo': {
                    'daily_emails_sent': daily_count,
                    'daily_limit': daily_limit,
                    'monthly_limit': monthly_limit,
                    'emails_remaining': emails_remaining,
                    'limit_reached': limit_reached,
                    'connection_ok': connection_ok,
                    'service_name': 'Brevo SMTP',
                    'host': settings.EMAIL_HOST,
                    'port': settings.EMAIL_PORT,
                    'use_tls': settings.EMAIL_USE_TLS,
                    'from_email': settings.DEFAULT_FROM_EMAIL
                },
                'current_service': 'brevo',
                'overall_status': 'operational' if connection_ok and not limit_reached else 'limited',
                'can_send_emails': connection_ok and not limit_reached
            }

            logger.info(f"Email service status check: {daily_count}/{daily_limit} emails sent today")
            return status

        except Exception as e:
            logger.error(f"Error checking email service status: {e}")
            return {
                'brevo': {
                    'daily_emails_sent': 0,
                    'daily_limit': 300,
                    'monthly_limit': 9000,
                    'emails_remaining': 300,
                    'limit_reached': False,
                    'connection_ok': False,
                    'service_name': 'Brevo SMTP',
                    'host': settings.EMAIL_HOST,
                    'port': settings.EMAIL_PORT,
                    'use_tls': settings.EMAIL_USE_TLS,
                    'from_email': settings.DEFAULT_FROM_EMAIL,
                    'error': str(e)
                },
                'current_service': 'brevo',
                'overall_status': 'error',
                'can_send_emails': False
            }
