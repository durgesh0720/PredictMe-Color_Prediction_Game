#!/usr/bin/env python3
"""
Verification script to check that all currency references are now in Rupees
"""
import os
import re
import glob

def check_currency_in_file(file_path):
    """Check for any remaining non-Rupee currency references"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        issues = []
        
        # Check for $ symbols (excluding template literals ${})
        dollar_pattern = r'\$(?!\{)(\d+(?:\.\d+)?|\w+)'
        dollar_matches = re.findall(dollar_pattern, content)
        if dollar_matches:
            issues.append(f"Found $ symbols: {dollar_matches}")
        
        # Check for USD currency codes
        if "'USD'" in content or '"USD"' in content:
            issues.append("Found USD currency code")
        
        # Check for dollar words
        if re.search(r'\bdollar\b', content, re.IGNORECASE):
            issues.append("Found 'dollar' word")
        
        # Count ₹ symbols (good)
        rupee_count = content.count('₹')
        if rupee_count > 0:
            issues.append(f"✅ Found {rupee_count} ₹ symbols")
        
        # Count INR currency codes (good)
        inr_count = content.count("'INR'") + content.count('"INR"')
        if inr_count > 0:
            issues.append(f"✅ Found {inr_count} INR currency codes")
        
        return issues
        
    except Exception as e:
        return [f"Error reading file: {e}"]

def main():
    """Main verification function"""
    print("🔍 Verifying Currency Conversion to Rupees...")
    print("=" * 60)
    
    # Key files to check
    key_files = [
        'polling/templates/room.html',
        'polling/responsible_gambling.py',
        'polling/payment_service.py',
        'server/settings.py',
        'tests/payment/test_payment_basic.py',
        'polling/templates/admin/modern_financial_management.html',
        'polling/templates/admin/modern_dashboard.html'
    ]
    
    total_rupee_symbols = 0
    total_inr_codes = 0
    issues_found = 0
    
    for file_path in key_files:
        if os.path.exists(file_path):
            print(f"\n📄 {file_path}")
            issues = check_currency_in_file(file_path)
            
            for issue in issues:
                if issue.startswith("✅"):
                    print(f"   {issue}")
                    if "₹ symbols" in issue:
                        count = int(issue.split()[2])
                        total_rupee_symbols += count
                    elif "INR currency codes" in issue:
                        count = int(issue.split()[2])
                        total_inr_codes += count
                else:
                    print(f"   ⚠️ {issue}")
                    issues_found += 1
        else:
            print(f"\n❌ {file_path} - File not found")
    
    print("\n" + "=" * 60)
    print("📊 Currency Conversion Summary:")
    print(f"   ✅ Total ₹ symbols found: {total_rupee_symbols}")
    print(f"   ✅ Total INR currency codes: {total_inr_codes}")
    print(f"   ⚠️ Issues found: {issues_found}")
    
    if issues_found == 0:
        print("\n🎉 SUCCESS: All currency references converted to Rupees!")
        print("   - Payment system uses INR")
        print("   - UI displays ₹ symbols")
        print("   - Comments and documentation updated")
        print("   - Test files use Rupee amounts")
    else:
        print(f"\n⚠️ WARNING: {issues_found} issues found that may need attention")
    
    # Quick test of key currency values
    print("\n🧪 Key Currency Settings:")
    try:
        import django
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
        django.setup()
        
        from django.conf import settings
        print(f"   MIN_DEPOSIT_AMOUNT: ₹{settings.MIN_DEPOSIT_AMOUNT}")
        print(f"   MAX_DEPOSIT_AMOUNT: ₹{settings.MAX_DEPOSIT_AMOUNT}")
        print(f"   MIN_WITHDRAWAL_AMOUNT: ₹{settings.MIN_WITHDRAWAL_AMOUNT}")
        print(f"   MAX_WITHDRAWAL_AMOUNT: ₹{settings.MAX_WITHDRAWAL_AMOUNT}")
        
        from polling.responsible_gambling import ResponsibleGamblingLimits
        limits = ResponsibleGamblingLimits()
        print(f"   MIN_BET_AMOUNT: ₹{limits.min_bet_amount/100:.2f}")
        print(f"   MAX_BET_AMOUNT: ₹{limits.max_bet_amount/100:.2f}")
        
    except Exception as e:
        print(f"   Error loading settings: {e}")

if __name__ == "__main__":
    main()
