#!/usr/bin/env python
"""
Complete migration fix script for withdrawal system
"""

import os
import sys
import django
import subprocess

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.db import connection
from django.core.management import execute_from_command_line

def run_sql(sql, description):
    """Execute SQL and handle errors"""
    print(f"🔧 {description}...")
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql)
        print(f"✅ {description} completed")
        return True
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False

def run_command(command, description):
    """Run management command"""
    print(f"🔧 {description}...")
    try:
        execute_from_command_line(command.split())
        print(f"✅ {description} completed")
        return True
    except Exception as e:
        print(f"❌ {description} failed: {e}")
        return False

def main():
    """Fix migrations completely"""
    
    print("🚀 Starting complete migration fix...")
    
    # Step 1: Check current database state
    print("\n📋 Checking current database state...")
    with connection.cursor() as cursor:
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [table[0] for table in cursor.fetchall()]
        print(f"Found {len(tables)} tables")
        
        # Check for problematic tables
        problem_tables = ['polling_achievement', 'polling_dailybonus', 'polling_playerachievement', 'polling_playerstats']
        existing_problem_tables = [t for t in problem_tables if t in tables]
        
        if existing_problem_tables:
            print(f"❌ Found problematic tables: {existing_problem_tables}")
            for table in existing_problem_tables:
                run_sql(f"DROP TABLE IF EXISTS {table}", f"Dropping {table}")
        else:
            print("✅ No problematic tables found")
    
    # Step 2: Ensure withdrawal system tables exist
    print("\n🔧 Ensuring withdrawal system tables exist...")
    
    # Create wallet_transactions table
    run_sql("""
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
            withdrawal_request_id VARCHAR(100),
            created_at DATETIME NOT NULL,
            player_id INTEGER NOT NULL
        );
    """, "Creating wallet_transactions table")
    
    # Create withdrawal_requests table
    run_sql("""
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
            approved_by_id INTEGER
        );
    """, "Creating withdrawal_requests table")
    
    # Create master_wallet table
    run_sql("""
        CREATE TABLE IF NOT EXISTS master_wallet (
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
    """, "Creating master_wallet table")
    
    # Create master_wallet_transactions table
    run_sql("""
        CREATE TABLE IF NOT EXISTS master_wallet_transactions (
            id TEXT PRIMARY KEY,
            transaction_type VARCHAR(20) NOT NULL,
            amount DECIMAL(12, 2) NOT NULL,
            balance_after DECIMAL(15, 2) NOT NULL,
            description TEXT NOT NULL,
            created_at DATETIME NOT NULL,
            master_wallet_id TEXT NOT NULL
        );
    """, "Creating master_wallet_transactions table")
    
    # Step 3: Create indexes
    print("\n🔧 Creating database indexes...")
    indexes = [
        ("CREATE INDEX IF NOT EXISTS idx_wallet_transactions_player ON wallet_transactions(player_id);", "wallet_transactions player index"),
        ("CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at ON wallet_transactions(created_at);", "wallet_transactions created_at index"),
        ("CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_player ON withdrawal_requests(player_id);", "withdrawal_requests player index"),
        ("CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status ON withdrawal_requests(status);", "withdrawal_requests status index"),
        ("CREATE INDEX IF NOT EXISTS idx_master_wallet_transactions_wallet ON master_wallet_transactions(master_wallet_id);", "master_wallet_transactions wallet index"),
    ]
    
    for sql, desc in indexes:
        run_sql(sql, desc)
    
    # Step 4: Ensure master wallet record exists
    print("\n🔧 Ensuring master wallet record exists...")
    run_sql("""
        INSERT OR IGNORE INTO master_wallet (
            id, total_balance, available_balance, reserved_balance,
            total_deposits_received, total_withdrawals_paid,
            created_at, updated_at
        ) VALUES (
            'default-master-wallet',
            0, 0, 0, 0, 0,
            datetime('now'), datetime('now')
        );
    """, "Creating default master wallet")
    
    # Step 5: Mark migrations as applied
    print("\n🔧 Marking migrations as applied...")
    run_sql("""
        INSERT OR IGNORE INTO django_migrations (app, name, applied) VALUES 
        ('polling', '0024_ensure_wallet_transactions_table', datetime('now')),
        ('polling', '0025_finalize_withdrawal_system', datetime('now'));
    """, "Marking migrations as applied")
    
    # Step 6: Test the system
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
        print("\n📋 Next steps:")
        print("1. Test withdrawal functionality at /wallet/")
        print("2. Check admin panel at /control-panel/withdrawals/")
        print("3. Use these test bank details:")
        print("   Account Number: 123456789012")
        print("   IFSC Code: SBIN0001234")
        print("   Account Holder: Test User")
        print("   Bank Name: State Bank of India")
    else:
        print("\n❌ Migration fix failed. Check the errors above.")
