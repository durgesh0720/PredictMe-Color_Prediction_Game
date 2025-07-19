# Notification System Documentation

## Overview

The notification system in the Color Prediction Game has been configured to use:

- **Email notifications**: Only for critical authentication events (OTP verification, password reset)
- **In-app notifications**: For all events (game results, wallet transactions, etc.)

This approach reduces email spam while ensuring users still receive important security-related emails.

## Email Notification Types

The following notification types will send emails:

| Notification Type | Description | Email | In-App |
|------------------|-------------|-------|--------|
| `email_verified` | When email is verified | ✅ | ✅ |
| `password_changed` | When password is changed | ✅ | ✅ |
| `security_alert` | Security-related alerts | ✅ | ✅ |
| `login_alert` | New device logins | ✅ | ✅ |

## In-App Only Notification Types

The following notification types will only send in-app notifications (no emails):

| Notification Type | Description | Email | In-App |
|------------------|-------------|-------|--------|
| `wallet_transaction` | Wallet deposits and withdrawals | ❌ | ✅ |
| `game_result` | Game results (wins/losses) | ❌ | ✅ |
| `big_win` | Significant wins | ❌ | ✅ |
| `account_activity` | Account-related activities | ❌ | ✅ |
| `profile_updated` | Profile updates | ❌ | ✅ |
| `low_balance` | Low wallet balance alerts | ❌ | ✅ |
| `payment_failed` | Failed payment attempts | ❌ | ✅ |
| `game_round_start` | New game round notifications | ❌ | ✅ |
| `system_announcement` | System announcements | ❌ | ✅ |
| `maintenance_notice` | Scheduled maintenance | ❌ | ✅ |
| `new_features` | New feature announcements | ❌ | ✅ |

## Email Service

A dedicated email service has been created for authentication-related emails:

```python
from polling.email_service import send_otp_email, send_password_reset_email, send_welcome_email

# Send OTP verification email
send_otp_email(email="user@example.com", otp_code="123456", purpose="verification")

# Send password reset email
send_password_reset_email(email="user@example.com", reset_token="abcdef123456")

# Send welcome email after registration
send_welcome_email(email="user@example.com", username="username")
```

## Notification Service

The notification service has been updated to respect these settings:

```python
from polling.notification_service import notify_wallet_transaction, notify_game_result

# Send wallet transaction notification (in-app only)
notify_wallet_transaction(user=player, transaction_type='deposit', amount=100, new_balance=500)

# Send game result notification (in-app only)
notify_game_result(user=player, game_round=game_round, bet_result='win', amount=50)
```

## Email Templates

New email templates have been created for authentication emails:

- `templates/emails/otp_verification.html` - OTP verification emails
- `templates/emails/password_reset_otp.html` - Password reset OTP emails
- `templates/emails/password_reset.html` - Password reset link emails
- `templates/emails/welcome.html` - Welcome emails after registration

## Configuration

The notification settings can be updated using the provided script:

```bash
python scripts/setup/update_notification_settings.py
```

This script:
1. Updates notification types to use email only for authentication events
2. Updates user preferences to match the new settings
3. Displays the current notification configuration

## Testing

A comprehensive test suite is available to verify the notification system:

```bash
python tests/notification/test_notification_email_settings.py
```

This test suite verifies:
1. Notification types are configured correctly
2. Wallet notifications don't send emails
3. Game result notifications don't send emails
4. OTP emails are sent correctly
5. Password reset emails are sent correctly

## User Preferences

Users can still customize their notification preferences through the notification settings page. However, email delivery is restricted to authentication-related notifications regardless of user preferences.

## Implementation Details

### Notification Delivery Logic

The notification delivery logic has been updated to only send emails for specific notification types:

```python
def deliver_notification(self, notification, preference):
    # Only send email for specific notification types
    email_notification_types = ['password_changed', 'security_alert', 'login_alert', 'email_verified']
    
    # Send email if enabled AND it's a critical notification type
    if (delivery_method in ['email', 'both'] and 
        preference.notification_type.email_enabled and
        preference.notification_type.name in email_notification_types):
        self.send_email_notification(notification)
    
    # Always send in-app notification if enabled
    if delivery_method in ['in_app', 'both'] and preference.notification_type.in_app_enabled:
        self.send_in_app_notification(notification)
```

### OTP Service

The OTP service has been updated to use the dedicated email service:

```python
def send_otp_email(email, otp_code, username=None):
    # Use the new email service for OTP emails
    from .email_service import send_otp_email
    
    success = send_otp_email(email, otp_code, "verification")
    
    if success:
        return True, "OTP email sent successfully"
    else:
        return False, "Failed to send OTP email"
```

## Benefits

1. **Reduced Email Spam**: Users only receive emails for critical authentication events
2. **Better User Experience**: In-app notifications for game events and transactions
3. **Improved Deliverability**: Critical emails are more likely to be delivered and read
4. **Simplified Email Templates**: Focused templates for authentication emails
5. **Consistent Notification System**: Clear separation between email and in-app notifications
