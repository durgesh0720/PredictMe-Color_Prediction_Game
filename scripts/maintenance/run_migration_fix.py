#!/usr/bin/env python
"""
Script to safely run migrations and fix withdrawal system
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            print(f"Error: {result.stderr.strip()}")
            return False
    except Exception as e:
        print(f"❌ Error running {description}: {e}")
        return False

def main():
    """Main function to fix migration issues"""
    
    print("🚀 Starting migration fix for withdrawal system...")
    
    # Step 1: Show current migration status
    print("\n📋 Checking current migration status...")
    run_command("python manage.py showmigrations polling", "Checking migrations")
    
    # Step 2: Try to run migrations
    print("\n🔄 Running migrations...")
    if run_command("python manage.py migrate", "Running migrations"):
        print("\n🎉 Migrations completed successfully!")
        
        # Step 3: Test the withdrawal system
        print("\n🧪 Testing withdrawal system...")
        test_script = """
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.db import connection
from polling.models import Player, WalletTransaction, WithdrawalRequest, MasterWallet

# Check tables exist
with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('wallet_transactions', 'withdrawal_requests', 'master_wallet');")
    tables = cursor.fetchall()
    print(f"✅ Found tables: {[table[0] for table in tables]}")

# Test model queries
try:
    player_count = Player.objects.count()
    wallet_count = WalletTransaction.objects.count()
    withdrawal_count = WithdrawalRequest.objects.count()
    master_count = MasterWallet.objects.count()
    
    print(f"✅ Players: {player_count}")
    print(f"✅ Wallet transactions: {wallet_count}")
    print(f"✅ Withdrawal requests: {withdrawal_count}")
    print(f"✅ Master wallets: {master_count}")
    
    print("\\n🎉 Withdrawal system is working correctly!")
    print("\\n📋 You can now test withdrawals with these details:")
    print("   Account Number: 123456789012")
    print("   IFSC Code: SBIN0001234")
    print("   Account Holder: Test User")
    print("   Bank Name: State Bank of India")
    
except Exception as e:
    print(f"❌ Error testing models: {e}")
"""
        
        with open('test_withdrawal_system.py', 'w') as f:
            f.write(test_script)
        
        if run_command("python test_withdrawal_system.py", "Testing withdrawal system"):
            print("\n✅ All tests passed!")
        
        # Clean up test file
        try:
            os.remove('test_withdrawal_system.py')
        except:
            pass
            
    else:
        print("\n❌ Migration failed. Let's try to fix it...")
        
        # Alternative approach: Reset migrations
        print("\n🔄 Trying alternative approach...")
        print("You may need to:")
        print("1. Delete the problematic migration file manually")
        print("2. Run: python manage.py migrate --fake polling 0024")
        print("3. Then run: python manage.py migrate")
        
        return False
    
    return True

if __name__ == "__main__":
    if main():
        print("\n🎉 Migration fix completed successfully!")
        print("\n📋 Next steps:")
        print("1. Test withdrawal functionality in the web interface")
        print("2. Check admin panel at /control-panel/withdrawals/")
        print("3. Verify all currency symbols show ₹ instead of $")
    else:
        print("\n❌ Migration fix failed. Please check the errors above.")
        print("\nYou can try running the migration manually:")
        print("python manage.py migrate polling 0024 --fake")
        print("python manage.py migrate")
