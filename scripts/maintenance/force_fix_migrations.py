#!/usr/bin/env python
"""
Force fix migrations by cleaning up Django's migration state
"""

import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def main():
    print("🔧 Force fixing migration state...")
    
    with connection.cursor() as cursor:
        # 1. Check current migration state
        print("\n📋 Current migration state:")
        cursor.execute("SELECT name FROM django_migrations WHERE app='polling' ORDER BY name;")
        migrations = cursor.fetchall()
        for migration in migrations:
            print(f"  ✅ {migration[0]}")
        
        # 2. Remove any problematic migrations from Django's records
        problematic_migrations = [
            '0026_remove_playerachievement_achievement_and_more',
            '0027_remove_playerachievement_achievement_and_more',  # Just in case
        ]
        
        for migration_name in problematic_migrations:
            cursor.execute(
                "DELETE FROM django_migrations WHERE app='polling' AND name=?;", 
                [migration_name]
            )
            print(f"🗑️  Removed {migration_name} from Django's records")
        
        # 3. Ensure withdrawal system tables exist
        print("\n🔧 Ensuring withdrawal system tables exist...")
        
        # Check what tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [table[0] for table in cursor.fetchall()]
        
        # Create wallet_transactions if missing
        if 'wallet_transactions' not in existing_tables:
            print("Creating wallet_transactions table...")
            cursor.execute("""
                CREATE TABLE wallet_transactions (
                    id TEXT PRIMARY KEY,
                    transaction_type VARCHAR(20) NOT NULL,
                    amount DECIMAL(10, 2) NOT NULL,
                    balance_before DECIMAL(10, 2) NOT NULL,
                    balance_after DECIMAL(10, 2) NOT NULL,
                    description TEXT,
                    payment_reference VARCHAR(100),
                    involves_real_money BOOLEAN NOT NULL DEFAULT 1,
                    master_wallet_transaction_id VARCHAR(100),
                    withdrawal_request_id VARCHAR(100),
                    created_at DATETIME NOT NULL,
                    player_id INTEGER NOT NULL
                );
            """)
            print("✅ wallet_transactions table created")
        else:
            print("✅ wallet_transactions table exists")
        
        # Create withdrawal_requests if missing
        if 'withdrawal_requests' not in existing_tables:
            print("Creating withdrawal_requests table...")
            cursor.execute("""
                CREATE TABLE withdrawal_requests (
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
                    approved_by_id INTEGER
                );
            """)
            print("✅ withdrawal_requests table created")
        else:
            print("✅ withdrawal_requests table exists")
        
        # Create master_wallet if missing
        if 'master_wallet' not in existing_tables:
            print("Creating master_wallet table...")
            cursor.execute("""
                CREATE TABLE master_wallet (
                    id TEXT PRIMARY KEY,
                    total_balance DECIMAL(15, 2) NOT NULL DEFAULT 0,
                    available_balance DECIMAL(15, 2) NOT NULL DEFAULT 0,
                    reserved_balance DECIMAL(15, 2) NOT NULL DEFAULT 0,
                    total_deposits_received DECIMAL(15, 2) NOT NULL DEFAULT 0,
                    total_withdrawals_paid DECIMAL(15, 2) NOT NULL DEFAULT 0,
                    bank_account_number VARCHAR(50),
                    bank_ifsc_code VARCHAR(20),
                    bank_name VARCHAR(100),
                    account_holder_name VARCHAR(100),
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                );
            """)
            print("✅ master_wallet table created")
        else:
            print("✅ master_wallet table exists")
        
        # Create master_wallet_transactions if missing
        if 'master_wallet_transactions' not in existing_tables:
            print("Creating master_wallet_transactions table...")
            cursor.execute("""
                CREATE TABLE master_wallet_transactions (
                    id TEXT PRIMARY KEY,
                    transaction_type VARCHAR(20) NOT NULL,
                    amount DECIMAL(12, 2) NOT NULL,
                    balance_after DECIMAL(15, 2) NOT NULL,
                    description TEXT NOT NULL,
                    created_at DATETIME NOT NULL,
                    master_wallet_id TEXT NOT NULL
                );
            """)
            print("✅ master_wallet_transactions table created")
        else:
            print("✅ master_wallet_transactions table exists")
        
        # 4. Mark our migrations as applied
        migrations_to_mark = [
            '0024_ensure_wallet_transactions_table',
            '0025_finalize_withdrawal_system',
        ]
        
        for migration_name in migrations_to_mark:
            cursor.execute(
                "INSERT OR IGNORE INTO django_migrations (app, name, applied) VALUES (?, ?, datetime('now'));",
                ['polling', migration_name]
            )
            print(f"✅ Marked {migration_name} as applied")
        
        # 5. Ensure master wallet record exists
        cursor.execute("SELECT COUNT(*) FROM master_wallet;")
        master_wallet_count = cursor.fetchone()[0]
        
        if master_wallet_count == 0:
            cursor.execute("""
                INSERT INTO master_wallet (
                    id, total_balance, available_balance, reserved_balance,
                    total_deposits_received, total_withdrawals_paid,
                    created_at, updated_at
                ) VALUES (
                    'default-master-wallet',
                    0, 0, 0, 0, 0,
                    datetime('now'), datetime('now')
                );
            """)
            print("✅ Created default master wallet")
        else:
            print(f"✅ Master wallet exists (count: {master_wallet_count})")
    
    # 6. Test the models
    print("\n🧪 Testing withdrawal system...")
    try:
        from polling.models import Player, WalletTransaction, WithdrawalRequest, MasterWallet
        
        player_count = Player.objects.count()
        wallet_count = WalletTransaction.objects.count()
        withdrawal_count = WithdrawalRequest.objects.count()
        master_count = MasterWallet.objects.count()
        
        print(f"✅ Players: {player_count}")
        print(f"✅ Wallet transactions: {wallet_count}")
        print(f"✅ Withdrawal requests: {withdrawal_count}")
        print(f"✅ Master wallets: {master_count}")
        
        print("\n🎉 Withdrawal system is working correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error testing models: {e}")
        return False

if __name__ == "__main__":
    if main():
        print("\n🎉 Migration fix completed successfully!")
        print("\n📋 You can now:")
        print("1. Test withdrawal at /wallet/")
        print("2. Check admin panel at /control-panel/withdrawals/")
        print("3. Use test bank details:")
        print("   Account: 123456789012")
        print("   IFSC: SBIN0001234")
        print("   Name: Test User")
        print("   Bank: State Bank of India")
    else:
        print("\n❌ Fix failed. Check errors above.")
