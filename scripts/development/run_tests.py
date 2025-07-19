#!/usr/bin/env python
"""
Comprehensive test runner for the Color Prediction Game.
This script provides various testing options and detailed reporting.
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')

import django
django.setup()

from django.core.management import execute_from_command_line
from django.test.utils import get_runner
from django.conf import settings


class ColoredOutput:
    """Utility class for colored console output."""
    
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'
    
    @classmethod
    def print_colored(cls, text, color):
        print(f"{color}{text}{cls.END}")
    
    @classmethod
    def print_header(cls, text):
        print(f"\n{cls.BOLD}{cls.CYAN}{'='*70}")
        print(f"{text}")
        print(f"{'='*70}{cls.END}")
    
    @classmethod
    def print_success(cls, text):
        print(f"{cls.GREEN}✓ {text}{cls.END}")
    
    @classmethod
    def print_error(cls, text):
        print(f"{cls.RED}✗ {text}{cls.END}")
    
    @classmethod
    def print_warning(cls, text):
        print(f"{cls.YELLOW}⚠ {text}{cls.END}")
    
    @classmethod
    def print_info(cls, text):
        print(f"{cls.BLUE}ℹ {text}{cls.END}")


class TestRunner:
    """Main test runner class."""
    
    def __init__(self):
        self.test_suites = {
            'auth': 'tests.test_authentication',
            'game': 'tests.test_game_mechanics',
            'admin': 'tests.test_admin_panel',
            'wallet': 'tests.test_wallet_system',
            'api': 'tests.test_comprehensive_api',
            'integration': 'tests.test_integration',
            'performance': 'tests.test_performance',
            'security': 'tests.test_security',
            'core': 'tests.test_core_functionality',
        }
        
        self.quick_tests = [
            'tests.test_authentication.UserLoginTests',
            'tests.test_game_mechanics.BettingSystemTests',
            'tests.test_wallet_system.WalletServiceTests',
            'tests.test_comprehensive_api.AuthenticatedAPITests',
        ]
        
        self.security_tests = [
            'tests.test_authentication.SecurityValidationTests',
            'tests.test_security.AuthenticationSecurityTests',
            'tests.test_security.InputValidationSecurityTests',
            'tests.test_security.AuthorizationSecurityTests',
        ]
        
        self.performance_tests = [
            'tests.test_performance.DatabasePerformanceTests',
            'tests.test_performance.ConcurrentUserTests',
            'tests.test_performance.LoadTestingTests',
        ]
    
    def run_command(self, command, description):
        """Run a command and return success status."""
        ColoredOutput.print_info(f"Running: {description}")
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=project_root
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            if result.returncode == 0:
                ColoredOutput.print_success(f"{description} completed in {duration:.2f}s")
                return True
            else:
                ColoredOutput.print_error(f"{description} failed in {duration:.2f}s")
                if result.stderr:
                    print(f"Error: {result.stderr}")
                return False
                
        except Exception as e:
            ColoredOutput.print_error(f"{description} failed with exception: {e}")
            return False
    
    def run_django_tests(self, test_pattern, verbosity=1):
        """Run Django tests with specified pattern."""
        command = f"python manage.py test {test_pattern} --verbosity={verbosity}"
        return self.run_command(command, f"Django tests: {test_pattern}")
    
    def run_all_tests(self, verbosity=1):
        """Run all test suites."""
        ColoredOutput.print_header("🧪 RUNNING COMPREHENSIVE TEST SUITE")
        
        results = {}
        total_start_time = time.time()
        
        for name, suite in self.test_suites.items():
            ColoredOutput.print_header(f"Running {name.upper()} Tests")
            success = self.run_django_tests(suite, verbosity)
            results[name] = success
        
        total_end_time = time.time()
        total_duration = total_end_time - total_start_time
        
        # Print summary
        self.print_test_summary(results, total_duration)
        
        return all(results.values())
    
    def run_quick_tests(self, verbosity=1):
        """Run quick test suite."""
        ColoredOutput.print_header("⚡ RUNNING QUICK TEST SUITE")
        
        test_pattern = ' '.join(self.quick_tests)
        return self.run_django_tests(test_pattern, verbosity)
    
    def run_security_tests(self, verbosity=1):
        """Run security test suite."""
        ColoredOutput.print_header("🔒 RUNNING SECURITY TEST SUITE")
        
        test_pattern = ' '.join(self.security_tests)
        return self.run_django_tests(test_pattern, verbosity)
    
    def run_performance_tests(self, verbosity=1):
        """Run performance test suite."""
        ColoredOutput.print_header("🚀 RUNNING PERFORMANCE TEST SUITE")
        
        test_pattern = ' '.join(self.performance_tests)
        return self.run_django_tests(test_pattern, verbosity)
    
    def run_specific_suite(self, suite_name, verbosity=1):
        """Run a specific test suite."""
        if suite_name not in self.test_suites:
            ColoredOutput.print_error(f"Unknown test suite: {suite_name}")
            ColoredOutput.print_info(f"Available suites: {', '.join(self.test_suites.keys())}")
            return False
        
        ColoredOutput.print_header(f"Running {suite_name.upper()} Test Suite")
        return self.run_django_tests(self.test_suites[suite_name], verbosity)
    
    def print_test_summary(self, results, duration):
        """Print test summary."""
        ColoredOutput.print_header("📊 TEST SUMMARY")
        
        passed = sum(1 for success in results.values() if success)
        total = len(results)
        
        print(f"Total Test Suites: {total}")
        ColoredOutput.print_success(f"Passed: {passed}")
        
        if passed < total:
            ColoredOutput.print_error(f"Failed: {total - passed}")
        
        print(f"Total Duration: {duration:.2f} seconds")
        
        # Detailed results
        print(f"\n{ColoredOutput.BOLD}Detailed Results:{ColoredOutput.END}")
        for suite, success in results.items():
            status = "✓ PASS" if success else "✗ FAIL"
            color = ColoredOutput.GREEN if success else ColoredOutput.RED
            print(f"  {suite:<15} {color}{status}{ColoredOutput.END}")
        
        # Overall result
        if passed == total:
            ColoredOutput.print_success("\n🎉 ALL TEST SUITES PASSED! 🎉")
            ColoredOutput.print_success("Your Color Prediction Game is ready for production! 🚀")
        else:
            ColoredOutput.print_error(f"\n❌ {total - passed} TEST SUITE(S) FAILED")
            ColoredOutput.print_warning("Please review the failed tests before deployment.")
    
    def check_environment(self):
        """Check test environment setup."""
        ColoredOutput.print_header("🔍 CHECKING TEST ENVIRONMENT")
        
        checks = [
            ("Python version", sys.version_info >= (3, 8)),
            ("Django installation", self.check_django()),
            ("Database connection", self.check_database()),
            ("Test settings", self.check_test_settings()),
        ]
        
        all_passed = True
        for check_name, result in checks:
            if result:
                ColoredOutput.print_success(f"{check_name}: OK")
            else:
                ColoredOutput.print_error(f"{check_name}: FAILED")
                all_passed = False
        
        return all_passed
    
    def check_django(self):
        """Check Django installation."""
        try:
            import django
            return True
        except ImportError:
            return False
    
    def check_database(self):
        """Check database connection."""
        try:
            from django.db import connection
            connection.ensure_connection()
            return True
        except Exception:
            return False
    
    def check_test_settings(self):
        """Check test settings."""
        try:
            return hasattr(settings, 'DATABASES') and 'default' in settings.DATABASES
        except Exception:
            return False
    
    def setup_test_data(self):
        """Set up test data."""
        ColoredOutput.print_header("🔧 SETTING UP TEST DATA")
        
        commands = [
            ("python manage.py migrate", "Running migrations"),
            ("python manage.py shell -c \"from tests.utils import setup_test_notification_types; setup_test_notification_types()\"", "Setting up notification types"),
        ]
        
        for command, description in commands:
            if not self.run_command(command, description):
                return False
        
        return True
    
    def generate_coverage_report(self):
        """Generate test coverage report."""
        ColoredOutput.print_header("📊 GENERATING COVERAGE REPORT")
        
        commands = [
            ("coverage run --source='.' manage.py test", "Running tests with coverage"),
            ("coverage report", "Generating coverage report"),
            ("coverage html", "Generating HTML coverage report"),
        ]
        
        for command, description in commands:
            self.run_command(command, description)
        
        ColoredOutput.print_info("Coverage report generated in htmlcov/index.html")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Color Prediction Game Test Runner')
    parser.add_argument('command', nargs='?', default='all',
                       help='Test command: all, quick, security, performance, or suite name')
    parser.add_argument('-v', '--verbosity', type=int, default=1, choices=[0, 1, 2],
                       help='Verbosity level')
    parser.add_argument('--check', action='store_true',
                       help='Check test environment')
    parser.add_argument('--setup', action='store_true',
                       help='Set up test data')
    parser.add_argument('--coverage', action='store_true',
                       help='Generate coverage report')
    
    args = parser.parse_args()
    
    runner = TestRunner()
    
    # Check environment if requested
    if args.check:
        if not runner.check_environment():
            sys.exit(1)
        return
    
    # Set up test data if requested
    if args.setup:
        if not runner.setup_test_data():
            sys.exit(1)
        return
    
    # Generate coverage report if requested
    if args.coverage:
        runner.generate_coverage_report()
        return
    
    # Run tests based on command
    success = False
    
    if args.command == 'all':
        success = runner.run_all_tests(args.verbosity)
    elif args.command == 'quick':
        success = runner.run_quick_tests(args.verbosity)
    elif args.command == 'security':
        success = runner.run_security_tests(args.verbosity)
    elif args.command == 'performance':
        success = runner.run_performance_tests(args.verbosity)
    elif args.command in runner.test_suites:
        success = runner.run_specific_suite(args.command, args.verbosity)
    else:
        ColoredOutput.print_error(f"Unknown command: {args.command}")
        ColoredOutput.print_info("Available commands: all, quick, security, performance")
        ColoredOutput.print_info(f"Available suites: {', '.join(runner.test_suites.keys())}")
        sys.exit(1)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
