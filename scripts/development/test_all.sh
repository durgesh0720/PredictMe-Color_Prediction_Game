#!/bin/bash

# Comprehensive Test Execution Script for Color Prediction Game
# This script runs all tests with proper setup and reporting

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Function to print colored output
print_colored() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_header() {
    echo
    print_colored $CYAN "=================================================================="
    print_colored $WHITE "$1"
    print_colored $CYAN "=================================================================="
}

print_success() {
    print_colored $GREEN "✓ $1"
}

print_error() {
    print_colored $RED "✗ $1"
}

print_warning() {
    print_colored $YELLOW "⚠ $1"
}

print_info() {
    print_colored $BLUE "ℹ $1"
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check Python version
check_python_version() {
    local python_version=$(python --version 2>&1 | cut -d' ' -f2)
    local major_version=$(echo $python_version | cut -d'.' -f1)
    local minor_version=$(echo $python_version | cut -d'.' -f2)
    
    if [ "$major_version" -eq 3 ] && [ "$minor_version" -ge 8 ]; then
        print_success "Python version: $python_version"
        return 0
    else
        print_error "Python 3.8+ required, found: $python_version"
        return 1
    fi
}

# Function to setup virtual environment
setup_venv() {
    if [ ! -d "venv" ]; then
        print_info "Creating virtual environment..."
        python -m venv venv
    fi
    
    print_info "Activating virtual environment..."
    source venv/bin/activate
    
    print_info "Upgrading pip..."
    pip install --upgrade pip
}

# Function to install dependencies
install_dependencies() {
    print_info "Installing test dependencies..."
    
    if [ -f "requirements-test.txt" ]; then
        pip install -r requirements-test.txt
    else
        print_warning "requirements-test.txt not found, installing basic dependencies..."
        pip install pytest pytest-django coverage
    fi
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    fi
}

# Function to setup database
setup_database() {
    print_info "Setting up test database..."
    python manage.py migrate --settings=tests.test_settings
}

# Function to run environment checks
run_environment_checks() {
    print_header "🔍 ENVIRONMENT CHECKS"
    
    local checks_passed=0
    local total_checks=5
    
    # Check Python version
    if check_python_version; then
        ((checks_passed++))
    fi
    
    # Check Django
    if python -c "import django; print('Django version:', django.get_version())" 2>/dev/null; then
        print_success "Django installation: OK"
        ((checks_passed++))
    else
        print_error "Django installation: FAILED"
    fi
    
    # Check database connection
    if python manage.py check --database default --settings=tests.test_settings >/dev/null 2>&1; then
        print_success "Database connection: OK"
        ((checks_passed++))
    else
        print_error "Database connection: FAILED"
    fi
    
    # Check test settings
    if python -c "from tests.test_settings import *; print('Test settings loaded')" >/dev/null 2>&1; then
        print_success "Test settings: OK"
        ((checks_passed++))
    else
        print_error "Test settings: FAILED"
    fi
    
    # Check required directories
    if [ -d "tests" ]; then
        print_success "Test directory: OK"
        ((checks_passed++))
    else
        print_error "Test directory: MISSING"
    fi
    
    print_info "Environment checks: $checks_passed/$total_checks passed"
    
    if [ $checks_passed -eq $total_checks ]; then
        return 0
    else
        return 1
    fi
}

# Function to run specific test suite
run_test_suite() {
    local suite_name=$1
    local description=$2
    
    print_header "🧪 RUNNING $description"
    
    local start_time=$(date +%s)
    
    if python manage.py test $suite_name --verbosity=2 --settings=tests.test_settings; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_success "$description completed in ${duration}s"
        return 0
    else
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))
        print_error "$description failed in ${duration}s"
        return 1
    fi
}

