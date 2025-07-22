# 🔔 Notification Signals System

## Overview

The notification signals system provides automatic, event-driven notifications throughout the Color Prediction Game. Using Django signals, notifications are sent automatically when specific events occur, ensuring users stay informed about all important activities.

## 🎯 Key Features

### ⚡ **Automatic Triggering**
- Notifications fire automatically on model changes
- No manual intervention required
- Consistent notification delivery
- Real-time event processing

### 🛡️ **Smart Rate Limiting**
- Prevents notification spam
- Configurable thresholds per notification type
- Cache-based cooldown periods
- User-specific rate limiting

### 🔍 **Intelligent Detection**
- Suspicious betting pattern detection
- Low balance monitoring
- Security threat identification
- Performance anomaly detection

### 📊 **Performance Optimized**
- Efficient signal processing
- Minimal database impact
- Background task integration
- Automatic cleanup

## 📡 Signal Types

### 1. **Transaction Signals**

**Trigger:** `post_save` on `Transaction` model

**Purpose:** Notify users of wallet activities

**Events:**
- Deposits and withdrawals
- Balance changes
- Payment processing
- Admin adjustments

**Rate Limiting:** 1 notification per transaction type per minute

```python
@receiver(post_save, sender=Transaction)
def handle_transaction_notification(sender, instance, created, **kwargs):
    # Automatically sends wallet transaction notifications
```

### 2. **Bet Monitoring Signals**

**Trigger:** `post_save` on `Bet` model

**Purpose:** Monitor betting patterns and send game results

**Events:**
- Bet creation (pattern detection)
- Bet result processing
- Win/loss notifications
- Suspicious activity detection

**Features:**
- Rapid betting detection (>10 bets in 5 minutes)
- Large bet alerts (>50% of balance)
- Pattern betting detection (>15 same color bets)
- Big win notifications (>₹500)

```python
@receiver(post_save, sender=Bet)
def handle_bet_creation_and_monitoring(sender, instance, created, **kwargs):
    # Monitors betting patterns and sends result notifications
```

### 3. **Account Activity Signals**

**Trigger:** `post_save` on `Player` model

**Purpose:** Track account changes and security events

**Events:**
- New account creation
- Email verification
- Profile updates
- Security changes

**Detection:**
- Field change comparison
- First-time verification
- Profile modification tracking

```python
@receiver(post_save, sender=Player)
def handle_player_account_changes(sender, instance, created, **kwargs):
    # Sends account activity notifications
```

### 4. **Security Monitoring Signals**

**Trigger:** `post_save` on `OTPVerification` model

**Purpose:** Security event notifications

**Events:**
- OTP generation
- Verification attempts
- Security alerts
- Suspicious login patterns

```python
@receiver(post_save, sender=OTPVerification)
def handle_otp_verification(sender, instance, created, **kwargs):
    # Sends security notifications for OTP events
```

### 5. **Game Round Signals**

**Trigger:** `post_save` on `GameRound` model

**Purpose:** Game completion notifications

**Events:**
- Round completion
- Result announcements
- Batch player notifications
- Performance tracking

```python
@receiver(post_save, sender=GameRound)
def handle_game_round_completion(sender, instance, created, **kwargs):
    # Sends notifications when game rounds complete
```

## 🔧 Configuration

### Rate Limiting Thresholds

```python
# Email rate limits
EMAIL_RATE_LIMIT = 10  # per hour per user

# Suspicious betting thresholds
RAPID_BETTING_THRESHOLD = 10  # bets in 5 minutes
LARGE_BET_THRESHOLD = 0.5     # 50% of balance
PATTERN_BETTING_THRESHOLD = 15 # same color in 1 hour

# Balance thresholds
LOW_BALANCE_THRESHOLD = 100   # ₹100
BIG_WIN_THRESHOLD = 500       # ₹500
```

### Cache Keys

```python
# Rate limiting
f"email_notification_{user_id}"
f"rapid_betting_alert_{player_id}"
f"large_bet_alert_{player_id}"
f"pattern_betting_alert_{player_id}"

# Notification tracking
f"bet_notification_sent_{bet_id}"
f"round_completed_{round_id}"
f"email_verified_{player_id}"
```

## 🚀 Advanced Features

### 1. **Suspicious Pattern Detection**

Automatically detects and alerts on:
- **Rapid Betting:** >10 bets in 5 minutes
- **Large Bets:** >50% of user balance
- **Pattern Betting:** >15 consecutive same-color bets
- **Unusual Activity:** Deviations from normal patterns

### 2. **Login Monitoring**

Tracks and alerts on:
- **New Device Logins:** Different IP addresses
- **Failed Attempts:** Multiple failed login attempts
- **Suspicious Locations:** Unusual geographic patterns
- **Session Anomalies:** Abnormal session behavior

