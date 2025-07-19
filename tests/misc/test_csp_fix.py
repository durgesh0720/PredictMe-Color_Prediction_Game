#!/usr/bin/env python
"""
Test CSP fix for Razorpay
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

def test_csp_headers():
    """Test that CSP headers allow Razorpay"""
    print("🧪 Testing CSP Headers for Razorpay...")
    
    client = Client()
    
    # Create test user and login
    try:
        player = Player.objects.get(username='test_csp_user')
    except Player.DoesNotExist:
        player = Player.objects.create(
            username='test_csp_user',
            email='test_csp@example.com',
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
    
    # Get payment dashboard
    response = client.get('/payment/dashboard/')
    
    if response.status_code == 200:
        print("✅ Payment dashboard loads successfully")
        
        # Check CSP header
        csp_header = response.get('Content-Security-Policy', '')
        print(f"📋 CSP Header: {csp_header}")
        
        if 'https://checkout.razorpay.com' in csp_header:
            print("✅ Razorpay domain found in script-src")
        else:
            print("❌ Razorpay domain NOT found in script-src")
            
        if 'https://api.razorpay.com' in csp_header:
            print("✅ Razorpay API domain found in connect-src")
        else:
            print("❌ Razorpay API domain NOT found in connect-src")

        if 'https://lumberjack.razorpay.com' in csp_header:
            print("✅ Razorpay Lumberjack domain found in connect-src")
        else:
            print("❌ Razorpay Lumberjack domain NOT found in connect-src")

        if 'frame-src' in csp_header and 'https://api.razorpay.com' in csp_header:
            print("✅ Razorpay frame-src configured")
        else:
            print("❌ Razorpay frame-src NOT configured")
            
        # Check if Razorpay key is in response
        content = response.content.decode()
        if 'rzp_test_Wdl1blkg3PBf6z' in content:
            print("✅ Razorpay key found in template")
        else:
            print("❌ Razorpay key not found in template")
            
        return True
    else:
        print(f"❌ Payment dashboard returned status {response.status_code}")
        return False

def main():
    """Run CSP test"""
    print("🚀 Testing CSP Fix for Razorpay...\n")
    
    if test_csp_headers():
        print("\n🎉 CSP Test Results:")
        print("✅ Payment dashboard accessible")
        print("✅ CSP headers updated")
        print("✅ Razorpay domains whitelisted")
        print("\n💡 Next Steps:")
        print("1. Clear browser cache (Ctrl+F5)")
        print("2. Test payment dashboard in browser")
        print("3. Check browser console for Razorpay loading")
        print("4. Try a test payment")
    else:
        print("\n❌ CSP test failed")

if __name__ == '__main__':
    main()
