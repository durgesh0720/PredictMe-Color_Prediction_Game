#!/usr/bin/env python
"""
Debug Payment Issue
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player
from polling.payment_service import PaymentService
from polling.payment_validation import PaymentValidationService
from polling.fraud_detection import FraudDetectionService

def test_payment_validation():
    """Test payment validation service"""
    print("🔍 Testing Payment Validation...")
    
    # Get or create test user
    try:
        player = Player.objects.get(username='durgesh1')
    except Player.DoesNotExist:
        print("❌ Player 'durgesh1' not found")
        return False
    
    print(f"✅ Found player: {player.username}")
    
    # Test validation
    amount = 100.0
    transaction_type = 'deposit'
    
    try:
        is_valid, validation_errors = PaymentValidationService.comprehensive_payment_validation(
            player, amount, transaction_type
        )
        
        print(f"📋 Validation result: {is_valid}")
        if not is_valid:
            print(f"❌ Validation errors: {validation_errors}")
        else:
            print("✅ Validation passed")
            
        return is_valid
        
    except Exception as e:
        print(f"❌ Validation error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fraud_detection():
    """Test fraud detection service"""
    print("\n🛡️ Testing Fraud Detection...")
    
    try:
        player = Player.objects.get(username='durgesh1')
        amount = 100.0
        
        risk_score, risk_factors = FraudDetectionService.calculate_fraud_score(
            player, amount, 'deposit', None
        )
        
        print(f"📊 Risk score: {risk_score}")
        print(f"📋 Risk factors: {risk_factors}")
        
        should_flag, flag_reason = FraudDetectionService.should_flag_transaction(
            risk_score, risk_factors
        )
        
        print(f"🚩 Should flag: {should_flag}")
        if should_flag:
            print(f"📝 Flag reason: {flag_reason}")
        
        return True
        
    except Exception as e:
        print(f"❌ Fraud detection error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_razorpay_config():
    """Test Razorpay configuration"""
    print("\n💳 Testing Razorpay Configuration...")
    
    try:
        from django.conf import settings
        import razorpay
        
        print(f"🔑 Razorpay Key ID: {settings.RAZORPAY_KEY_ID[:10]}...")
        print(f"🔐 Razorpay Secret: {'*' * 20}")
        
        # Test client creation
        razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
        print("✅ Razorpay client created successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Razorpay config error: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_create_order():
    """Test create order method directly"""
    print("\n📦 Testing Create Order Method...")
    
    try:
        player = Player.objects.get(username='durgesh1')
        amount = 100.0
        
        print(f"👤 Player: {player.username}")
        print(f"💰 Amount: ₹{amount}")
        
        result = PaymentService.create_order(
            player=player,
            amount=amount,
            currency='INR',
            description='Test deposit',
            request=None
        )
        
        print(f"📋 Result type: {type(result)}")
        print(f"📋 Result: {result}")
        
        if result is None:
            print("❌ Method returned None!")
            return False
        
        if isinstance(result, tuple) and len(result) == 3:
            success, order_or_error, order_data = result
            print(f"✅ Success: {success}")
            print(f"📄 Order/Error: {order_or_error}")
            print(f"📊 Order Data: {order_data}")
            return success
        else:
            print(f"❌ Unexpected result format: {result}")
            return False
        
    except Exception as e:
        print(f"❌ Create order error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all debug tests"""
    print("🚀 Starting Payment Debug Tests...\n")
    
    tests = [
        test_payment_validation,
        test_fraud_detection,
        test_razorpay_config,
        test_create_order
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
                print(f"✅ {test.__name__} PASSED\n")
            else:
                print(f"❌ {test.__name__} FAILED\n")
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}\n")
    
    print(f"📊 Debug Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All debug tests passed! Payment system should be working.")
    else:
        print(f"\n⚠️ {total - passed} tests failed. Check the issues above.")

if __name__ == '__main__':
    main()
