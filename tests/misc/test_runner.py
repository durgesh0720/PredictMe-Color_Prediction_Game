"""
Comprehensive test runner for the Color Prediction Game.
Runs all test suites and generates detailed reports.
"""

import os
import sys
import time
import unittest
from io import StringIO
from django.test.runner import DiscoverRunner
from django.test.utils import get_runner
from django.conf import settings
from django.core.management import execute_from_command_line


class ColoredTestResult(unittest.TextTestResult):
    """Test result class with colored output."""
    
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.success_count = 0
        self.start_time = None
    
    def startTest(self, test):
        super().startTest(test)
        self.start_time = time.time()
        if self.verbosity > 1:
            self.stream.write(f"Running {test._testMethodName}... ")
            self.stream.flush()
    
    def addSuccess(self, test):
        super().addSuccess(test)
        self.success_count += 1
        if self.verbosity > 1:
            elapsed = time.time() - self.start_time
            self.stream.write(f"\033[92m✓ PASS\033[0m ({elapsed:.3f}s)\n")
    
    def addError(self, test, err):
        super().addError(test, err)
        if self.verbosity > 1:
            elapsed = time.time() - self.start_time
            self.stream.write(f"\033[91m✗ ERROR\033[0m ({elapsed:.3f}s)\n")
    
    def addFailure(self, test, err):
        super().addFailure(test, err)
        if self.verbosity > 1:
            elapsed = time.time() - self.start_time
            self.stream.write(f"\033[91m✗ FAIL\033[0m ({elapsed:.3f}s)\n")
    
    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        if self.verbosity > 1:
            elapsed = time.time() - self.start_time
            self.stream.write(f"\033[93m- SKIP\033[0m ({elapsed:.3f}s): {reason}\n")


class ColoredTestRunner(unittest.TextTestRunner):
    """Test runner with colored output."""
    
    resultclass = ColoredTestResult
    
    def run(self, test):
        result = super().run(test)
        
        # Print summary
        print("\n" + "="*70)
        print(f"\033[1mTEST SUMMARY\033[0m")
        print("="*70)
        
        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        skipped = len(result.skipped)
        success = result.success_count
        
        print(f"Total Tests: {total_tests}")
        print(f"\033[92mPassed: {success}\033[0m")
        if failures > 0:
            print(f"\033[91mFailed: {failures}\033[0m")
        if errors > 0:
            print(f"\033[91mErrors: {errors}\033[0m")
        if skipped > 0:
            print(f"\033[93mSkipped: {skipped}\033[0m")
        
        success_rate = (success / total_tests * 100) if total_tests > 0 else 0
        print(f"Success Rate: {success_rate:.1f}%")
        
        if failures == 0 and errors == 0:
            print(f"\n\033[92m🎉 ALL TESTS PASSED! 🎉\033[0m")
        else:
            print(f"\n\033[91m❌ SOME TESTS FAILED\033[0m")
        
        return result


