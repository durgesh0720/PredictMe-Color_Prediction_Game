# Email System Tests

This directory contains tests for the email system functionality including SMTP configuration, email delivery, and template rendering.

## 🧪 Test Files

### Configuration Tests
- **[test_brevo_config.py](./test_brevo_config.py)** - Brevo SMTP configuration tests

### Email Delivery Tests
- **test_email_delivery.py** - Email sending and delivery tests
- **test_email_templates.py** - Email template rendering tests
- **test_otp_emails.py** - OTP email functionality tests

## 📧 Email Test Categories

### SMTP Configuration
- Connection testing
- Authentication validation
- TLS/SSL configuration
- Port and host verification

### Email Delivery
- OTP verification emails
- Password reset emails
- Welcome emails
- Notification emails

### Template Rendering
- HTML email templates
- Plain text fallbacks
- Dynamic content insertion
- Responsive design

### Error Handling
- SMTP connection failures
- Authentication errors
- Rate limiting
- Bounce handling

## 🔧 Running Email Tests

### Individual Test Files
```bash
# Test Brevo configuration
python tests/email/test_brevo_config.py

# Run all email tests
python -m pytest tests/email/ -v

# Test with email sending (use carefully)
python -m pytest tests/email/ -v --send-emails
```

### Test Configuration
```python
# Email test settings
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'  # For testing
TEST_EMAIL_RECIPIENT = 'test@example.com'

# Brevo test credentials (use test account)
BREVO_TEST_API_KEY = 'test-api-key'
BREVO_TEST_SMTP_KEY = 'test-smtp-key'
```

## 📊 Test Scenarios

### Connection Tests
```python
def test_brevo_connection():
    """Test Brevo SMTP connection"""
    from polling.brevo_email_service import BrevoEmailService
    
    result = BrevoEmailService.test_brevo_connection()
    assert result is True
```

### Email Sending Tests
```python
def test_otp_email_sending():
    """Test OTP email sending"""
    from polling.brevo_email_service import BrevoEmailService
    
    result = BrevoEmailService.send_otp_email(
        email='test@example.com',
        otp_code='123456',
        purpose='verification'
    )
    assert result is True
```

### Template Tests
```python
def test_email_template_rendering():
    """Test email template rendering"""
    from django.template.loader import render_to_string
    
    context = {
        'otp_code': '123456',
        'email': 'test@example.com',
        'expires_in': 10
    }
    
    html_content = render_to_string('emails/otp_verification.html', context)
    assert '123456' in html_content
    assert 'test@example.com' in html_content
```

## 🔍 Test Data

### Email Templates
- **OTP Verification**: `templates/emails/otp_verification.html`
- **Password Reset**: `templates/emails/password_reset_otp.html`
- **Welcome Email**: `templates/emails/welcome.html`

### Test Recipients
```python
TEST_EMAILS = {
    'valid': 'test@example.com',
    'invalid': 'invalid-email',
    'blocked': 'blocked@domain.com'
}
```

## 📈 Performance Testing

### Email Sending Performance
```python
def test_email_sending_performance():
    """Test email sending performance"""
    import time
    
    start_time = time.time()
    
    # Send test email
    result = send_test_email()
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Should send within 5 seconds
    assert duration < 5.0
    assert result is True
```

### Rate Limiting Tests
```python
def test_rate_limiting():
    """Test email rate limiting"""
    from polling.brevo_email_service import BrevoEmailService
    
    # Check daily limit
    count = BrevoEmailService.get_daily_email_count()
    assert count >= 0
    assert count <= 300  # Free plan limit
```

## 🚨 Security Tests

### Email Validation
- Valid email format testing
- Domain validation
- Spam prevention
- Rate limiting validation

### Content Security
- Template injection prevention
- XSS prevention in emails
- Content sanitization
- Attachment security

## 📋 Test Environment Setup

### Local Testing
```bash
# Set test environment variables
export EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
export BREVO_API_KEY='test-key'
export BREVO_SMTP_KEY='test-smtp-key'

# Run tests
python -m pytest tests/email/
```

### CI/CD Testing
```yaml
# GitHub Actions example
- name: Test Email System
  run: |
    export EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend'
    python -m pytest tests/email/ -v
```

## 📚 Related Documentation

- **[Email Documentation](../../docs/email/)** - Email system guides
- **[Brevo Setup Guide](../../docs/email/BREVO_SETUP_GUIDE.md)** - Brevo configuration
- **[System Documentation](../../docs/system/)** - System architecture