# Function to run all tests
run_all_tests() {
    print_header "🚀 RUNNING COMPREHENSIVE TEST SUITE"
    
    local total_suites=0
    local passed_suites=0
    local start_time=$(date +%s)
    
    # Define test suites
    declare -A test_suites=(
        ["tests.test_authentication"]="AUTHENTICATION TESTS"
        ["tests.test_game_mechanics"]="GAME MECHANICS TESTS"
        ["tests.test_admin_panel"]="ADMIN PANEL TESTS"
        ["tests.test_wallet_system"]="WALLET SYSTEM TESTS"
        ["tests.test_comprehensive_api"]="API TESTS"
        ["tests.test_integration"]="INTEGRATION TESTS"
        ["tests.test_performance"]="PERFORMANCE TESTS"
        ["tests.test_security"]="SECURITY TESTS"
        ["tests.test_core_functionality"]="CORE FUNCTIONALITY TESTS"
    )
    
    # Run each test suite
    for suite in "${!test_suites[@]}"; do
        ((total_suites++))
        if run_test_suite "$suite" "${test_suites[$suite]}"; then
            ((passed_suites++))
        fi
    done
    
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    # Print summary
    print_header "📊 TEST SUMMARY"
    echo "Total Test Suites: $total_suites"
    print_success "Passed: $passed_suites"
    
    if [ $passed_suites -lt $total_suites ]; then
        local failed_suites=$((total_suites - passed_suites))
        print_error "Failed: $failed_suites"
    fi
    
    echo "Total Duration: ${total_duration}s"
    
    if [ $passed_suites -eq $total_suites ]; then
        print_success "🎉 ALL TEST SUITES PASSED! 🎉"
        print_success "Your Color Prediction Game is ready for production! 🚀"
        return 0
    else
        print_error "❌ Some test suites failed"
        print_warning "Please review the failed tests before deployment."
        return 1
    fi
}

# Function to run quick tests
run_quick_tests() {
    print_header "⚡ RUNNING QUICK TEST SUITE"
    
    local quick_tests=(
        "tests.test_authentication.UserLoginTests"
        "tests.test_game_mechanics.BettingSystemTests"
        "tests.test_wallet_system.WalletServiceTests"
        "tests.test_comprehensive_api.AuthenticatedAPITests"
    )
    
    local test_pattern=$(IFS=' '; echo "${quick_tests[*]}")
    
    if python manage.py test $test_pattern --verbosity=2 --settings=tests.test_settings; then
        print_success "Quick tests passed!"
        return 0
    else
        print_error "Quick tests failed!"
        return 1
    fi
}

# Function to run security tests
run_security_tests() {
    print_header "🔒 RUNNING SECURITY TEST SUITE"
    
    local security_tests=(
        "tests.test_authentication.SecurityValidationTests"
        "tests.test_security.AuthenticationSecurityTests"
        "tests.test_security.InputValidationSecurityTests"
        "tests.test_security.AuthorizationSecurityTests"
    )
    
    local test_pattern=$(IFS=' '; echo "${security_tests[*]}")
    
    if python manage.py test $test_pattern --verbosity=2 --settings=tests.test_settings; then
        print_success "Security tests passed!"
        return 0
    else
        print_error "Security tests failed!"
        return 1
    fi
}

# Function to generate coverage report
generate_coverage_report() {
    print_header "📊 GENERATING COVERAGE REPORT"
    
    print_info "Running tests with coverage..."
    coverage run --source='.' manage.py test --settings=tests.test_settings
    
    print_info "Generating coverage report..."
    coverage report
    
    print_info "Generating HTML coverage report..."
    coverage html
    
    print_success "Coverage report generated in htmlcov/index.html"
}

# Function to run linting
run_linting() {
    print_header "🔍 RUNNING CODE QUALITY CHECKS"
    
    if command_exists flake8; then
        print_info "Running flake8..."
        flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
        print_success "Flake8 checks passed"
    else
        print_warning "flake8 not installed, skipping..."
    fi
    
    if command_exists black; then
        print_info "Checking code formatting with black..."
        black --check .
        print_success "Black formatting checks passed"
    else
        print_warning "black not installed, skipping..."
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTION]"
    echo ""
    echo "Options:"
    echo "  all         Run all test suites (default)"
    echo "  quick       Run quick test suite"
    echo "  security    Run security tests"
    echo "  coverage    Generate coverage report"
    echo "  lint        Run code quality checks"
    echo "  setup       Setup test environment"
    echo "  check       Check environment only"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 all      # Run all tests"
    echo "  $0 quick    # Run quick tests"
    echo "  $0 coverage # Generate coverage report"
}

# Main execution
main() {
    local command=${1:-all}
    
    case $command in
        "all")
            if run_environment_checks; then
                run_all_tests
            else
                print_error "Environment checks failed"
                exit 1
            fi
            ;;
        "quick")
            if run_environment_checks; then
                run_quick_tests
            else
                print_error "Environment checks failed"
                exit 1
            fi
            ;;
        "security")
            if run_environment_checks; then
                run_security_tests
            else
                print_error "Environment checks failed"
                exit 1
            fi
            ;;
        "coverage")
            if run_environment_checks; then
                generate_coverage_report
            else
                print_error "Environment checks failed"
                exit 1
            fi
            ;;
        "lint")
            run_linting
            ;;
        "setup")
            setup_venv
            install_dependencies
            setup_database
            print_success "Test environment setup complete!"
            ;;
        "check")
            run_environment_checks
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            print_error "Unknown command: $command"
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
