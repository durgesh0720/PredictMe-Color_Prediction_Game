import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from django.db import connection

# Check what tables exist
with connection.cursor() as cursor:
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    print("Existing tables:")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Check specifically for wallet_transactions
    table_names = [table[0] for table in tables]
    if 'wallet_transactions' in table_names:
        print("\n✅ wallet_transactions table exists")
    else:
        print("\n❌ wallet_transactions table missing")
        
        # Create it manually
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
                created_at DATETIME NOT NULL,
                player_id INTEGER NOT NULL
            );
        """)
        print("✅ wallet_transactions table created")
