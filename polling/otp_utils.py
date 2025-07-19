# OTP Utilities for Email Verification

import logging
from django.conf import settings
from .models import OTPVerification

logger = logging.getLogger(__name__)


class OTPService:
    """Service class for handling OTP generation and email sending"""
    
    @staticmethod
    def generate_and_send_otp(email, username=None):
        """
        Generate OTP and send it via email
        Returns (success, message, otp_object)
        """
        try:
            # Generate new OTP
            otp = OTPVerification.generate_otp(email)
            
            # Send email
            success, message = OTPService.send_otp_email(email, otp.otp_code, username)
            
            if success:
                logger.info(f"OTP sent successfully to {email}")
                return True, "OTP sent successfully to your email", otp
            else:
                logger.error(f"Failed to send OTP to {email}: {message}")
                return False, f"Failed to send OTP: {message}", None
                
        except Exception as e:
            logger.error(f"Error generating/sending OTP for {email}: {e}")
            return False, "An error occurred while sending OTP", None
    
    @staticmethod
    def send_otp_email(email, otp_code, username=None):
        """
        Send OTP email using the dedicated email service
        Returns (success, message)
        """
        try:
            # Use Brevo email service for OTP emails
            from .brevo_email_service import BrevoEmailService

            success = BrevoEmailService.send_otp_email(email, otp_code, "verification")

            if success:
                return True, "OTP email sent successfully"
            else:
                return False, "Failed to send OTP email"

        except Exception as e:
            logger.error(f"Error sending email to {email}: {e}")
            return False, str(e)
    
    @staticmethod
    def verify_otp(email, otp_code):
        """
        Verify OTP code for email (includes fallback OTP check)
        Returns (success, message)
        """
        try:
            # First try normal OTP verification
            success, message = OTPVerification.verify_otp(email, otp_code)

            if success:
                logger.info(f"OTP verified successfully for {email}")
                return success, message

            # If normal verification fails, check fallback OTP
            from .email_service import EmailService
            fallback_otp = EmailService.get_fallback_otp(email)

            if fallback_otp and fallback_otp == otp_code:
                logger.info(f"Fallback OTP verified successfully for {email}")
                # Clear the fallback OTP after successful verification
                from django.core.cache import cache
                cache.delete(f"fallback_otp_{email}")
                return True, "OTP verified successfully"

            logger.warning(f"OTP verification failed for {email}: {message}")
            return success, message

        except Exception as e:
            logger.error(f"Error verifying OTP for {email}: {e}")
            return False, "An error occurred during verification"
    
    @staticmethod
    def resend_otp(email, username=None):
        """
        Resend OTP to email (generates new OTP)
        Returns (success, message)
        """
        try:
            # Check if there's a recent OTP (within last 2 minutes) to prevent spam
            from django.utils import timezone
            from datetime import timedelta
            
            recent_otp = OTPVerification.objects.filter(
                email=email,
                created_at__gte=timezone.now() - timedelta(minutes=2)
            ).first()
            
            if recent_otp:
                return False, "Please wait 2 minutes before requesting a new OTP"
            
            # Generate and send new OTP
            success, message, otp_obj = OTPService.generate_and_send_otp(email, username)
            return success, message
            
        except Exception as e:
            logger.error(f"Error resending OTP for {email}: {e}")
            return False, "An error occurred while resending OTP"
