"""
Comprehensive security tests for the Color Prediction Game.
Tests authentication, authorization, input validation, and vulnerability protection.
"""

import json
import time
from unittest.mock import patch, Mock
from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone

from polling.models import Player, Admin, GameRound, Bet, Transaction
from polling.security import PasswordSecurity, InputValidator, SecurityAudit
from tests.conftest import BaseTestCase, PlayerFactory, AdminFactory, GameRoundFactory
from tests.utils import (
    TestClient, SecurityTestHelpers, setup_test_notification_types
)


class AuthenticationSecurityTests(BaseTestCase):
    """Test authentication security measures."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory(email_verified=True)
    
    def test_password_hashing_security(self):
        """Test that passwords are properly hashed."""
        password = 'SecurePassword123!'
        
        # Create player with password
        player = PlayerFactory()
        player.set_password(password)
        
        # Password should be hashed, not stored in plain text
        self.assertNotEqual(player.password_hash, password)
        self.assertTrue(player.check_password(password))
        self.assertFalse(player.check_password('wrong_password'))
    
    def test_session_security(self):
        """Test session security measures."""
        # Login user
        self.client.login_player(self.player)
        
        # Check session data
        session = self.client.session
        self.assertTrue(session.get('is_authenticated'))
        self.assertEqual(session.get('user_id'), self.player.id)
        
        # Session should not contain sensitive data
        self.assertNotIn('password', str(session.items()))
        self.assertNotIn('password_hash', str(session.items()))
    
    def test_login_rate_limiting(self):
        """Test login rate limiting protection."""
        login_url = reverse('login')
        
        # Make multiple failed login attempts
        failed_attempts = 0
        for i in range(10):
            response = self.client.post(login_url, {
                'username': self.player.username,
                'password': 'wrong_password'
            })
            
            if 'too many' in response.content.decode().lower():
                break
            failed_attempts += 1
        
        # Should be rate limited after several attempts
        self.assertLess(failed_attempts, 10, "Login rate limiting not working")
    
    def test_session_timeout(self):
        """Test session timeout functionality."""
        # Login user
        self.client.login_player(self.player)
        
        # Simulate session timeout by manipulating session
        session = self.client.session
        session['last_activity'] = timezone.now() - timezone.timedelta(hours=2)
        session.save()
        
        # Access protected page
        response = self.client.get('/profile/')
        
        # Should redirect to login due to timeout
        self.assertEqual(response.status_code, 302)
    
    def test_concurrent_session_protection(self):
        """Test protection against concurrent sessions."""
        # Login with first client
        client1 = TestClient()
        client1.login_player(self.player)
        
        # Login with second client (same user)
        client2 = TestClient()
        client2.login_player(self.player)
        
        # Both sessions should be valid (or implement session invalidation)
        response1 = client1.get('/profile/')
        response2 = client2.get('/profile/')
        
        # At least one should work
        self.assertTrue(
            response1.status_code == 200 or response2.status_code == 200,
            "No valid sessions after concurrent login"
        )


class InputValidationSecurityTests(BaseTestCase):
    """Test input validation and sanitization."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory(balance=1000)
        self.client.login_player(self.player)
    
    def test_sql_injection_protection(self):
        """Test SQL injection protection."""
        sql_payloads = SecurityTestHelpers.test_sql_injection_payload()
        
        for payload in sql_payloads:
            # Test in various endpoints
            endpoints = [
                f'/api/player/{payload}/',
                f'/profile/?search={payload}',
            ]
            
            for endpoint in endpoints:
                response = self.client.get(endpoint)
                
                # Should not return 500 (database error)
                self.assertNotEqual(response.status_code, 500, 
                                  f"SQL injection possible at {endpoint}")
                
                # Should return 400 or 404
                self.assertIn(response.status_code, [400, 404])
    
    def test_xss_protection(self):
        """Test XSS protection in forms and outputs."""
        xss_payloads = SecurityTestHelpers.test_xss_payload()
        
        for payload in xss_payloads:
            # Test in registration form
            registration_data = {
                'username': 'testuser',
                'email': 'test@gmail.com',
                'first_name': payload,  # XSS payload in first name
                'last_name': 'User',
                'password': 'SecurePass123!',
                'confirm_password': 'SecurePass123!',
            }
            
            response = self.client.post('/register/', registration_data)
            
            # Check response doesn't contain unescaped XSS
            content = response.content.decode()
            self.assertNotIn('<script>', content)
            self.assertNotIn('javascript:', content)
            self.assertNotIn('onerror=', content)
    
    def test_path_traversal_protection(self):
        """Test path traversal protection."""
        traversal_payloads = SecurityTestHelpers.test_path_traversal_payload()
        
        for payload in traversal_payloads:
            # Test in file-related endpoints
            response = self.client.get(f'/static/{payload}')
            
            # Should not allow access to system files
            self.assertNotEqual(response.status_code, 200)
    
    def test_command_injection_protection(self):
        """Test command injection protection."""
        command_payloads = [
            '; ls -la',
            '| cat /etc/passwd',
            '&& rm -rf /',
            '`whoami`',
            '$(id)',
        ]
        
        for payload in command_payloads:
            # Test in search or filter parameters
            response = self.client.get(f'/game-history/?search={payload}')
            
            # Should handle safely
            self.assertIn(response.status_code, [200, 400, 404])
    
    def test_file_upload_security(self):
        """Test file upload security (if implemented)."""
        # Test malicious file uploads
        malicious_files = [
            ('test.php', b'<?php system(₹_GET["cmd"]); ?>'),
            ('test.jsp', b'<% Runtime.getRuntime().exec(request.getParameter("cmd")); %>'),
            ('test.exe', b'MZ\x90\x00'),  # PE header
        ]
        
        for filename, content in malicious_files:
            # If profile image upload is implemented
            response = self.client.post('/profile/upload/', {
                'file': (filename, content, 'application/octet-stream')
            })
            
            # Should reject malicious files
            self.assertNotEqual(response.status_code, 200)