class ComprehensiveTestRunner:
    """Comprehensive test runner for all test suites."""
    
    def __init__(self):
        self.test_suites = [
            'tests.test_authentication',
            'tests.test_game_mechanics', 
            'tests.test_admin_panel',
            'tests.test_wallet_system',
            'tests.test_comprehensive_api',
            'tests.test_integration',
            'tests.test_core_functionality',
        ]
        
        self.results = {}
    
    def run_test_suite(self, suite_name, verbosity=2):
        """Run a specific test suite."""
        print(f"\n{'='*70}")
        print(f"\033[1m🧪 RUNNING {suite_name.upper()}\033[0m")
        print(f"{'='*70}")
        
        # Capture output
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        try:
            # Run the test
            from django.test.utils import get_runner
            TestRunner = get_runner(settings)
            test_runner = TestRunner(verbosity=verbosity, interactive=False)
            
            start_time = time.time()
            result = test_runner.run_tests([suite_name])
            end_time = time.time()
            
            # Store results
            self.results[suite_name] = {
                'passed': result == 0,
                'duration': end_time - start_time,
                'exit_code': result
            }
            
            return result == 0
            
        except Exception as e:
            print(f"\033[91mError running {suite_name}: {e}\033[0m")
            self.results[suite_name] = {
                'passed': False,
                'duration': 0,
                'exit_code': 1,
                'error': str(e)
            }
            return False
        
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def run_all_tests(self, verbosity=2):
        """Run all test suites."""
        print("\033[1m" + "="*70)
        print("🚀 STARTING COMPREHENSIVE TEST SUITE")
        print("="*70 + "\033[0m")
        
        total_start_time = time.time()
        
        # Run each test suite
        for suite in self.test_suites:
            success = self.run_test_suite(suite, verbosity)
            
            if success:
                print(f"\033[92m✓ {suite} PASSED\033[0m")
            else:
                print(f"\033[91m✗ {suite} FAILED\033[0m")
        
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        # Print final summary
        self.print_final_summary(total_duration)
        
        # Return overall success
        return all(result['passed'] for result in self.results.values())
    
    def print_final_summary(self, total_duration):
        """Print final test summary."""
        print("\n" + "="*70)
        print("\033[1m📊 FINAL TEST REPORT\033[0m")
        print("="*70)
        
        passed_suites = sum(1 for r in self.results.values() if r['passed'])
        total_suites = len(self.results)
        
        print(f"Total Test Suites: {total_suites}")
        print(f"\033[92mPassed: {passed_suites}\033[0m")
        print(f"\033[91mFailed: {total_suites - passed_suites}\033[0m")
        print(f"Total Duration: {total_duration:.2f} seconds")
        
        # Detailed results
        print(f"\n\033[1mDetailed Results:\033[0m")
        for suite, result in self.results.items():
            status = "\033[92m✓ PASS\033[0m" if result['passed'] else "\033[91m✗ FAIL\033[0m"
            duration = result['duration']
            print(f"  {suite:<40} {status} ({duration:.2f}s)")
        
        # Overall result
        if passed_suites == total_suites:
            print(f"\n\033[92m🎉 ALL TEST SUITES PASSED! 🎉\033[0m")
            print(f"\033[92mYour Color Prediction Game is ready for production! 🚀\033[0m")
        else:
            print(f"\n\033[91m❌ {total_suites - passed_suites} TEST SUITE(S) FAILED\033[0m")
            print(f"\033[93mPlease review the failed tests before deployment.\033[0m")
    
    def run_specific_tests(self, test_patterns, verbosity=2):
        """Run specific test patterns."""
        print(f"\033[1m🎯 RUNNING SPECIFIC TESTS: {', '.join(test_patterns)}\033[0m")
        
        for pattern in test_patterns:
            self.run_test_suite(pattern, verbosity)
        
        # Print summary for specific tests
        passed = sum(1 for r in self.results.values() if r['passed'])
        total = len(self.results)
        
        if passed == total:
            print(f"\n\033[92m✓ All specified tests passed!\033[0m")
        else:
            print(f"\n\033[91m✗ {total - passed} test(s) failed\033[0m")


def run_quick_tests():
    """Run a quick subset of critical tests."""
    runner = ComprehensiveTestRunner()
    
    quick_tests = [
        'tests.test_authentication.UserLoginTests',
        'tests.test_game_mechanics.BettingSystemTests',
        'tests.test_wallet_system.WalletServiceTests',
        'tests.test_comprehensive_api.AuthenticatedAPITests',
    ]
    
    print("\033[1m⚡ RUNNING QUICK TEST SUITE\033[0m")
    runner.run_specific_tests(quick_tests, verbosity=1)


def run_security_tests():
    """Run security-focused tests."""
    runner = ComprehensiveTestRunner()
    
    security_tests = [
        'tests.test_authentication.SecurityValidationTests',
        'tests.test_comprehensive_api.APISecurityTests',
        'tests.test_wallet_system.FraudDetectionTests',
    ]
    
    print("\033[1m🔒 RUNNING SECURITY TEST SUITE\033[0m")
    runner.run_specific_tests(security_tests, verbosity=2)


def run_performance_tests():
    """Run performance-focused tests."""
    runner = ComprehensiveTestRunner()
    
    performance_tests = [
        'tests.test_comprehensive_api.PerformanceTests',
        'tests.test_integration.SystemStressTest',
        'tests.test_game_mechanics.RealTimeUpdatesTests',
    ]
    
    print("\033[1m🚀 RUNNING PERFORMANCE TEST SUITE\033[0m")
    runner.run_specific_tests(performance_tests, verbosity=2)


if __name__ == '__main__':
    import django
    from django.conf import settings
    
    # Configure Django settings for testing
    if not settings.configured:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.test_settings')
        django.setup()
    
    # Parse command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'quick':
            run_quick_tests()
        elif command == 'security':
            run_security_tests()
        elif command == 'performance':
            run_performance_tests()
        elif command == 'all':
            runner = ComprehensiveTestRunner()
            success = runner.run_all_tests()
            sys.exit(0 if success else 1)
        else:
            # Run specific test pattern
            runner = ComprehensiveTestRunner()
            runner.run_specific_tests([command])
    else:
        # Run all tests by default
        runner = ComprehensiveTestRunner()
        success = runner.run_all_tests()
        sys.exit(0 if success else 1)
