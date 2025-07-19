"""
Comprehensive authentication tests for the Color Prediction Game.
Tests user registration, login, logout, profile management, and OTP verification.
"""

import json
from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core import mail
from django.utils import timezone
from datetime import timedelta

from polling.models import Player, OTPVerification, NotificationType
from polling.security import PasswordSecurity, InputValidator
from tests.conftest import BaseTestCase, PlayerFactory
from tests.utils import TestClient, AssertionHelpers, setup_test_notification_types


class UserRegistrationTests(BaseTestCase):
    """Test user registration functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.registration_url = reverse('register')
        
        self.valid_registration_data = {
            'username': 'newuser',
            'email': 'newuser@gmail.com',
            'first_name': 'New',
            'last_name': 'User',
            'password': 'SecurePass123!',
            'confirm_password': 'SecurePass123!',
        }
    
    def test_registration_page_loads(self):
        """Test registration page loads correctly."""
        response = self.client.get(self.registration_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Create Account')
    
    def test_successful_registration(self):
        """Test successful user registration."""
        response = self.client.post(self.registration_url, self.valid_registration_data)
        
        # Should redirect after successful registration
        self.assertEqual(response.status_code, 302)
        
        # User should be created
        self.assertTrue(Player.objects.filter(username='newuser').exists())
        
        # User should not be verified initially
        player = Player.objects.get(username='newuser')
        self.assertFalse(player.email_verified)
    
    def test_registration_with_invalid_email_domain(self):
        """Test registration with invalid email domain."""
        invalid_data = self.valid_registration_data.copy()
        invalid_data['email'] = 'user@invalid-domain.com'
        
        response = self.client.post(self.registration_url, invalid_data)
        self.assertEqual(response.status_code, 200)  # Should stay on registration page
        self.assertContains(response, 'Only emails from')
    
    def test_registration_with_weak_password(self):
        """Test registration with weak password."""
        weak_data = self.valid_registration_data.copy()
        weak_data['password'] = '123'
        weak_data['confirm_password'] = '123'
        
        response = self.client.post(self.registration_url, weak_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Password must be')
    
    def test_registration_with_mismatched_passwords(self):
        """Test registration with mismatched passwords."""
        mismatch_data = self.valid_registration_data.copy()
        mismatch_data['confirm_password'] = 'DifferentPassword123!'
        
        response = self.client.post(self.registration_url, mismatch_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Passwords do not match')
    
    def test_registration_with_existing_username(self):
        """Test registration with existing username."""
        # Create existing user
        PlayerFactory(username='existinguser')
        
        duplicate_data = self.valid_registration_data.copy()
        duplicate_data['username'] = 'existinguser'
        
        response = self.client.post(self.registration_url, duplicate_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Username already exists')
    
    def test_registration_with_existing_email(self):
        """Test registration with existing email."""
        # Create existing user
        PlayerFactory(email='existing@gmail.com')
        
        duplicate_data = self.valid_registration_data.copy()
        duplicate_data['email'] = 'existing@gmail.com'
        
        response = self.client.post(self.registration_url, duplicate_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Email already registered')
    
    @patch('polling.otp_utils.OTPService.send_otp')
    def test_otp_sent_after_registration(self, mock_send_otp):
        """Test OTP is sent after successful registration."""
        mock_send_otp.return_value = (True, 'OTP sent successfully', '123456')
        
        response = self.client.post(self.registration_url, self.valid_registration_data)
        
        # Should redirect to OTP verification
        self.assertEqual(response.status_code, 302)
        mock_send_otp.assert_called_once()


class UserLoginTests(BaseTestCase):
    """Test user login functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.login_url = reverse('login')
        
        # Create verified user
        self.player = PlayerFactory(
            username='testuser',
            email='test@gmail.com',
            email_verified=True
        )
        self.player.set_password('TestPass123!')
    
    def test_login_page_loads(self):
        """Test login page loads correctly."""
        response = self.client.get(self.login_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sign In')
    
    def test_successful_login(self):
        """Test successful user login."""
        login_data = {
            'username': 'testuser',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, login_data)
        
        # Should redirect after successful login
        self.assertEqual(response.status_code, 302)
        
        # Session should be set
        self.assertTrue(self.client.session.get('is_authenticated'))
        self.assertEqual(self.client.session.get('username'), 'testuser')
    
    def test_login_with_invalid_credentials(self):
        """Test login with invalid credentials."""
        invalid_data = {
            'username': 'testuser',
            'password': 'WrongPassword'
        }
        
        response = self.client.post(self.login_url, invalid_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid username or password')
    
    def test_login_with_unverified_email(self):
        """Test login with unverified email."""
        # Create unverified user
        unverified_player = PlayerFactory(
            username='unverified',
            email_verified=False
        )
        unverified_player.set_password('TestPass123!')
        
        login_data = {
            'username': 'unverified',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, 302)  # Redirect to verification
    
    def test_login_with_inactive_user(self):
        """Test login with inactive user."""
        # Create inactive user
        inactive_player = PlayerFactory(
            username='inactive',
            is_active=False
        )
        inactive_player.set_password('TestPass123!')
        
        login_data = {
            'username': 'inactive',
            'password': 'TestPass123!'
        }
        
        response = self.client.post(self.login_url, login_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Account is deactivated')
    
    def test_login_rate_limiting(self):
        """Test login rate limiting after multiple failed attempts."""
        invalid_data = {
            'username': 'testuser',
            'password': 'WrongPassword'
        }
        
        # Make multiple failed login attempts
        for _ in range(6):  # Exceed rate limit
            response = self.client.post(self.login_url, invalid_data)
        
        # Should be rate limited
        self.assertContains(response, 'Too many failed login attempts')


class UserLogoutTests(BaseTestCase):
    """Test user logout functionality."""
    
    def setUp(self):
        super().setUp()
        self.client = TestClient()
        self.logout_url = reverse('logout')
        self.player = PlayerFactory()
    
    def test_logout_clears_session(self):
        """Test logout clears user session."""
        # Login user
        self.client.login_player(self.player)
        self.assertTrue(self.client.session.get('is_authenticated'))
        
        # Logout
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)
        
        # Session should be cleared
        self.assertFalse(self.client.session.get('is_authenticated'))
        self.assertIsNone(self.client.session.get('username'))
    
    def test_logout_without_login(self):
        """Test logout without being logged in."""
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, 302)  # Should redirect


class OTPVerificationTests(BaseTestCase):
    """Test OTP verification functionality."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.verify_url = reverse('verify_otp')
        self.resend_url = reverse('resend_otp')
        
        self.player = PlayerFactory(email_verified=False)
        
        # Create OTP
        self.otp = OTPVerification.objects.create(
            email=self.player.email,
            otp_code='123456',
            expires_at=timezone.now() + timedelta(minutes=10)
        )
        
        # Set session for pending verification
        session = self.client.session
        session['pending_verification_email'] = self.player.email
        session['pending_user_id'] = self.player.id
        session.save()
    
    def test_otp_verification_page_loads(self):
        """Test OTP verification page loads."""
        response = self.client.get(self.verify_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Verify')
    
    def test_successful_otp_verification(self):
        """Test successful OTP verification."""
        verification_data = {
            'otp': '123456'
        }
        
        response = self.client.post(self.verify_url, verification_data)
        self.assertEqual(response.status_code, 302)  # Redirect after success
        
        # Player should be verified
        self.player.refresh_from_db()
        self.assertTrue(self.player.email_verified)
        
        # OTP should be marked as used
        self.otp.refresh_from_db()
        self.assertTrue(self.otp.is_used)
    
    def test_invalid_otp_verification(self):
        """Test verification with invalid OTP."""
        verification_data = {
            'otp': '999999'
        }
        
        response = self.client.post(self.verify_url, verification_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid or expired verification code')
    
    def test_expired_otp_verification(self):
        """Test verification with expired OTP."""
        # Make OTP expired
        self.otp.expires_at = timezone.now() - timedelta(minutes=1)
        self.otp.save()
        
        verification_data = {
            'otp': '123456'
        }
        
        response = self.client.post(self.verify_url, verification_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Invalid or expired verification code')
    
    @patch('polling.otp_utils.OTPService.resend_otp')
    def test_otp_resend(self, mock_resend):
        """Test OTP resend functionality."""
        mock_resend.return_value = (True, 'OTP sent successfully', '654321')
        
        response = self.client.post(self.resend_url)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        mock_resend.assert_called_once()
    
    def test_otp_resend_rate_limiting(self):
        """Test OTP resend rate limiting."""
        # First resend should work
        with patch('polling.otp_utils.OTPService.resend_otp') as mock_resend:
            mock_resend.return_value = (True, 'OTP sent successfully', '654321')
            response1 = self.client.post(self.resend_url)
            data1 = json.loads(response1.content)
            self.assertTrue(data1['success'])
        
        # Immediate second resend should be rate limited
        response2 = self.client.post(self.resend_url)
        data2 = json.loads(response2.content)
        self.assertFalse(data2['success'])
        self.assertIn('wait', data2['message'].lower())


class UserProfileTests(BaseTestCase):
    """Test user profile management."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.profile_url = reverse('user_profile')
        self.edit_profile_url = reverse('edit_profile')
        self.change_password_url = reverse('change_password')
        
        self.player = PlayerFactory(email_verified=True)
        self.client.login_player(self.player)
    
    def test_profile_page_requires_authentication(self):
        """Test profile page requires authentication."""
        self.client.logout_player()
        response = self.client.get(self.profile_url)
        self.assert_redirects_to_login(response)
    
    def test_profile_page_loads_for_authenticated_user(self):
        """Test profile page loads for authenticated user."""
        response = self.client.get(self.profile_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.player.username)
    
    def test_edit_profile_success(self):
        """Test successful profile editing."""
        edit_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'phone_number': '+1234567890',
        }
        
        response = self.client.post(self.edit_profile_url, edit_data)
        self.assertEqual(response.status_code, 302)
        
        # Profile should be updated
        self.player.refresh_from_db()
        self.assertEqual(self.player.first_name, 'Updated')
        self.assertEqual(self.player.last_name, 'Name')
    
    def test_change_password_success(self):
        """Test successful password change."""
        self.player.set_password('OldPassword123!')
        
        password_data = {
            'current_password': 'OldPassword123!',
            'new_password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!',
        }
        
        response = self.client.post(self.change_password_url, password_data)
        self.assertEqual(response.status_code, 302)
        
        # Password should be changed
        self.player.refresh_from_db()
        self.assertTrue(self.player.check_password('NewPassword123!'))
    
    def test_change_password_with_wrong_current_password(self):
        """Test password change with wrong current password."""
        self.player.set_password('OldPassword123!')
        
        password_data = {
            'current_password': 'WrongPassword',
            'new_password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!',
        }
        
        response = self.client.post(self.change_password_url, password_data)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Current password is incorrect')


