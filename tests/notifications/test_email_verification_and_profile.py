#!/usr/bin/env python
"""
Test script for email verification reminders and profile image functionality
"""

import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player
from polling.otp_utils import OTPService
from django.core.files.uploadedfile import SimpleUploadedFile
import tempfile
from PIL import Image
import io

def test_email_verification_system():
    """Test the email verification system"""
    print("🧪 Testing Email Verification System")
    print("=" * 50)
    
    # Create a test user
    test_email = "test_user@example.com"
    test_username = "testuser123"
    
    # Clean up any existing test user
    Player.objects.filter(email=test_email).delete()
    
    try:
        # Create unverified user
        player = Player(
            username=test_username,
            email=test_email,
            first_name="Test",
            last_name="User",
            balance=1000,
            email_verified=False,
            is_active=True
        )
        player.set_password("testpassword123")
        player.save()
        
        print(f"✅ Created test user: {player.username}")
        print(f"📧 Email: {player.email}")
        print(f"🔐 Email verified: {player.email_verified}")
        
        # Test OTP generation and sending
        print("\n📤 Testing OTP generation...")
        success, message, otp = OTPService.generate_and_send_otp(player.email, player.username)
        
        if success:
            print(f"✅ OTP generated successfully")
            print(f"🔑 OTP Code: {otp.otp_code}")
            print(f"⏰ Expires at: {otp.expires_at}")
            
            # Test OTP verification
            print("\n🔍 Testing OTP verification...")
            verify_success, verify_message = OTPService.verify_otp(player.email, otp.otp_code)
            
            if verify_success:
                print("✅ OTP verification successful")
                
                # Update user as verified
                player.email_verified = True
                player.save()
                print(f"✅ User marked as verified: {player.email_verified}")
            else:
                print(f"❌ OTP verification failed: {verify_message}")
        else:
            print(f"❌ OTP generation failed: {message}")
            
    except Exception as e:
        print(f"❌ Error in email verification test: {e}")
    
    return player

def test_profile_image_system(player):
    """Test the profile image system"""
    print("\n🖼️ Testing Profile Image System")
    print("=" * 50)
    
    try:
        # Create a test image
        print("🎨 Creating test image...")
        image = Image.new('RGB', (100, 100), color='blue')
        image_io = io.BytesIO()
        image.save(image_io, format='JPEG')
        image_io.seek(0)
        
        # Create uploaded file
        uploaded_file = SimpleUploadedFile(
            "test_avatar.jpg",
            image_io.getvalue(),
            content_type="image/jpeg"
        )
        
        print(f"📁 Test image created: {uploaded_file.name}")
        print(f"📏 File size: {uploaded_file.size} bytes")
        print(f"🏷️ Content type: {uploaded_file.content_type}")
        
        # Test avatar upload
        print("\n📤 Testing avatar upload...")
        player.avatar = uploaded_file
        player.save()
        
        print(f"✅ Avatar uploaded successfully")
        print(f"🔗 Avatar URL: {player.avatar.url if player.avatar else 'None'}")
        
        # Test avatar display properties
        if player.avatar:
            print(f"📂 Avatar path: {player.avatar.path}")
            print(f"📊 Avatar exists: {os.path.exists(player.avatar.path) if hasattr(player.avatar, 'path') else 'N/A'}")
        
        # Test default avatar fallback
        print("\n🔄 Testing default avatar fallback...")
        original_avatar = player.avatar
        player.avatar = None
        player.save()
        
        print(f"✅ Avatar removed, should show default: {player.username[0].upper()}")
        
        # Restore avatar
        player.avatar = original_avatar
        player.save()
        print("✅ Avatar restored")
        
    except Exception as e:
        print(f"❌ Error in profile image test: {e}")

def test_template_context():
    """Test template context and display logic"""
    print("\n🎭 Testing Template Context")
    print("=" * 50)
    
    try:
        # Test unverified user context
        unverified_user = Player.objects.filter(email_verified=False).first()
        if unverified_user:
            print(f"👤 Unverified user: {unverified_user.username}")
            print(f"📧 Email: {unverified_user.email}")
            print(f"🔐 Verified: {unverified_user.email_verified}")
            print(f"🖼️ Has avatar: {bool(unverified_user.avatar)}")
            print(f"🔤 Default avatar letter: {unverified_user.username[0].upper()}")
            print("✅ Should show email verification reminder")
        
        # Test verified user context
        verified_user = Player.objects.filter(email_verified=True).first()
        if verified_user:
            print(f"\n👤 Verified user: {verified_user.username}")
            print(f"📧 Email: {verified_user.email}")
            print(f"🔐 Verified: {verified_user.email_verified}")
            print(f"🖼️ Has avatar: {bool(verified_user.avatar)}")
            print("✅ Should NOT show email verification reminder")
            
    except Exception as e:
        print(f"❌ Error in template context test: {e}")

def cleanup_test_data():
    """Clean up test data"""
    print("\n🧹 Cleaning up test data...")
    try:
        # Remove test users
        deleted_count = Player.objects.filter(username__startswith="testuser").delete()[0]
        print(f"✅ Deleted {deleted_count} test users")
        
        # Clean up test images
        import glob
        test_images = glob.glob("media/avatars/test_avatar*")
        for img in test_images:
            try:
                os.remove(img)
                print(f"✅ Deleted test image: {img}")
            except:
                pass
                
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")

def main():
    """Run all tests"""
    print("🚀 Starting Email Verification and Profile Image Tests")
    print("=" * 60)
    
    try:
        # Test email verification
        player = test_email_verification_system()
        
        # Test profile images
        if player:
            test_profile_image_system(player)
        
        # Test template context
        test_template_context()
        
        print("\n" + "=" * 60)
        print("🎉 All tests completed!")
        print("💡 Check the Django admin or database to verify the results")
        print("🌐 Visit the application to see the UI changes in action")
        
    except Exception as e:
        print(f"💥 Test suite failed: {e}")
    finally:
        # Always cleanup
        cleanup_test_data()

if __name__ == "__main__":
    main()
