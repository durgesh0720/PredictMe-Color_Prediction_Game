# Responsible Gambling Configuration Guide

This guide explains how to configure responsible gambling limits through environment variables in your `.env` file.

## Overview

The responsible gambling system enforces betting limits to promote safe gambling practices. All limits can be configured through environment variables and are applied in real-time.

## Environment Variables

### Current Configuration

The following environment variables control responsible gambling limits:

| Variable | Description | Default Value | Current Value |
|----------|-------------|---------------|---------------|
| `RG_DAILY_LOSS_LIMIT` | Maximum daily loss amount (in paise) | 10000 (₹100) | **1000000 (₹10000)** |
| `RG_DAILY_BET_LIMIT` | Maximum daily betting amount (in paise) | 50000 (₹500) | **2000000 (₹20000)** |
| `RG_SESSION_LOSS_LIMIT` | Maximum session loss amount (in paise) | 5000 (₹50) | **500000 (₹5000)** |
| `RG_SESSION_TIME_LIMIT` | Maximum session duration (in seconds) | 7200 (2 hours) | 7200 (2 hours) |
| `RG_MAX_BET_AMOUNT` | Maximum single bet amount (in paise) | 2000 (₹20) | **500000 (₹5000)** |
| `RG_MIN_BET_AMOUNT` | Minimum single bet amount (in paise) | 100 (₹1) | **1000 (₹10)** |
| `RG_COOLING_OFF_PERIOD` | Cooling-off period duration (in seconds) | 86400 (24 hours) | 86400 (24 hours) |

### Currency Note
All monetary values are stored in **paise** (1 Rupee = 100 paise). This ensures precise calculations without floating-point errors.

## How to Increase Betting Limits

### Step 1: Edit the .env File

Open your `.env` file and modify the responsible gambling configuration section:

```bash
# Responsible Gambling Configuration
RG_DAILY_LOSS_LIMIT=1000000
RG_DAILY_BET_LIMIT=2000000
RG_SESSION_LOSS_LIMIT=500000
RG_SESSION_TIME_LIMIT=7200
RG_MAX_BET_AMOUNT=500000    # Currently set to ₹5000
RG_MIN_BET_AMOUNT=1000      # Currently set to ₹10
RG_COOLING_OFF_PERIOD=86400
```

### Step 2: Common Limit Increases

#### To increase maximum bet to ₹200:
```bash
RG_MAX_BET_AMOUNT=20000
```

#### To increase maximum bet to ₹500:
```bash
RG_MAX_BET_AMOUNT=50000
```

#### To increase maximum bet to ₹1000:
```bash
RG_MAX_BET_AMOUNT=100000
```

### Step 3: Restart the Server

After modifying the `.env` file, restart your Django server for changes to take effect:

```bash
# Stop the current server (Ctrl+C)
# Then restart:
python manage.py runserver
```

## Example Configurations

### Conservative (Default)
```bash
RG_MAX_BET_AMOUNT=2000      # ₹20 per bet
RG_DAILY_LOSS_LIMIT=10000   # ₹100 daily loss
RG_SESSION_LOSS_LIMIT=5000  # ₹50 session loss
```

### Moderate
```bash
RG_MAX_BET_AMOUNT=10000     # ₹100 per bet
RG_DAILY_LOSS_LIMIT=50000   # ₹500 daily loss
RG_SESSION_LOSS_LIMIT=25000 # ₹250 session loss
```

### Liberal
```bash
RG_MAX_BET_AMOUNT=50000     # ₹500 per bet
RG_DAILY_LOSS_LIMIT=100000  # ₹1000 daily loss
RG_SESSION_LOSS_LIMIT=50000 # ₹500 session loss
```

## Testing Configuration

Use the provided test script to verify your configuration:

```bash
python test_responsible_gambling_config.py
```

This will show:
- Current configuration values
- Bet validation tests
- Examples of how to modify limits

## Environment-Specific Configurations

### Development (.env.development)
Higher limits for testing:
```bash
RG_MAX_BET_AMOUNT=10000     # ₹100
RG_DAILY_LOSS_LIMIT=50000   # ₹500
```

### Testing (.env.testing)
Very high limits for automated testing:
```bash
RG_MAX_BET_AMOUNT=20000     # ₹200
RG_DAILY_LOSS_LIMIT=100000  # ₹1000
```

### Production (.env or production settings)
Conservative limits for real money:
```bash
RG_MAX_BET_AMOUNT=5000      # ₹50
RG_DAILY_LOSS_LIMIT=20000   # ₹200
```

## Important Notes

1. **Currency Format**: All amounts are in paise (1 ₹ = 100 paise)
2. **Server Restart Required**: Changes require server restart
3. **Player-Specific Limits**: Individual players can set lower limits via the API
4. **Validation**: The system validates all bets against these limits
5. **Logging**: All limit violations are logged for monitoring

## API Integration

The responsible gambling system integrates with:
- WebSocket betting validation
- REST API endpoints for limit management
- Admin panel for monitoring
- Player dashboard for self-imposed limits

## Troubleshooting

### Limits Not Applied
1. Check `.env` file syntax
2. Restart Django server
3. Verify environment variable loading in Django shell

### Testing Limits
```python
# Django shell
from django.conf import settings
print(f"Max bet: ₹{settings.RG_MAX_BET_AMOUNT/100:.2f}")

from polling.responsible_gambling import BettingLimits
limits = BettingLimits()
print(f"Loaded max bet: ₹{limits.max_bet_amount/100:.2f}")
```

## Security Considerations

- Limits should be set based on legal requirements
- Monitor for unusual betting patterns
- Implement proper logging and alerting
- Regular review of limit effectiveness
- Consider implementing progressive limits based on player behavior

---

**Last Updated**: Current configuration shows betting limits updated to:
- **Minimum bet**: ₹10.00 (increased from ₹1.00)
- **Maximum bet**: ₹5000.00 (increased from ₹20.00)
- **Daily betting limit**: ₹20,000.00
- **Daily loss limit**: ₹10,000.00
- **Session loss limit**: ₹5,000.00
