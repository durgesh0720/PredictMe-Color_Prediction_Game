#!/usr/bin/env python3
"""
Test script to validate the round_id validation fix
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.websocket_security import WebSocketValidator

def test_round_id_validation():
    """Test round_id validation with different data types"""
    
    print("🧪 Testing Round ID Validation Fix")
    print("=" * 50)
    
    # Test cases
    test_cases = [
        # (test_data, expected_result, description)
        (
            {'type': 'place_bet', 'color': 'red', 'amount': 10, 'round_id': '123'},
            True,
            "String round_id (should pass)"
        ),
        (
            {'type': 'place_bet', 'color': 'red', 'amount': 10, 'round_id': 123},
            True,
            "Integer round_id (should pass after conversion)"
        ),
        (
            {'type': 'place_bet', 'color': 'red', 'amount': 10, 'round_id': None},
            False,
            "None round_id (should fail)"
        ),
        (
            {'type': 'place_bet', 'color': 'red', 'amount': 10, 'round_id': []},
            False,
            "List round_id (should fail)"
        ),
        (
            {'type': 'place_bet', 'color': 'red', 'amount': 10, 'round_id': 'a' * 60},
            False,
            "Too long round_id (should fail)"
        ),
        (
            {'type': 'place_bet', 'color': 'red', 'amount': 10},
            False,
            "Missing round_id (should fail)"
        )
    ]
    
    passed = 0
    failed = 0
    
    for i, (test_data, expected_result, description) in enumerate(test_cases, 1):
        print(f"\n{i}. {description}")
        print(f"   Input: {test_data}")
        
        try:
            is_valid, error_msg = WebSocketValidator.validate_json_message(test_data)
            
            if is_valid == expected_result:
                print(f"   ✅ PASS - Valid: {is_valid}")
                if not is_valid:
                    print(f"   Error: {error_msg}")
                passed += 1
            else:
                print(f"   ❌ FAIL - Expected: {expected_result}, Got: {is_valid}")
                if error_msg:
                    print(f"   Error: {error_msg}")
                failed += 1
                
        except Exception as e:
            print(f"   ❌ EXCEPTION - {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 ALL TESTS PASSED! Round ID validation fix is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the validation logic.")
        return False

if __name__ == "__main__":
    success = test_round_id_validation()
    sys.exit(0 if success else 1)
