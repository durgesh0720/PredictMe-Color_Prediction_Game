#!/usr/bin/env python
"""
Test script to verify Gmail SMTP configuration
Run this to test if email sending works properly
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.core.mail import send_mail
from django.template.loader import render_to_string
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_email_configuration():
    """Test the email configuration"""
    print("🔧 Testing Gmail SMTP Configuration...")
    print(f"📧 Email Backend: {settings.EMAIL_BACKEND}")
    print(f"🌐 Email Host: {settings.EMAIL_HOST}")
    print(f"🔌 Email Port: {settings.EMAIL_PORT}")
    print(f"🔐 Email Use TLS: {settings.EMAIL_USE_TLS}")
    print(f"👤 Email User: {settings.EMAIL_HOST_USER}")
    print(f"🔑 Email Password Set: {'Yes' if settings.EMAIL_HOST_PASSWORD else 'No'}")
    print(f"📨 Default From Email: {settings.DEFAULT_FROM_EMAIL}")
    print("-" * 50)

def send_test_email(to_email):
    """Send a test email"""
    try:
        subject = "🧪 Test Email - Color Prediction Game"
        
        html_message = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Test Email</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: linear-gradient(45deg, #667eea, #764ba2); color: white; padding: 20px; border-radius: 10px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; border-radius: 10px; margin-top: 20px; }
                .success { color: #059669; font-weight: bold; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎮 Color Prediction Game</h1>
                    <h2>Email Configuration Test</h2>
                </div>
                <div class="content">
                    <p>Hello!</p>
                    <p class="success">✅ Congratulations! Your Brevo SMTP configuration is working correctly.</p>
                    <p>This test email confirms that:</p>
                    <ul>
                        <li>📧 Brevo SMTP connection is successful</li>
                        <li>🔐 SMTP key authentication is working</li>
                        <li>📨 Email delivery is functioning properly</li>
                        <li>🎨 HTML email formatting is supported</li>
                    </ul>
                    <p>Your OTP verification system is now ready to send verification codes to users!</p>
                    <hr>
                    <p><small>This is an automated test email from Color Prediction Game.</small></p>
                </div>
            </div>
        </body>
        </html>
        """
        
        plain_message = """
        Color Prediction Game - Email Configuration Test

        Congratulations! Your Brevo SMTP configuration is working correctly.

        This test email confirms that:
        - Brevo SMTP connection is successful
        - SMTP key authentication is working
        - Email delivery is functioning properly
        - HTML email formatting is supported

        Your OTP verification system is now ready to send verification codes to users!

        This is an automated test email from Color Prediction Game.
        """
        
        print(f"📤 Sending test email to: {to_email}")
        
        result = send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[to_email],
            html_message=html_message,
            fail_silently=False,
        )
        
        if result:
            print("✅ Test email sent successfully!")
            print("📬 Please check your inbox (and spam folder) for the test email.")
            return True
        else:
            print("❌ Failed to send test email.")
            return False
            
    except Exception as e:
        print(f"❌ Error sending test email: {e}")
        logger.error(f"Email test error: {e}")
        return False

def main():
    """Main test function"""
    print("🚀 Starting Email Configuration Test")
    print("=" * 50)
    
    # Test configuration
    test_email_configuration()
    
    # Get test email address
    test_email = input("📧 Enter your email address to receive test email: ").strip()
    
    if not test_email:
        print("❌ No email address provided. Exiting.")
        return
    
    # Validate email format
    import re
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, test_email):
        print("❌ Invalid email format. Please enter a valid email address.")
        return
    
    print(f"🎯 Testing email delivery to: {test_email}")
    print("-" * 50)
    
    # Send test email
    success = send_test_email(test_email)
    
    print("=" * 50)
    if success:
        print("🎉 Email test completed successfully!")
        print("💡 Your OTP verification system is ready to use.")
    else:
        print("💥 Email test failed!")
        print("🔧 Please check your Brevo configuration:")
        print("   1. Verify your Brevo account is active")
        print("   2. Generate a new SMTP key in Brevo dashboard")
        print("   3. Update EMAIL_HOST_PASSWORD in .env file")
        print("   4. Ensure domain is verified in Brevo")

if __name__ == "__main__":
    main()
