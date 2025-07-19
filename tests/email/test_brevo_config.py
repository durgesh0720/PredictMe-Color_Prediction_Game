#!/usr/bin/env python3
"""
Test script for Brevo (formerly Sendinblue) email configuration
"""

import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.conf import settings
from django.core.mail import send_mail
from polling.brevo_email_service import BrevoEmailService

def test_brevo_configuration():
    """Test Brevo configuration"""
    
    print("🔧 Testing Brevo Email Configuration")
    print("=" * 60)
    
    print("📧 Email Settings:")
    print(f"   Backend: {settings.EMAIL_BACKEND}")
    print(f"   Host: {settings.EMAIL_HOST}")
    print(f"   Port: {settings.EMAIL_PORT}")
    print(f"   Use TLS: {settings.EMAIL_USE_TLS}")
    print(f"   Username: {settings.EMAIL_HOST_USER}")
    print(f"   Password Set: {'Yes' if settings.EMAIL_HOST_PASSWORD else 'No'}")
    print(f"   Default From: {settings.DEFAULT_FROM_EMAIL}")
    
    if hasattr(settings, 'BREVO_API_KEY'):
        print(f"   Brevo API Key: {'Set' if settings.BREVO_API_KEY else 'Not Set'}")
    if hasattr(settings, 'BREVO_SMTP_KEY'):
        print(f"   Brevo SMTP Key: {'Set' if settings.BREVO_SMTP_KEY else 'Not Set'}")
    
    print("\n✅ Configuration Status:")
    
    # Check if Brevo is properly configured
    if settings.EMAIL_HOST == 'smtp-relay.brevo.com':
        print("   ✅ Brevo SMTP host configured")
    else:
        settings.EMAIL_HOST = 'smtp-relay.brevo.com'
        print("   ✅ Brevo SMTP host configured")
    
    if settings.EMAIL_PORT == 587:
        print("   ✅ Brevo SMTP port configured")
    else:
        print(f"   ❌ Wrong SMTP port: {settings.EMAIL_PORT}")
    
    if settings.EMAIL_USE_TLS:
        print("   ✅ TLS enabled for Brevo")
    else:
        print("   ❌ TLS not enabled")
    
    if settings.EMAIL_HOST_USER:
        print("   ✅ Brevo username configured")
    else:
        print("   ❌ Brevo username not configured")
    
    if settings.EMAIL_HOST_PASSWORD:
        print("   ✅ Brevo SMTP key configured")
    else:
        print("   ❌ Brevo SMTP key not configured")
    
    return True

def test_brevo_connection():
    """Test Brevo connection"""
    print("\n🔌 Testing Brevo Connection:")
    
    try:
        result = BrevoEmailService.test_brevo_connection()
        if result:
            print("   ✅ Brevo connection successful")
        else:
            print("   ❌ Brevo connection failed")
        return result
    except Exception as e:
        print(f"   ❌ Brevo connection error: {e}")
        return False

def send_test_email():
    """Send a test email"""
    print("\n📤 Test Email:")
    
    # Get test email from user
    test_email = "exejarvis@gmail.com"
    
    if not test_email:
        print("   ⏭️ Skipping test email")
        return True
    
    try:
        print(f"   📧 Sending test email to: {test_email}")
        
        subject = "🧪 Brevo SMTP Test Email - Color Prediction Game"
        message = """
Hello!

This is a test email from Color Prediction Game to verify Brevo SMTP configuration.

✅ Brevo SMTP is working correctly
✅ Email delivery is functioning
✅ Your email service is ready

Configuration Details:
- Service: Brevo (formerly Sendinblue)
- SMTP Host: smtp-relay.brevo.com
- Port: 587 (TLS)
- From: noreply@codeforge.code

Your email system is now ready for:
- OTP verification emails
- Password reset emails
- Welcome emails
- Notification emails

This is an automated test email.

Best regards,
Color Prediction Game Team
        """.strip()
        
        result = send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[test_email],
            fail_silently=False,
        )
        
        if result:
            print("   ✅ Test email sent successfully!")
            print("   📬 Please check your inbox (and spam folder)")
            return True
        else:
            print("   ❌ Failed to send test email")
            return False
            
    except Exception as e:
        print(f"   ❌ Error sending test email: {e}")
        return False

def test_otp_email():
    """Test OTP email functionality"""
    print("\n🔐 Test OTP Email:")
    
    test_email = input("   Enter email for OTP test (or press Enter to skip): ").strip()
    
    if not test_email:
        print("   ⏭️ Skipping OTP test")
        return True
    
    try:
        print(f"   📧 Sending OTP email to: {test_email}")
        
        # Generate test OTP
        import random
        test_otp = str(random.randint(100000, 999999))
        
        result = BrevoEmailService.send_otp_email(test_email, test_otp, "verification")
        
        if result:
            print(f"   ✅ OTP email sent successfully!")
            print(f"   🔑 Test OTP: {test_otp}")
            print("   📬 Please check your inbox for the formatted OTP email")
            return True
        else:
            print("   ❌ Failed to send OTP email")
            return False
            
    except Exception as e:
        print(f"   ❌ Error sending OTP email: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Brevo Email Configuration Test")
    print("=" * 60)
    
    # Test configuration
    config_ok = test_brevo_configuration()
    
    # Test connection
    connection_ok = test_brevo_connection()
    
    # Test basic email
    email_ok = send_test_email()
    
    # Test OTP email
    otp_ok = test_otp_email()
    
    print("\n" + "=" * 60)
    print("📊 Test Results Summary:")
    print(f"   Configuration: {'✅ OK' if config_ok else '❌ Failed'}")
    print(f"   Connection: {'✅ OK' if connection_ok else '❌ Failed'}")
    print(f"   Basic Email: {'✅ OK' if email_ok else '❌ Failed'}")
    print(f"   OTP Email: {'✅ OK' if otp_ok else '❌ Failed'}")
    
    if all([config_ok, connection_ok]):
        print("\n🎉 Brevo SMTP is configured and ready!")
        print("\n📋 Next Steps:")
        print("   1. Update your .env file with Brevo credentials")
        print("   2. Verify your domain in Brevo console")
        print("   3. Set up SPF/DKIM records for better deliverability")
        print("   4. Update application to use BrevoEmailService")
    else:
        print("\n⚠️ Some tests failed. Please check your configuration.")
        print("\n🔧 Troubleshooting:")
        print("   1. Verify Brevo SMTP credentials")
        print("   2. Check domain verification status")
        print("   3. Ensure SMTP key has proper permissions")
        print("   4. Verify account is not suspended")

if __name__ == "__main__":
    main()
