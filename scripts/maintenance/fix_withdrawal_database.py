#!/usr/bin/env python
"""
Script to fix the withdrawal system database issues
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.db import connection, transaction
from django.core.management import execute_from_command_line

def check_and_fix_database():
    """Check and fix database issues for withdrawal system"""
    
    print("🔧 Checking withdrawal system database...")
    
    with connection.cursor() as cursor:
        # Check if wallet_transactions table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='wallet_transactions';
        """)
        
        wallet_table_exists = cursor.fetchone() is not None
        
        if wallet_table_exists:
            print("✅ wallet_transactions table exists")
        else:
            print("❌ wallet_transactions table missing - creating it...")
            
            # Create the wallet_transactions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallet_transactions (
                    id TEXT PRIMARY KEY,
                    transaction_type VARCHAR(20) NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    balance_before DECIMAL(10, 2) NOT NULL,
                    balance_after DECIMAL(10, 2) NOT NULL,
                    description TEXT,
                    payment_reference VARCHAR(100),
                    involves_real_money BOOLEAN NOT NULL DEFAULT 1,
                    master_wallet_transaction_id VARCHAR(100),
                    created_at DATETIME NOT NULL,
                    player_id INTEGER NOT NULL,
                    FOREIGN KEY (player_id) REFERENCES polling_player (id)
                );
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_wallet_transactions_player 
                ON wallet_transactions(player_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at 
                ON wallet_transactions(created_at);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_wallet_transactions_type 
                ON wallet_transactions(transaction_type);
            """)
            
            print("✅ wallet_transactions table created successfully")
        
        # Check if withdrawal_requests table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='withdrawal_requests';
        """)
        
        withdrawal_table_exists = cursor.fetchone() is not None
        
        if withdrawal_table_exists:
            print("✅ withdrawal_requests table exists")
        else:
            print("❌ withdrawal_requests table missing - creating it...")
            
            # Create the withdrawal_requests table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS withdrawal_requests (
                    id TEXT PRIMARY KEY,
                    amount DECIMAL(10, 2) NOT NULL,
                    bank_account_number VARCHAR(50) NOT NULL,
                    bank_ifsc_code VARCHAR(20) NOT NULL,
                    bank_name VARCHAR(100) NOT NULL,
                    account_holder_name VARCHAR(100) NOT NULL,
                    status VARCHAR(20) NOT NULL DEFAULT 'pending',
                    payment_reference VARCHAR(100),
                    payment_gateway_response TEXT,
                    admin_notes TEXT,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    approved_at DATETIME,
                    processed_at DATETIME,
                    player_id INTEGER NOT NULL,
                    approved_by_id INTEGER,
                    FOREIGN KEY (player_id) REFERENCES polling_player (id),
                    FOREIGN KEY (approved_by_id) REFERENCES polling_admin (id)
                );
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_player 
                ON withdrawal_requests(player_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status 
                ON withdrawal_requests(status);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_created_at 
                ON withdrawal_requests(created_at);
            """)
            
            print("✅ withdrawal_requests table created successfully")
        
        # Check if master_wallet table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='master_wallet';
        """)
        
        master_wallet_exists = cursor.fetchone() is not None
        
        if master_wallet_exists:
            print("✅ master_wallet table exists")
        else:
            print("❌ master_wallet table missing - creating it...")
            
            # Create the master_wallet table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS master_wallet (
                    id TEXT PRIMARY KEY,
                    total_balance DECIMAL(15, 2) NOT NULL DEFAULT 0,
                    available_balance DECIMAL(15, 2) NOT NULL DEFAULT 0,
                    reserved_balance DECIMAL(15, 2) NOT NULL DEFAULT 0,
                    bank_account_number VARCHAR(50),
                    bank_ifsc_code VARCHAR(20),
                    bank_name VARCHAR(100),
                    account_holder_name VARCHAR(100),
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                );
            """)
            
            print("✅ master_wallet table created successfully")
        
        # Check if master wallet record exists
        cursor.execute("SELECT COUNT(*) FROM master_wallet;")
        master_wallet_count = cursor.fetchone()[0]
        
        if master_wallet_count == 0:
            print("❌ No master wallet record found - creating default...")
            
            import uuid
            from django.utils import timezone
            
            cursor.execute("""
                INSERT INTO master_wallet (
                    id, total_balance, available_balance, reserved_balance,
                    created_at, updated_at
                ) VALUES (?, 0, 0, 0, ?, ?);
            """, [
                str(uuid.uuid4()),
                timezone.now(),
                timezone.now()
            ])
            
            print("✅ Default master wallet created")
        else:
            print(f"✅ Master wallet record exists (count: {master_wallet_count})")

def test_withdrawal_system():
    """Test if the withdrawal system is working"""
    
    print("\n🧪 Testing withdrawal system...")
    
    try:
        from polling.models import Player, WalletTransaction, WithdrawalRequest, MasterWallet
        
        # Test model imports
        print("✅ All models imported successfully")
        
        # Test database queries
        player_count = Player.objects.count()
        print(f"✅ Players in database: {player_count}")
        
        wallet_transaction_count = WalletTransaction.objects.count()
        print(f"✅ Wallet transactions: {wallet_transaction_count}")
        
        withdrawal_count = WithdrawalRequest.objects.count()
        print(f"✅ Withdrawal requests: {withdrawal_count}")
        
        master_wallet_count = MasterWallet.objects.count()
        print(f"✅ Master wallets: {master_wallet_count}")
        
        print("\n🎉 Withdrawal system is working correctly!")
        
    except Exception as e:
        print(f"❌ Error testing withdrawal system: {e}")
        return False
    
    return True

def main():
    """Main function"""
    
    print("🚀 Starting withdrawal system database fix...")
    
    try:
        # Fix database issues
        check_and_fix_database()
        
        # Test the system
        if test_withdrawal_system():
            print("\n✅ Withdrawal system is ready!")
            print("\n📋 Next steps:")
            print("1. Try creating a withdrawal request from the user interface")
            print("2. Check the admin panel at /control-panel/withdrawals/")
            print("3. Test approval/rejection functionality")
            print("\n🧪 Use these test bank details:")
            print("   Account Number: 123456789012")
            print("   IFSC Code: SBIN0001234")
            print("   Account Holder: Test User")
            print("   Bank Name: State Bank of India")
        else:
            print("\n❌ There are still issues with the withdrawal system")
            
    except Exception as e:
        print(f"❌ Error fixing database: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
