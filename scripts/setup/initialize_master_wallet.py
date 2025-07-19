#!/usr/bin/env python
"""
Initialize Master Wallet for Real Money System
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.db import connection

def fix_migration_issue():
    """Fix the migration foreign key constraint issue"""
    print("🔧 Fixing migration foreign key constraint issue...")
    
    with connection.cursor() as cursor:
        # Check if master_wallet table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='master_wallet';
        """)
        
        if not cursor.fetchone():
            print("📦 Creating master_wallet table...")
            # Create master_wallet table manually
            cursor.execute("""
                CREATE TABLE "master_wallet" (
                    "id" char(32) NOT NULL PRIMARY KEY,
                    "total_balance" decimal NOT NULL,
                    "available_balance" decimal NOT NULL,
                    "reserved_balance" decimal NOT NULL,
                    "bank_account_number" varchar(50),
                    "bank_ifsc_code" varchar(20),
                    "bank_name" varchar(100),
                    "account_holder_name" varchar(100),
                    "razorpay_account_id" varchar(100),
                    "razorpay_settlement_account" varchar(100),
                    "total_deposits_received" decimal NOT NULL,
                    "total_withdrawals_paid" decimal NOT NULL,
                    "total_game_winnings_paid" decimal NOT NULL,
                    "total_game_losses_collected" decimal NOT NULL,
                    "created_at" datetime NOT NULL,
                    "updated_at" datetime NOT NULL,
                    "is_active" bool NOT NULL
                );
            """)
            
            # Insert default master wallet
            import uuid
            from django.utils import timezone
            
            master_wallet_id = str(uuid.uuid4()).replace('-', '')
            now = timezone.now().isoformat()
            
            cursor.execute("""
                INSERT INTO master_wallet (
                    id, total_balance, available_balance, reserved_balance,
                    total_deposits_received, total_withdrawals_paid,
                    total_game_winnings_paid, total_game_losses_collected,
                    created_at, updated_at, is_active
                ) VALUES (%s, 0, 0, 0, 0, 0, 0, 0, %s, %s, 1)
            """, [master_wallet_id, now, now])
            
            print(f"✅ Created master wallet with ID: {master_wallet_id}")
            
            # Update existing master_wallet_transactions to use this ID
            cursor.execute("""
                UPDATE master_wallet_transactions
                SET master_wallet_id = %s
                WHERE master_wallet_id = '00000000000000000000000000000000'
            """, [master_wallet_id])
            
            print("✅ Updated existing transactions to reference new master wallet")
        else:
            print("✅ Master wallet table already exists")

def main():
    """Initialize the master wallet system"""
    print("🚀 Initializing Master Wallet System...\n")
    
    try:
        fix_migration_issue()
        print("\n🎉 Master wallet system initialized successfully!")
        print("\n📊 Next Steps:")
        print("1. Run: python manage.py migrate")
        print("2. Configure master wallet bank details in admin panel")
        print("3. Test deposit and withdrawal flows")
        
    except Exception as e:
        print(f"\n❌ Error initializing master wallet: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