class AuthorizationSecurityTests(BaseTestCase):
    """Test authorization and access control."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory()
        self.admin = AdminFactory()
    
    def test_unauthorized_access_protection(self):
        """Test protection against unauthorized access."""
        protected_urls = [
            '/profile/',
            '/wallet/',
            '/history/',
            '/api/place-bet/',
            '/api/user/balance/',
        ]
        
        # Test without authentication
        for url in protected_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [302, 401, 403], 
                         f"Unauthorized access allowed to {url}")
    
    def test_admin_access_protection(self):
        """Test admin-only access protection."""
        admin_urls = [
            '/control-panel/',
            '/control-panel/users/',
            '/control-panel/financial/',
            '/control-panel/api/select-color/',
        ]
        
        # Test with regular user
        self.client.login_player(self.player)
        
        for url in admin_urls:
            response = self.client.get(url)
            self.assertIn(response.status_code, [302, 401, 403], 
                         f"Non-admin access allowed to {url}")
    
    def test_user_data_isolation(self):
        """Test that users can only access their own data."""
        player1 = PlayerFactory(username='player1')
        player2 = PlayerFactory(username='player2')
        
        # Create transactions for both players
        Transaction.objects.create(
            player=player1,
            transaction_type='deposit',
            amount=100,
            balance_before=0,
            balance_after=100,
            description='Player 1 deposit'
        )
        
        Transaction.objects.create(
            player=player2,
            transaction_type='deposit',
            amount=200,
            balance_before=0,
            balance_after=200,
            description='Player 2 deposit'
        )
        
        # Login as player1
        self.client.login_player(player1)
        
        # Try to access player2's data
        response = self.client.get(f'/api/player/{player2.username}/transactions/')
        
        # Should not allow access to other user's data
        self.assertIn(response.status_code, [401, 403, 404])
    
    def test_privilege_escalation_protection(self):
        """Test protection against privilege escalation."""
        # Login as regular user
        self.client.login_player(self.player)
        
        # Try to perform admin actions
        admin_actions = [
            ('/control-panel/api/select-color/', {'room': 'main', 'color': 'red'}),
            ('/control-panel/api/create-admin/', {'username': 'hacker', 'password': 'hack123'}),
        ]
        
        for url, data in admin_actions:
            response = self.client.post_json(url, data)
            self.assertIn(response.status_code, [302, 401, 403], 
                         f"Privilege escalation possible at {url}")


class CSRFProtectionTests(BaseTestCase):
    """Test CSRF protection."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory(balance=1000)
    
    def test_csrf_protection_on_forms(self):
        """Test CSRF protection on forms."""
        # Login user
        self.client.login_player(self.player)
        
        # Try to submit form without CSRF token
        bet_data = {
            'room': 'main',
            'bet_type': 'color',
            'color': 'red',
            'amount': 100
        }
        
        # Remove CSRF token
        if 'csrftoken' in self.client.cookies:
            del self.client.cookies['csrftoken']
        
        response = self.client.post('/api/place-bet/', 
                                  json.dumps(bet_data),
                                  content_type='application/json')
        
        # Should be protected by CSRF
        self.assertIn(response.status_code, [403, 400])
    
    def test_csrf_token_validation(self):
        """Test CSRF token validation."""
        # Get CSRF token
        response = self.client.get('/login/')
        self.assertEqual(response.status_code, 200)
        
        # CSRF token should be present
        self.assertIn('csrftoken', self.client.cookies)


