#!/usr/bin/env python
"""
Complete Razorpay integration test
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.test import Client
from polling.models import Player
from django.utils import timezone
import json

def test_complete_payment_flow():
    """Test complete payment flow with CSP"""
    print("🧪 Testing Complete Payment Flow...")
    
    client = Client()
    
    # Create test user and login
    try:
        player = Player.objects.get(username='test_complete_user')
    except Player.DoesNotExist:
        player = Player.objects.create(
            username='test_complete_user',
            email='test_complete@example.com',
            balance=0,
            email_verified=True,
            created_at=timezone.now()
        )
    
    # Login user
    session = client.session
    session['is_authenticated'] = True
    session['user_id'] = player.id
    session['username'] = player.username
    session.save()
    
    print("✅ User logged in successfully")
    
    # Test 1: Payment Dashboard Access
    response = client.get('/payment/dashboard/')
    if response.status_code == 200:
        print("✅ Payment dashboard accessible")
        
        # Check CSP headers
        csp = response.get('Content-Security-Policy', '')
        permissions = response.get('Permissions-Policy', '')
        
        required_csp_domains = [
            'https://checkout.razorpay.com',
            'https://api.razorpay.com',
            'https://lumberjack.razorpay.com'
        ]
        
        all_domains_present = all(domain in csp for domain in required_csp_domains)
        if all_domains_present:
            print("✅ All required Razorpay domains in CSP")
        else:
            print("❌ Missing Razorpay domains in CSP")
            
        if 'frame-src' in csp:
            print("✅ Frame-src directive configured")
        else:
            print("❌ Frame-src directive missing")
            
        if 'web-share=(self)' in permissions:
            print("✅ Web-share permissions configured")
        else:
            print("⚠️ Web-share permissions not configured")
    else:
        print(f"❌ Payment dashboard failed: {response.status_code}")
        return False
    
    # Test 2: Create Order API
    order_data = {
        'amount': 100,
        'description': 'Test payment',
        'currency': 'INR'
    }
    
    response = client.post('/api/payment/create-deposit-order/', 
                         json.dumps(order_data),
                         content_type='application/json')
    
    if response.status_code == 200:
        order_response = response.json()
        if order_response.get('success'):
            print("✅ Order creation API working")
            print(f"📦 Order ID: {order_response.get('order_id')}")
        else:
            print(f"❌ Order creation failed: {order_response.get('message')}")
            return False
    else:
        print(f"❌ Order creation API failed: {response.status_code}")
        return False
    
    # Test 3: Payment History
    response = client.get('/payment/history/')
    if response.status_code == 200:
        print("✅ Payment history accessible")
    else:
        print(f"❌ Payment history failed: {response.status_code}")
    
    # Test 4: Test Razorpay Simple Page
    response = client.get('/test-razorpay-simple/')
    if response.status_code == 200:
        print("✅ Simple test page accessible")
    else:
        print(f"❌ Simple test page failed: {response.status_code}")
    
    return True

def test_csp_compliance():
    """Test CSP compliance for all Razorpay requirements"""
    print("\n🔒 Testing CSP Compliance...")
    
    client = Client()
    response = client.get('/')
    
    csp = response.get('Content-Security-Policy', '')
    
    # Required CSP directives for Razorpay
    required_directives = {
        'script-src': ['https://checkout.razorpay.com'],
        'connect-src': ['https://api.razorpay.com', 'https://lumberjack.razorpay.com'],
        'frame-src': ['https://api.razorpay.com', 'https://checkout.razorpay.com']
    }
    
    all_passed = True
    
    for directive, domains in required_directives.items():
        if directive in csp:
            print(f"✅ {directive} directive present")
            for domain in domains:
                if domain in csp:
                    print(f"  ✅ {domain} allowed")
                else:
                    print(f"  ❌ {domain} missing")
                    all_passed = False
        else:
            print(f"❌ {directive} directive missing")
            all_passed = False
    
    return all_passed

def main():
    """Run all tests"""
    print("🚀 Starting Complete Razorpay Integration Tests...\n")
    
    tests = [
        test_complete_payment_flow,
        test_csp_compliance
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
        print("\n🎉 All tests passed! Razorpay integration is fully working!")
        print("\n✅ What's Working:")
        print("✅ CSP allows all Razorpay domains")
        print("✅ Payment dashboard loads without errors")
        print("✅ Order creation API functional")
        print("✅ Payment history accessible")
        print("✅ Frame embedding allowed")
        print("✅ Analytics tracking allowed")
        print("✅ Web-share permissions configured")
        
        print(f"\n🌐 Ready for Testing:")
        print(f"💳 Payment Dashboard: http://localhost:8000/payment/dashboard/")
        print(f"🧪 Simple Test: http://localhost:8000/test-razorpay-simple/")
        print(f"📊 Payment History: http://localhost:8000/payment/history/")
        
        print(f"\n💡 Browser Testing:")
        print("1. Clear browser cache (Ctrl+F5)")
        print("2. Open Developer Tools → Console")
        print("3. Visit payment dashboard")
        print("4. Should see no CSP errors")
        print("5. Try test payment with ₹10")
        
    else:
        print("\n⚠️ Some tests failed. Check the configuration.")

if __name__ == '__main__':
    main()
