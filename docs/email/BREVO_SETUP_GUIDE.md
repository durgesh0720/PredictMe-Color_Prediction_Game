# Brevo (Sendinblue) Email Configuration Guide

## Overview
This guide helps you configure Brevo (formerly Sendinblue) SMTP for the Color Prediction Game email system.

## Why Brevo?

✅ **Reliable**: 99.9% uptime guarantee
✅ **Generous Free Tier**: 300 emails/day free
✅ **Easy Setup**: Simple SMTP configuration
✅ **Good Deliverability**: High inbox placement rates
✅ **Advanced Features**: Templates, analytics, automation
✅ **Global Infrastructure**: Multiple data centers

## Brevo Account Setup

### 1. Create Brevo Account
1. Go to [https://www.brevo.com](https://www.brevo.com)
2. Sign up for a free account
3. Verify your email address
4. Complete account setup

### 2. Domain Verification (Recommended)
1. In Brevo dashboard, go to "Senders & IP"
2. Click "Domains"
3. Add your domain: `codeforge.code`
4. Add the provided DNS records:

**SPF Record (TXT)**
```
codeforge.code → "v=spf1 include:spf.brevo.com mx ~all"
```

**DKIM Record (CNAME)**
```
mail._domainkey.codeforge.code → mail._domainkey.brevo.com
```

**DMARC Record (TXT)**
```
_dmarc.codeforge.code → "v=DMARC1; p=none; rua=mailto:dmarc@codeforge.code"
```

### 3. Get SMTP Credentials
1. In Brevo dashboard, go to "SMTP & API"
2. Click "SMTP" tab
3. Note down:
   - **SMTP Server**: `smtp-relay.brevo.com`
   - **Port**: `587` (TLS)
   - **Login**: Your Brevo account email
   - **SMTP Key**: Generate new SMTP key

## Environment Configuration

### Update .env File
```env
# Email Configuration (Brevo SMTP)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp-relay.brevo.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-brevo-email@domain.com
EMAIL_HOST_PASSWORD=your-brevo-smtp-key
DEFAULT_FROM_EMAIL=noreply@codeforge.code

# Brevo Configuration
BREVO_API_KEY=your-brevo-api-key
BREVO_SMTP_KEY=your-brevo-smtp-key
```

### Example Values
```env
EMAIL_HOST_USER=admin@codeforge.code
EMAIL_HOST_PASSWORD=xsmtpsib-a1b2c3d4e5f6g7h8-i9j0k1l2m3n4o5p6
BREVO_API_KEY=xkeysib-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6-q7r8s9t0u1v2w3x4
```

## Application Integration

### 1. Updated Files

The following files have been configured for Brevo:

- `server/settings.py` - Brevo SMTP configuration
- `deployment/production_settings.py` - Production Brevo settings
- `.env` - Brevo environment variables
- `.env.example` - Example Brevo configuration
- `polling/brevo_email_service.py` - Brevo email service
- `polling/otp_utils.py` - Updated to use Brevo

### 2. Email Service Usage

```python
from polling.brevo_email_service import BrevoEmailService

# Send OTP verification email
BrevoEmailService.send_otp_email(email, otp_code, "verification")

# Send password reset email
BrevoEmailService.send_password_reset_email(email, otp_code)

# Send welcome email
BrevoEmailService.send_welcome_email(email, username)

# Test connection
BrevoEmailService.test_brevo_connection()

# Get daily email count
count = BrevoEmailService.get_daily_email_count()
```

## Testing Configuration

### Run Test Script
```bash
python test_brevo_config.py
```

This will test:
- ✅ Brevo SMTP configuration
- ✅ Connection to Brevo servers
- ✅ Basic email sending
- ✅ OTP email functionality

### Manual Testing
```python
# Django shell
python manage.py shell

from polling.brevo_email_service import BrevoEmailService

# Test connection
BrevoEmailService.test_brevo_connection()

# Send test OTP
BrevoEmailService.send_otp_email("test@example.com", "123456", "verification")
```

## Brevo Limits and Features

### Free Plan Limits
- **Daily Emails**: 300 emails/day
- **Monthly Emails**: 9,000 emails/month
- **Contacts**: Unlimited
- **Templates**: Unlimited
- **Support**: Email support

### Paid Plans
- **Starter**: €25/month - 20,000 emails/month
- **Business**: €65/month - 60,000 emails/month
- **Enterprise**: Custom pricing

### Advanced Features
- **Email Templates**: Drag-and-drop editor
- **Automation**: Email workflows
- **Analytics**: Open rates, click rates, bounces
- **A/B Testing**: Subject line testing
- **Segmentation**: Contact lists
- **API Access**: REST API for advanced integration

## Email Templates

### OTP Verification Email
- Subject: "🔐 Email Verification Code - Color Prediction Game"
- Contains: 6-digit OTP code
- Expires: 10 minutes
- Security notice included

### Password Reset Email
- Subject: "🔑 Password Reset Code - Color Prediction Game"
- Contains: 6-digit reset code
- Expires: 10 minutes
- Security instructions

### Welcome Email
- Subject: "🎮 Welcome to Color Prediction Game!"
- Contains: Account confirmation
- Login instructions
- Feature overview

## Troubleshooting

### Common Issues

1. **Authentication Failed**
   - Verify SMTP key is correct
   - Check if account is verified
   - Ensure SMTP is enabled

2. **Emails Going to Spam**
   - Set up SPF, DKIM, DMARC records
   - Use verified domain
   - Avoid spam trigger words

3. **Daily Limit Exceeded**
   - Monitor daily usage
   - Upgrade to paid plan
   - Implement email queuing

4. **Domain Not Verified**
   - Add DNS records correctly
   - Wait for DNS propagation
   - Check domain status in Brevo

### Monitoring

```python
# Check daily email count
from polling.brevo_email_service import BrevoEmailService
count = BrevoEmailService.get_daily_email_count()
print(f"Emails sent today: {count}")
```

## Email Service Setup

1. **Configure environment variables**
2. **Update email service imports**
3. **Test with small volume**
4. **Monitor deliverability**
5. **Set up domain authentication**

## Security Best Practices

- **Rotate SMTP keys** regularly
- **Use environment variables** for credentials
- **Monitor email logs** for suspicious activity
- **Set up domain authentication** (SPF/DKIM/DMARC)
- **Implement rate limiting** to prevent abuse

## Support

- **Brevo Documentation**: [https://developers.brevo.com](https://developers.brevo.com)
- **SMTP Guide**: [https://help.brevo.com/hc/en-us/articles/209467485](https://help.brevo.com/hc/en-us/articles/209467485)
- **API Documentation**: [https://developers.brevo.com/docs](https://developers.brevo.com/docs)

Your Brevo email configuration is now ready for production use!
