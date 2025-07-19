from django.core.management.base import BaseCommand
from django.conf import settings
from polling.otp_utils import OTPService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Test OTP email sending functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email address to send test OTP to'
        )
        parser.add_argument(
            '--username',
            type=str,
            default='TestUser',
            help='Username for the test (default: TestUser)'
        )

    def handle(self, *args, **options):
        email = options['email']
        username = options['username']
        
        self.stdout.write(
            self.style.SUCCESS('🧪 Testing OTP Email Functionality')
        )
        self.stdout.write('=' * 50)
        
        # Display current email configuration
        self.stdout.write(f"📧 Email Backend: {settings.EMAIL_BACKEND}")
        self.stdout.write(f"🌐 Email Host: {settings.EMAIL_HOST}")
        self.stdout.write(f"🔌 Email Port: {settings.EMAIL_PORT}")
        self.stdout.write(f"👤 Email User: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"🔑 Password Set: {'Yes' if settings.EMAIL_HOST_PASSWORD else 'No'}")
        self.stdout.write('-' * 50)
        
        # Test OTP generation and sending
        self.stdout.write(f"📤 Sending OTP to: {email}")
        self.stdout.write(f"👤 Username: {username}")
        
        try:
            success, message, otp = OTPService.generate_and_send_otp(email, username)
            
            if success:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {message}")
                )
                self.stdout.write(f"🔐 OTP Code: {otp.otp_code}")
                self.stdout.write(f"⏰ Expires at: {otp.expires_at}")
                self.stdout.write(f"🔄 Attempts allowed: {otp.max_attempts}")
                self.stdout.write(
                    self.style.WARNING("📬 Please check your email inbox (and spam folder)")
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f"❌ {message}")
                )
                self.stdout.write(
                    self.style.WARNING("🔧 Troubleshooting tips:")
                )
                self.stdout.write("   1. Check your Brevo SMTP key")
                self.stdout.write("   2. Ensure Brevo account is verified")
                self.stdout.write("   3. Verify EMAIL_HOST_PASSWORD in .env")
                self.stdout.write("   4. Check if domain is verified in Brevo")
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"💥 Error: {e}")
            )
            logger.error(f"OTP test command error: {e}")
        
        self.stdout.write('=' * 50)
        self.stdout.write("🏁 OTP test completed")
