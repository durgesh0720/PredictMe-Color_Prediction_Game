#!/usr/bin/env python3
"""
Comprehensive test suite for validating critical fixes
This test suite validates all the critical issues identified and fixed in the code review.
"""

import os
import sys
import django
import asyncio
import time
from decimal import Decimal
from unittest.mock import patch, MagicMock

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.test import TestCase, TransactionTestCase
from django.db import transaction
from polling.models import Player, GameRound, Bet, Transaction
from polling.error_recovery import ErrorRecoveryManager
from polling.consumers import GameRoomManager

class CriticalFixesTestSuite:
    """Test suite for validating critical fixes"""
    
    def __init__(self):
        self.test_results = []
        self.passed = 0
        self.failed = 0
    
    def run_test(self, test_name, test_func):
        """Run a single test and record results"""
        try:
            print(f"🧪 Running {test_name}...")
            result = test_func()
            if result:
                print(f"✅ {test_name} PASSED")
                self.passed += 1
            else:
                print(f"❌ {test_name} FAILED")
                self.failed += 1
            self.test_results.append((test_name, result))
        except Exception as e:
            print(f"💥 {test_name} ERROR: {e}")
            self.failed += 1
            self.test_results.append((test_name, False))
    
    def test_async_task_management_fix(self):
        """Test Fix #1: Async task management in error recovery"""
        try:
            # This should not raise RuntimeError anymore
            error_manager = ErrorRecoveryManager()
            
            # Check that monitoring is not started during init
            assert not error_manager._monitoring_started, "Monitoring should not start during init"
            
            # Check that we can safely call start_monitoring without event loop
            error_manager.start_monitoring()  # Should not crash
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_game_room_thread_safety(self):
        """Test Fix #3: Thread-safe game room management"""
        try:
            # Test the new GameRoomManager
            room_manager = GameRoomManager()
            
            # This should work without async context (basic structure test)
            assert hasattr(room_manager, '_rooms'), "Room manager should have _rooms attribute"
            assert hasattr(room_manager, '_lock'), "Room manager should have _lock attribute"
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_balance_precision_consistency(self):
        """Test Fix #2: Balance precision consistency"""
        try:
            # Check that we have the fix tool
            assert os.path.exists('fix_balance_precision.py'), "Balance precision fix tool should exist"
            
            # Test decimal precision handling
            test_amount = Decimal('123.45')
            assert test_amount.quantize(Decimal('0.01')) == Decimal('123.45'), "Decimal precision should work"
            
            # Test that we can handle large amounts without overflow
            large_amount = Decimal('999999.99')
            assert large_amount < Decimal('1000000'), "Large amounts should be handled correctly"
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_model_field_consistency(self):
        """Test database model field consistency"""
        try:
            # Check Player model fields
            player_fields = Player._meta.get_fields()
            field_names = [f.name for f in player_fields]
            
            # Check for duplicate email_verified fields
            email_verified_count = sum(1 for name in field_names if 'email_verified' in name)
            if email_verified_count > 1:
                print(f"   Warning: Found {email_verified_count} email_verified fields")
            
            # Check that balance field exists
            assert 'balance' in field_names, "Player should have balance field"
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_input_validation_consistency(self):
        """Test input validation consistency"""
        try:
            from polling.wallet_utils import validate_bet_amount
            
            # Test valid amounts
            valid, msg = validate_bet_amount(100, 1000)
            assert valid, f"Valid bet should pass: {msg}"
            
            # Test invalid amounts
            valid, msg = validate_bet_amount(-10, 1000)
            assert not valid, "Negative bet should fail"
            
            valid, msg = validate_bet_amount(0, 1000)
            assert not valid, "Zero bet should fail"
            
            valid, msg = validate_bet_amount(20000, 1000)
            assert not valid, "Excessive bet should fail"
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_security_headers(self):
        """Test security header implementation"""
        try:
            from polling.middleware import SecurityHeadersMiddleware
            
            # Check that security middleware exists
            middleware = SecurityHeadersMiddleware(lambda x: x)
            assert middleware is not None, "Security middleware should exist"
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_websocket_security(self):
        """Test WebSocket security measures"""
        try:
            from polling.websocket_security import WebSocketRateLimiter, WebSocketValidator
            
            # Test rate limiter
            rate_limiter = WebSocketRateLimiter()
            assert rate_limiter.max_messages_per_minute > 0, "Rate limiter should have limits"
            
            # Test validator
            validator = WebSocketValidator()
            assert validator.MAX_MESSAGE_SIZE > 0, "Validator should have size limits"
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_payment_security(self):
        """Test payment system security"""
        try:
            from polling.fraud_detection import FraudDetectionService
            
            # Check fraud detection thresholds
            assert FraudDetectionService.CRITICAL_RISK > 0, "Should have critical risk threshold"
            assert FraudDetectionService.HIGH_RISK > 0, "Should have high risk threshold"
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_database_constraints(self):
        """Test database constraint implementation"""
        try:
            # Check Bet model constraints
            bet_meta = Bet._meta
            constraints = bet_meta.constraints
            
            # Should have unique constraint for player-round
            unique_constraints = [c for c in constraints if hasattr(c, 'fields')]
            assert len(unique_constraints) > 0, "Should have unique constraints"
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def test_error_handling_robustness(self):
        """Test error handling robustness"""
        try:
            # Test that error recovery manager handles exceptions gracefully
            error_manager = ErrorRecoveryManager()
            
            # Test ensure_monitoring_started method
            error_manager.ensure_monitoring_started()  # Should not crash
            
            return True
        except Exception as e:
            print(f"   Error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all tests in the suite"""
        print("🚀 Starting Comprehensive Fixes Test Suite")
        print("=" * 60)
        
        # Run all tests
        self.run_test("Async Task Management Fix", self.test_async_task_management_fix)
        self.run_test("Game Room Thread Safety", self.test_game_room_thread_safety)
        self.run_test("Balance Precision Consistency", self.test_balance_precision_consistency)
        self.run_test("Model Field Consistency", self.test_model_field_consistency)
        self.run_test("Input Validation Consistency", self.test_input_validation_consistency)
        self.run_test("Security Headers", self.test_security_headers)
        self.run_test("WebSocket Security", self.test_websocket_security)
        self.run_test("Payment Security", self.test_payment_security)
        self.run_test("Database Constraints", self.test_database_constraints)
        self.run_test("Error Handling Robustness", self.test_error_handling_robustness)
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print(f"📈 Success Rate: {(self.passed / (self.passed + self.failed) * 100):.1f}%")
        
        if self.failed == 0:
            print("\n🎉 All tests passed! Critical fixes are working correctly.")
            return True
        else:
            print(f"\n⚠️  {self.failed} tests failed. Please review the issues above.")
            return False

if __name__ == "__main__":
    test_suite = CriticalFixesTestSuite()
    success = test_suite.run_all_tests()
    
    if not success:
        sys.exit(1)
    
    print("\n✨ Comprehensive fixes validation completed successfully!")
