from django.core.management.base import BaseCommand
from django.db import connection, transaction
import uuid
from django.utils import timezone


class Command(BaseCommand):
    help = 'Fix withdrawal system database issues'

    def handle(self, *args, **options):
        self.stdout.write("🔧 Fixing withdrawal system database...")
        
        with connection.cursor() as cursor:
            # Check existing tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [table[0] for table in cursor.fetchall()]
            
            self.stdout.write(f"Found {len(tables)} tables in database")
            
            # Create wallet_transactions table if missing
            if 'wallet_transactions' not in tables:
                self.stdout.write("❌ wallet_transactions table missing - creating...")
                
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
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_wallet_transactions_player ON wallet_transactions(player_id);")
                cursor.execute("CREATE INDEX idx_wallet_transactions_created_at ON wallet_transactions(created_at);")
                cursor.execute("CREATE INDEX idx_wallet_transactions_type ON wallet_transactions(transaction_type);")
                
                self.stdout.write(self.style.SUCCESS("✅ wallet_transactions table created"))
            else:
                self.stdout.write("✅ wallet_transactions table exists")
            
            # Create withdrawal_requests table if missing
            if 'withdrawal_requests' not in tables:
                self.stdout.write("❌ withdrawal_requests table missing - creating...")
                
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
                
                # Create indexes
                cursor.execute("CREATE INDEX idx_withdrawal_requests_player ON withdrawal_requests(player_id);")
                cursor.execute("CREATE INDEX idx_withdrawal_requests_status ON withdrawal_requests(status);")
                cursor.execute("CREATE INDEX idx_withdrawal_requests_created_at ON withdrawal_requests(created_at);")
                
                self.stdout.write(self.style.SUCCESS("✅ withdrawal_requests table created"))
            else:
                self.stdout.write("✅ withdrawal_requests table exists")
            
            # Create master_wallet table if missing
            if 'master_wallet' not in tables:
                self.stdout.write("❌ master_wallet table missing - creating...")
                
                cursor.execute("""
                    CREATE TABLE master_wallet (
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
                
                self.stdout.write(self.style.SUCCESS("✅ master_wallet table created"))
            else:
                self.stdout.write("✅ master_wallet table exists")
            
            # Ensure master wallet record exists
            cursor.execute("SELECT COUNT(*) FROM master_wallet;")
            master_wallet_count = cursor.fetchone()[0]
            
            if master_wallet_count == 0:
                self.stdout.write("❌ No master wallet record - creating default...")
                
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
                
                self.stdout.write(self.style.SUCCESS("✅ Default master wallet created"))
            else:
                self.stdout.write(f"✅ Master wallet exists (count: {master_wallet_count})")
        
        # Test the models
        try:
            from polling.models import WalletTransaction, WithdrawalRequest, MasterWallet
            
            # Test queries
            wallet_count = WalletTransaction.objects.count()
            withdrawal_count = WithdrawalRequest.objects.count()
            master_count = MasterWallet.objects.count()
            
            self.stdout.write(f"✅ WalletTransaction count: {wallet_count}")
            self.stdout.write(f"✅ WithdrawalRequest count: {withdrawal_count}")
            self.stdout.write(f"✅ MasterWallet count: {master_count}")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 Withdrawal system is ready!"))
            self.stdout.write("\n📋 Test with these bank details:")
            self.stdout.write("   Account Number: 123456789012")
            self.stdout.write("   IFSC Code: SBIN0001234")
            self.stdout.write("   Account Holder: Test User")
            self.stdout.write("   Bank Name: State Bank of India")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error testing models: {e}"))