### 3. **Balance Monitoring**

Automatically monitors:
- **Low Balance:** Alerts when balance drops below threshold
- **Big Wins:** Celebrates significant wins
- **Transaction Patterns:** Unusual deposit/withdrawal patterns
- **Balance Changes:** Tracks all balance modifications

### 4. **Performance Optimization**

- **Batch Processing:** Groups related notifications
- **Cache Utilization:** Reduces database queries
- **Background Tasks:** Offloads heavy processing
- **Cleanup Automation:** Removes old notifications

## 📋 Management Commands

### Send Bulk Notifications

```bash
# Send maintenance notification
python manage.py send_notifications \
    --type maintenance \
    --title "Scheduled Maintenance" \
    --message "System will be down for 2 hours" \
    --priority high \
    --verified-only

# Send promotional announcement
python manage.py send_notifications \
    --type announcement \
    --title "New Feature Available" \
    --message "Check out our new color option!" \
    --priority normal
```

### Background Tasks

```bash
# Run scheduled tasks manually
python manage.py shell -c "from polling.tasks import run_scheduled_tasks; run_scheduled_tasks()"

# Clean up old notifications
python manage.py shell -c "from polling.tasks import cleanup_old_notifications; cleanup_old_notifications()"
```

## 🔍 Monitoring & Debugging

### Signal Performance

```python
# Check signal execution time
import time
start_time = time.time()
# ... signal execution ...
duration = time.time() - start_time
logger.info(f"Signal executed in {duration:.3f} seconds")
```

### Notification Tracking

```python
# Check notification delivery status
notifications = Notification.objects.filter(
    user=user,
    created_at__gte=timezone.now() - timedelta(hours=1)
)

for notification in notifications:
    print(f"{notification.title}: {notification.status}")
    print(f"Email sent: {notification.email_sent}")
    print(f"In-app delivered: {notification.in_app_delivered}")
```

### Error Handling

All signals include comprehensive error handling:

```python
try:
    # Signal logic
    notify_user(...)
except Exception as e:
    logger.error(f"Signal error: {e}")
    # Continue execution without breaking the request
```

## 🎛️ Customization

### Adding New Signals

1. **Create Signal Function:**
```python
@receiver(post_save, sender=YourModel)
def handle_your_event(sender, instance, created, **kwargs):
    try:
        # Your notification logic
        notify_user(...)
    except Exception as e:
        logger.error(f"Error in your signal: {e}")
```

2. **Register in apps.py:**
```python
def ready(self):
    import polling.signals
```

3. **Add Rate Limiting:**
```python
cache_key = f"your_notification_{user_id}"
if not cache.get(cache_key):
    # Send notification
    cache.set(cache_key, True, 3600)  # 1 hour cooldown
```

### Configuring Thresholds

Adjust detection thresholds in `signals.py`:

```python
# Modify these values as needed
RAPID_BETTING_THRESHOLD = 15  # Increase for less sensitive detection
LOW_BALANCE_THRESHOLD = 50    # Decrease for earlier warnings
BIG_WIN_THRESHOLD = 1000      # Increase for higher celebration threshold
```

## 📊 Analytics

### Signal Effectiveness

Track signal performance:

```python
# Notification delivery rates
total_sent = Notification.objects.filter(status='sent').count()
total_delivered = Notification.objects.filter(in_app_delivered=True).count()
delivery_rate = (total_delivered / total_sent) * 100

# User engagement
read_notifications = Notification.objects.filter(read_at__isnull=False).count()
engagement_rate = (read_notifications / total_delivered) * 100
```

### Performance Metrics

Monitor signal impact:

```python
# Signal execution frequency
signal_executions = cache.get('signal_executions', 0)
cache.set('signal_executions', signal_executions + 1, 3600)

# Database impact
query_count_before = len(connection.queries)
# ... signal execution ...
query_count_after = len(connection.queries)
queries_used = query_count_after - query_count_before
```

## 🔮 Future Enhancements

### Planned Features

1. **Machine Learning Integration**
   - Predictive notification timing
   - User behavior analysis
   - Personalized notification frequency

2. **Advanced Analytics**
   - Notification effectiveness scoring
   - A/B testing for notification content
   - User engagement optimization

3. **Multi-Channel Expansion**
   - SMS notifications
   - Push notifications
   - Social media integration

4. **Smart Scheduling**
   - Optimal delivery time detection
   - Time zone awareness
   - User preference learning

## 🎉 Conclusion

The notification signals system provides a robust, automatic, and intelligent notification framework that enhances user engagement while maintaining system performance. With comprehensive monitoring, smart rate limiting, and extensive customization options, it ensures users stay informed about all important activities in the Color Prediction Game.

The system is production-ready and scales efficiently with your user base, providing a professional notification experience that keeps players engaged and informed! 🚀