class SecurityValidationTests(TestCase):
    """Test security validation functions."""

    def test_password_strength_validation(self):
        """Test password strength validation."""
        # Test with actual validation logic
        from polling.security import PasswordSecurity

        # Valid password
        errors = PasswordSecurity.validate_password_strength('SecurePass123!')
        self.assertEqual(len(errors), 0)  # No errors means valid

        # Too short
        errors = PasswordSecurity.validate_password_strength('123')
        self.assertGreater(len(errors), 0)  # Should have errors

        # No uppercase
        errors = PasswordSecurity.validate_password_strength('lowercase123!')
        self.assertGreater(len(errors), 0)  # Should have errors

        # No special character
        errors = PasswordSecurity.validate_password_strength('NoSpecial123')
        self.assertGreater(len(errors), 0)  # Should have errors

    def test_username_validation(self):
        """Test username validation."""
        from polling.security import InputValidator

        # Valid username
        is_valid, result = InputValidator.validate_username('validuser')
        self.assertTrue(is_valid)

        # Too short
        is_valid, message = InputValidator.validate_username('ab')
        self.assertFalse(is_valid)

        # Invalid characters
        is_valid, message = InputValidator.validate_username('invalid@user')
        self.assertFalse(is_valid)

    def test_email_domain_validation(self):
        """Test email domain validation."""
        from polling.security import InputValidator

        # Valid domains
        is_valid, result = InputValidator.validate_email('test@gmail.com')
        self.assertTrue(is_valid)

        is_valid, result = InputValidator.validate_email('test@outlook.com')
        self.assertTrue(is_valid)

        is_valid, result = InputValidator.validate_email('test@yahoo.com')
        self.assertTrue(is_valid)

        # Invalid domain
        is_valid, message = InputValidator.validate_email('test@invalid.com')
        self.assertFalse(is_valid)