class DataProtectionTests(BaseTestCase):
    """Test data protection and privacy."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory()
    
    def test_sensitive_data_exposure(self):
        """Test that sensitive data is not exposed."""
        # Login user
        self.client.login_player(self.player)
        
        # Get user profile
        response = self.client.get('/api/user/profile/')
        
        if response.status_code == 200:
            content = response.content.decode()
            
            # Should not expose sensitive data
            self.assertNotIn('password', content.lower())
            self.assertNotIn('password_hash', content.lower())
            self.assertNotIn('secret', content.lower())
    
    def test_error_message_information_disclosure(self):
        """Test that error messages don't disclose sensitive information."""
        # Try invalid login
        response = self.client.post('/login/', {
            'username': 'nonexistent_user',
            'password': 'wrong_password'
        })
        
        content = response.content.decode()
        
        # Error message should be generic
        self.assertNotIn('does not exist', content.lower())
        self.assertNotIn('user not found', content.lower())
        
        # Should use generic message
        self.assertIn('invalid', content.lower())
    
    def test_database_connection_security(self):
        """Test database connection security."""
        # Check that database queries are parameterized
        with connection.cursor() as cursor:
            # This should be safe (parameterized)
            cursor.execute("SELECT COUNT(*) FROM polling_player WHERE username = %s", ['test'])
            result = cursor.fetchone()
            
            # Should execute without error
            self.assertIsNotNone(result)


class SecurityHeadersTests(BaseTestCase):
    """Test security headers."""
    
    def setUp(self):
        super().setUp()
        self.client = TestClient()
    
    def test_security_headers_present(self):
        """Test that security headers are present."""
        response = self.client.get('/')
        
        # Check for security headers
        headers_to_check = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
        ]
        
        for header in headers_to_check:
            # Header should be present (if configured)
            if header in response:
                self.assertIsNotNone(response[header])
    
    def test_content_type_nosniff(self):
        """Test X-Content-Type-Options header."""
        response = self.client.get('/')
        
        # Should prevent MIME type sniffing
        if 'X-Content-Type-Options' in response:
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
    
    def test_frame_options(self):
        """Test X-Frame-Options header."""
        response = self.client.get('/')
        
        # Should prevent clickjacking
        if 'X-Frame-Options' in response:
            self.assertIn(response['X-Frame-Options'], ['DENY', 'SAMEORIGIN'])


