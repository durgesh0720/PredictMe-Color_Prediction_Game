# Email System Documentation

This directory contains documentation for the email system used in the Color Prediction Game.

## 📧 Email Service

The application uses **Brevo SMTP** for sending emails including:
- OTP verification emails
- Password reset emails  
- Welcome emails
- Notification emails

## 📋 Documentation Files

### Setup Guides
- **[BREVO_SETUP_GUIDE.md](./BREVO_SETUP_GUIDE.md)** - Complete Brevo SMTP setup guide

### Email Templates
- **OTP Verification** - `templates/emails/otp_verification.html`
- **Password Reset** - `templates/emails/password_reset_otp.html`
- **Welcome Email** - `templates/emails/welcome.html`

## 🔧 Configuration

### Environment Variables
```env
# Brevo SMTP Configuration
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-brevo-email@domain.com
EMAIL_HOST_PASSWORD=your-brevo-smtp-key
DEFAULT_FROM_EMAIL=noreply@yourdomain.com

# Brevo API Configuration
BREVO_API_KEY=your-brevo-api-key
BREVO_SMTP_KEY=your-brevo-smtp-key
```

## 📊 Email Service Features

### Daily Limits
- **Free Plan**: 300 emails/day
- **Paid Plans**: Higher limits available

### Email Types
- **Authentication**: OTP verification, password reset
- **Welcome**: New user onboarding
- **Notifications**: System notifications (if enabled)

## 🧪 Testing

### Test Files
- **tests/email/test_brevo_config.py** - Brevo configuration tests
- **tests/email/test_email_delivery.py** - Email delivery tests

### Manual Testing
```python
from polling.brevo_email_service import BrevoEmailService

# Test connection
BrevoEmailService.test_brevo_connection()

# Send test OTP
BrevoEmailService.send_otp_email("test@example.com", "123456", "verification")
```

## 🔍 Troubleshooting

### Common Issues
1. **Authentication Failed** - Check SMTP credentials
2. **Daily Limit Exceeded** - Monitor usage or upgrade plan
3. **Emails in Spam** - Set up domain authentication (SPF/DKIM)

### Monitoring
```python
# Check daily usage
from polling.brevo_email_service import BrevoEmailService
count = BrevoEmailService.get_daily_email_count()
print(f"Emails sent today: {count}")
```

## 📚 Related Documentation

- **[System Documentation](../system/)** - Overall system architecture
- **[API Documentation](../api/)** - API endpoints
- **[User Documentation](../user/)** - User guides
