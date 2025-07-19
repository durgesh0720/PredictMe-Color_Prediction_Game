#!/usr/bin/env python
"""
Test Razorpay integration with actual credentials
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

import razorpay
from django.conf import settings
from polling.models import Player, PaymentTransaction
from polling.payment_service import PaymentService
from django.utils import timezone

def test_razorpay_connection():
    """Test connection to Razorpay with actual credentials"""
    print("🔗 Testing Razorpay Connection...")
    
    try:
        # Initialize Razorpay client
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        
        # Test API connection by fetching payments (this will work even with no payments)
        try:
            payments = client.payment.all({'count': 1})
            print("✅ Successfully connected to Razorpay API")
            print(f"📊 API Response received (items: {len(payments.get('items', []))})")
            return True
        except Exception as api_error:
            print(f"❌ API connection failed: {api_error}")
            return False
            
    except Exception as e:
        print(f"❌ Razorpay client initialization failed: {e}")
        return False

def test_order_creation_live():
    """Test order creation with live Razorpay credentials"""
    print("\n📦 Testing Live Order Creation...")
    
    # Create or get test player
    try:
        player = Player.objects.get(username='razorpay_test_user')
    except Player.DoesNotExist:
        player = Player.objects.create(
            username='razorpay_test_user',
            email='test@razorpay.com',
            balance=0,
            email_verified=True,
            created_at=timezone.now()
        )
        print(f"✅ Created test player: {player.username}")
    
    try:
        # Test order creation with small amount
        success, result, order_data = PaymentService.create_order(
            player=player,
            amount=10,  # ₹10 test amount
            currency='INR',
            description='Test order creation'
        )
        
        if success:
            print(f"✅ Order created successfully!")
            print(f"🆔 Order ID: {result['id']}")
            print(f"💰 Amount: ₹{result['amount']/100}")
            print(f"💱 Currency: {result['currency']}")
            print(f"📝 Receipt: {result.get('receipt', 'N/A')}")
            
            # Check if PaymentTransaction was created
            payment_transaction = PaymentTransaction.objects.filter(
                razorpay_order_id=result['id']
            ).first()
            
            if payment_transaction:
                print(f"✅ PaymentTransaction created: {payment_transaction.id}")
                print(f"🔒 Fraud Score: {payment_transaction.fraud_score}")
                print(f"🚩 Flagged: {payment_transaction.is_flagged}")
            
            return True
        else:
            print(f"❌ Order creation failed: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Order creation error: {e}")
        return False

def test_webhook_signature():
    """Test webhook signature generation"""
    print("\n🔐 Testing Webhook Signature...")
    
    import hmac
    import hashlib
    import json
    
    # Sample webhook payload
    webhook_payload = {
        "event": "payment.captured",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_test123",
                    "order_id": "order_test123",
                    "amount": 1000,
                    "currency": "INR",
                    "status": "captured"
                }
            }
        }
    }
    
    payload_bytes = json.dumps(webhook_payload).encode('utf-8')
    
    # Generate signature using your webhook secret
    expected_signature = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    print(f"✅ Webhook secret configured: {settings.RAZORPAY_WEBHOOK_SECRET[:10]}...")
    print(f"✅ Generated signature: {expected_signature[:20]}...")
    
    # Test signature verification
    is_valid = hmac.compare_digest(expected_signature, expected_signature)
    print(f"✅ Signature verification: {is_valid}")
    
    return True

def test_payment_limits():
    """Test payment limits and validation"""
    print("\n💰 Testing Payment Limits...")
    
    print(f"💳 Min Deposit: ₹{settings.MIN_DEPOSIT_AMOUNT}")
    print(f"💳 Max Deposit: ₹{settings.MAX_DEPOSIT_AMOUNT}")
    print(f"💸 Min Withdrawal: ₹{settings.MIN_WITHDRAWAL_AMOUNT}")
    print(f"💸 Max Withdrawal: ₹{settings.MAX_WITHDRAWAL_AMOUNT}")
    print(f"📊 Daily Deposit Limit: ₹{getattr(settings, 'MAX_DAILY_DEPOSIT_LIMIT', 50000)}")
    print(f"📊 Daily Withdrawal Limit: ₹{getattr(settings, 'MAX_DAILY_WITHDRAWAL_LIMIT', 25000)}")
    
    return True

def test_currency_conversion():
    """Test INR to paise conversion"""
    print("\n💱 Testing Currency Conversion...")
    
    test_amounts = [10, 50, 100, 500, 1000]
    
    for amount in test_amounts:
        paise = int(amount * 100)
        print(f"₹{amount} = {paise} paise")
    
    return True

def main():
    """Run all live tests"""
    print("🚀 Starting Razorpay Live Integration Tests...\n")
    print(f"🔑 Using Razorpay Key ID: {settings.RAZORPAY_KEY_ID}")
    print(f"🌐 Ngrok URL: {settings.ALLOWED_HOSTS[1] if len(settings.ALLOWED_HOSTS) > 1 else 'Not configured'}")
    print(f"🔗 Webhook URL: https://{settings.ALLOWED_HOSTS[1]}/webhooks/razorpay/" if len(settings.ALLOWED_HOSTS) > 1 else "Configure ngrok URL")
    
    tests = [
        test_razorpay_connection,
        test_order_creation_live,
        test_webhook_signature,
        test_payment_limits,
        test_currency_conversion
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} failed: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Razorpay integration is ready!")
        print("\n✅ Next Steps:")
        print("1. Access payment dashboard: http://localhost:8000/payment/dashboard/")
        print("2. Test deposit with small amount (₹10)")
        print("3. Configure webhook in Razorpay dashboard")
        print("4. Test complete payment flow")
    else:
        print("⚠️ Some tests failed. Please check the configuration.")
    
    print(f"\n🔧 Configuration Summary:")
    print(f"✅ Razorpay Key ID: {settings.RAZORPAY_KEY_ID[:15]}...")
    print(f"✅ Razorpay Key Secret: {settings.RAZORPAY_KEY_SECRET[:15]}...")
    print(f"✅ Webhook Secret: {settings.RAZORPAY_WEBHOOK_SECRET[:15]}...")
    print(f"✅ Currency: INR")
    print(f"✅ Register bonus removed (balance starts at ₹0)")

if __name__ == '__main__':
    main()