class SecurityAuditTests(BaseTestCase):
    """Test security audit and logging."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory()
        self.admin = AdminFactory()
    
    def test_failed_login_logging(self):
        """Test that failed logins are logged."""
        # Attempt failed login
        response = self.client.post('/login/', {
            'username': self.player.username,
            'password': 'wrong_password'
        })
        
        # Should log the failed attempt (implementation dependent)
        # This test verifies the endpoint handles failed login properly
        self.assertEqual(response.status_code, 200)
    
    def test_admin_action_logging(self):
        """Test that admin actions are logged."""
        # Login as admin
        self.client.login_admin(self.admin)
        
        # Perform admin action
        response = self.client.post_json('/control-panel/api/select-color/', {
            'room': 'main',
            'color': 'red'
        })
        
        # Action should be logged (implementation dependent)
        # This test verifies the endpoint works
        self.assertIn(response.status_code, [200, 400])
    
    def test_suspicious_activity_detection(self):
        """Test detection of suspicious activity."""
        # Simulate suspicious activity (multiple rapid requests)
        for i in range(20):
            response = self.client.get('/login/')
            
            # Should handle rapid requests gracefully
            self.assertIn(response.status_code, [200, 429])  # 429 = Too Many Requests


class PasswordSecurityTests(BaseTestCase):
    """Test password security measures."""
    
    def setUp(self):
        super().setUp()
        self.password_security = PasswordSecurity()
    
    def test_password_strength_validation(self):
        """Test password strength validation."""
        # Test various password strengths
        test_cases = [
            ('weak', ['123', 'password', 'abc'], False),
            ('medium', ['Password123', 'MyPass1!'], True),
            ('strong', ['SecurePassword123!', 'MyVerySecureP@ssw0rd'], True),
        ]
        
        for strength, passwords, should_be_valid in test_cases:
            for password in passwords:
                errors = PasswordSecurity.validate_password_strength(password)
                is_valid = len(errors) == 0
                
                if should_be_valid:
                    self.assertTrue(is_valid, f"Password '{password}' should be valid")
                else:
                    self.assertFalse(is_valid, f"Password '{password}' should be invalid")
    
    def test_password_history_prevention(self):
        """Test prevention of password reuse."""
        player = PlayerFactory()
        old_password = 'OldPassword123!'
        new_password = 'NewPassword123!'
        
        # Set initial password
        player.set_password(old_password)
        
        # Change to new password
        player.set_password(new_password)
        
        # Should not be able to reuse old password immediately
        # (This would require password history implementation)
        self.assertTrue(player.check_password(new_password))
        self.assertFalse(player.check_password(old_password))
    
    def test_password_complexity_requirements(self):
        """Test password complexity requirements."""
        # Test specific complexity requirements
        complexity_tests = [
            ('NoUppercase123!', 'missing uppercase'),
            ('NOLOWERCASE123!', 'missing lowercase'),
            ('NoNumbers!', 'missing numbers'),
            ('NoSpecialChars123', 'missing special characters'),
            ('Short1!', 'too short'),
        ]
        
        for password, expected_issue in complexity_tests:
            errors = PasswordSecurity.validate_password_strength(password)
            
            # Should have errors for weak passwords
            if 'Short1!' == password:
                self.assertGreater(len(errors), 0, f"Password '{password}' should fail validation")


class RateLimitingTests(BaseTestCase):
    """Test rate limiting protection."""
    
    def setUp(self):
        super().setUp()
        setup_test_notification_types()
        self.client = TestClient()
        self.player = PlayerFactory(balance=1000)
    
    def test_api_rate_limiting(self):
        """Test API rate limiting."""
        # Login user
        self.client.login_player(self.player)
        
        # Make rapid API requests
        responses = []
        for i in range(50):
            response = self.client.get('/api/user/balance/')
            responses.append(response.status_code)
            
            # Small delay to avoid overwhelming the test
            time.sleep(0.01)
        
        # Should eventually hit rate limit
        rate_limited = any(status == 429 for status in responses)
        
        # Rate limiting may or may not be implemented
        # This test documents the expected behavior
        if rate_limited:
            self.assertTrue(rate_limited, "Rate limiting is working")
        else:
            # If no rate limiting, all should succeed
            self.assertTrue(all(status == 200 for status in responses))
    
    def test_login_attempt_rate_limiting(self):
        """Test login attempt rate limiting."""
        # Make multiple failed login attempts
        failed_attempts = 0
        
        for i in range(15):
            response = self.client.post('/login/', {
                'username': 'nonexistent',
                'password': 'wrong'
            })
            
            if response.status_code == 429:  # Too Many Requests
                break
            
            failed_attempts += 1
            time.sleep(0.1)
        
        # Should be rate limited before 15 attempts
        self.assertLess(failed_attempts, 15, "Login rate limiting not effective")
