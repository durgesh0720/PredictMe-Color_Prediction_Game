# models.py

from django.db import models
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.core.validators import EmailValidator, RegexValidator
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import timedelta
import random
import string
import uuid
from decimal import Decimal

class Player(models.Model):
    # Basic Information
    username = models.CharField(max_length=50, unique=True, db_index=True)
    email = models.EmailField(unique=True, validators=[EmailValidator()], null=True, blank=True)
    email_verified = models.BooleanField(default=False, db_index=True)
    password_hash = models.CharField(max_length=255, null=True, blank=True)

    # Profile Information
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    phone_validator = RegexValidator(
        regex=r'^\+?1?\d{9,15}$',
        message="Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed."
    )
    phone_number = models.CharField(validators=[phone_validator], max_length=17, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)

    # Game Statistics
    score = models.IntegerField(default=0, db_index=True)
    balance = models.IntegerField(default=0)  # Zero starting balance - users must deposit real money
    total_bets = models.IntegerField(default=0)
    total_wins = models.IntegerField(default=0)

    # Account Status
    is_active = models.BooleanField(default=True, db_index=True)
    is_verified = models.BooleanField(default=False)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.username

    def set_password(self, password):
        """Set password with validation and hashing"""
        try:
            validate_password(password, self)
            self.password_hash = make_password(password)
        except ValidationError as e:
            raise ValidationError(f"Password validation failed: {', '.join(e.messages)}")

    def check_password(self, password):
        """Check if provided password matches"""
        return check_password(password, self.password_hash)

    @property
    def full_name(self):
        """Return full name"""
        return f"{self.first_name} {self.last_name}".strip()

    @property
    def win_rate(self):
        if self.total_bets == 0:
            return 0
        return round((self.total_wins / self.total_bets) * 100, 2)

    @property
    def display_name(self):
        """Return display name (full name if available, otherwise username)"""
        return self.full_name if self.full_name else self.username

    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = timezone.now()
        self.save(update_fields=['last_login'])

    def debit_wallet(self, amount, transaction_type, description="", admin=None, bet=None):
        """
        Debit amount from wallet with transaction logging
        Returns True if successful, False if insufficient balance
        """
        from django.db import transaction as db_transaction

        if amount <= 0:
            raise ValueError("Debit amount must be positive")

        with db_transaction.atomic():
            # Refresh from database to get latest balance
            self.refresh_from_db()

            if self.balance < amount:
                return False

            balance_before = self.balance
            self.balance -= amount
            self.save()

            # Create transaction record
            Transaction.objects.create(
                player=self,
                transaction_type=transaction_type,
                amount=-amount,  # Negative for debit
                balance_before=balance_before,
                balance_after=self.balance,
                description=description,
                admin=admin,
                bet=bet
            )

        # Send notification outside atomic block (except for bet transactions)
        if transaction_type not in ['bet']:
            try:
                from .notification_service import notify_wallet_transaction
                notify_wallet_transaction(self, transaction_type, amount, self.balance)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending wallet notification: {e}")

        return True

    def credit_wallet(self, amount, transaction_type, description="", admin=None, bet=None, involves_real_money=True, payment_transaction_id=None):
        """
        Credit amount to wallet with transaction logging and real money tracking
        """
        from django.db import transaction as db_transaction

        if amount <= 0:
            raise ValueError("Credit amount must be positive")

        with db_transaction.atomic():
            # Refresh from database to get latest balance
            self.refresh_from_db()

            balance_before = self.balance
            self.balance += amount
            self.save()

            # Create legacy transaction record for backward compatibility
            Transaction.objects.create(
                player=self,
                transaction_type=transaction_type,
                amount=amount,  # Positive for credit
                balance_before=balance_before,
                balance_after=self.balance,
                description=description,
                admin=admin,
                bet=bet
            )

            # Create enhanced wallet transaction record (if table exists)
            try:
                # Check if WalletTransaction table exists before using it
                from django.db import connection
                table_names = connection.introspection.table_names()

                if 'wallet_transactions' in table_names:
                    wallet_transaction = WalletTransaction.objects.create(
                        player=self,
                        transaction_type=transaction_type,
                        amount=amount,
                        balance_before=balance_before,
                        balance_after=self.balance,
                        description=description,
                        involves_real_money=involves_real_money,
                        payment_transaction_id=payment_transaction_id
                    )

                    # If this involves real money and is a deposit, credit master wallet
                    if involves_real_money and transaction_type == 'deposit':
                        master_wallet = MasterWallet.objects.first()
                        if master_wallet:
                            master_wallet.credit_deposit(
                                amount=amount,
                                description=f'Deposit from {self.username} - {description}'
                            )
                            # Update wallet transaction with master wallet reference
                            latest_master_txn = master_wallet.transactions.first()
                            if latest_master_txn:
                                wallet_transaction.master_wallet_transaction_id = str(latest_master_txn.id)
                                wallet_transaction.save()
                else:
                    # If WalletTransaction table doesn't exist, just handle master wallet
                    if involves_real_money and transaction_type == 'deposit':
                        try:
                            # Check if MasterWallet table exists
                            if 'master_wallet_transactions' in table_names:
                                master_wallet = MasterWallet.objects.first()
                                if master_wallet:
                                    master_wallet.credit_deposit(
                                        amount=amount,
                                        description=f'Deposit from {self.username} - {description}'
                                    )
                            else:
                                # Skip master wallet if table doesn't exist
                                import logging
                                logger = logging.getLogger(__name__)
                                logger.debug(f"Master wallet table not found, skipping master wallet credit")
                        except Exception as master_e:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.error(f"Error crediting master wallet: {master_e}")

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error creating wallet transaction: {e}")
                # Continue execution even if wallet transaction fails

        # Send notification outside atomic block (except for win transactions, handled separately)
        if transaction_type not in ['win']:
            try:
                from .notification_service import notify_wallet_transaction
                notify_wallet_transaction(self, transaction_type, amount, self.balance)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending wallet notification: {e}")

        return True

    def request_withdrawal(self, amount, bank_account_number, bank_ifsc_code, bank_name, account_holder_name):
        """
        Request withdrawal - debit from user wallet and create withdrawal request
        """
        from django.db import transaction as db_transaction


        if amount <= 0:
            raise ValueError("Withdrawal amount must be positive")

        if self.balance < amount:
            raise ValueError("Insufficient balance")

        with db_transaction.atomic():
            # Refresh from database to get latest balance
            self.refresh_from_db()

            if self.balance < amount:
                raise ValueError("Insufficient balance")

            balance_before = self.balance
            self.balance -= amount
            self.save()

            # Create withdrawal request (with error handling for missing table)
            try:
                withdrawal_request = WithdrawalRequest.objects.create(
                    player=self,
                    amount=amount,
                    bank_account_number=bank_account_number,
                    bank_ifsc_code=bank_ifsc_code,
                    bank_name=bank_name,
                    account_holder_name=account_holder_name,
                    status='pending'
                )
            except Exception as e:
                # If withdrawal_requests table doesn't exist, create it and try again
                from django.db import connection
                import uuid
                from django.utils import timezone

                with connection.cursor() as cursor:
                    # Create withdrawal_requests table if it doesn't exist
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
                            approved_by_id INTEGER
                        );
                    """)

                    # Create indexes for performance
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_player ON withdrawal_requests(player_id);")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_status ON withdrawal_requests(status);")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_withdrawal_requests_created_at ON withdrawal_requests(created_at);")

                # Try creating the withdrawal request again
                withdrawal_request = WithdrawalRequest.objects.create(
                    player=self,
                    amount=amount,
                    bank_account_number=bank_account_number,
                    bank_ifsc_code=bank_ifsc_code,
                    bank_name=bank_name,
                    account_holder_name=account_holder_name,
                    status='pending'
                )

            # Create wallet transaction record (with error handling for missing table)
            try:
                WalletTransaction.objects.create(
                    player=self,
                    transaction_type='withdrawal',
                    amount=amount,
                    balance_before=balance_before,
                    balance_after=self.balance,
                    description=f'Withdrawal request to {bank_name} - {bank_account_number[-4:]}',
                    involves_real_money=True,
                    withdrawal_request_id=str(withdrawal_request.id)
                )
            except Exception as e:
                # If wallet_transactions table doesn't exist, create it and try again
                from django.db import connection
                import uuid
                from django.utils import timezone

                with connection.cursor() as cursor:
                    # Create wallet_transactions table if it doesn't exist
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
                            withdrawal_request_id VARCHAR(100),
                            created_at DATETIME NOT NULL,
                            player_id INTEGER NOT NULL
                        );
                    """)

                    # Create indexes for performance
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet_transactions_player ON wallet_transactions(player_id);")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet_transactions_created_at ON wallet_transactions(created_at);")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallet_transactions_type ON wallet_transactions(transaction_type);")

                # Try creating the wallet transaction again
                try:
                    WalletTransaction.objects.create(
                        player=self,
                        transaction_type='withdrawal',
                        amount=amount,
                        balance_before=balance_before,
                        balance_after=self.balance,
                        description=f'Withdrawal request to {bank_name} - {bank_account_number[-4:]}',
                        involves_real_money=True,
                        withdrawal_request_id=str(withdrawal_request.id)
                    )
                except Exception as e2:
                    # If it still fails, log the error but don't break the withdrawal process
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.error(f"Failed to create wallet transaction after table creation: {e2}")

            # Create legacy transaction record
            Transaction.objects.create(
                player=self,
                transaction_type='withdrawal',
                amount=-amount,  # Negative for debit
                balance_before=balance_before,
                balance_after=self.balance,
                description=f'Withdrawal request - ₹{amount}'
            )

            # Send notification
            try:
                from .notification_service import notify_wallet_transaction
                notify_wallet_transaction(self, 'withdrawal', amount, self.balance)
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error sending withdrawal notification: {e}")

            return withdrawal_request

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['score']),
            models.Index(fields=['created_at']),
            models.Index(fields=['is_active', 'created_at']),
            models.Index(fields=['balance']),
            models.Index(fields=['total_bets', 'total_wins']),
        ]

class GameRound(models.Model):
    room = models.CharField(max_length=50, db_index=True)
    start_time = models.DateTimeField(default=timezone.now, db_index=True)
    result_color = models.CharField(max_length=10, blank=True, null=True)
    result_number = models.IntegerField(blank=True, null=True)  # 0-9
    period_id = models.CharField(max_length=20, blank=True, db_index=True)
    game_type = models.CharField(max_length=20, default='parity', db_index=True)  # parity, sapre, bcone, noki
    ended = models.BooleanField(default=False, db_index=True)

    def save(self, *args, **kwargs):
        if not self.period_id:
            # Generate period ID based on timestamp
            timestamp = self.start_time.strftime('%Y%m%d%H%M')
            self.period_id = timestamp
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Room: {self.room} | Period: {self.period_id} | Type: {self.game_type}"

    @property
    def result_color_from_number(self):
        """Determine color based on the result number"""
        if self.result_number is None:
            return None

        if self.result_number in [1, 3, 7, 9]:
            return 'green'
        elif self.result_number in [2, 4, 6, 8]:
            return 'red'
        elif self.result_number in [0, 5]:
            return 'violet'

        return None

    class Meta:
        ordering = ['-start_time']
        indexes = [
            models.Index(fields=['room', 'ended']),
            models.Index(fields=['game_type', 'ended']),
            models.Index(fields=['start_time']),
            models.Index(fields=['period_id']),
            models.Index(fields=['ended', 'start_time']),
            models.Index(fields=['game_type', 'ended', 'start_time']),
        ]

class Bet(models.Model):
    BET_TYPES = [
        ('color', 'Color'),
        ('number', 'Number'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE, db_index=True)
    round = models.ForeignKey(GameRound, on_delete=models.CASCADE, db_index=True)
    bet_type = models.CharField(max_length=10, choices=BET_TYPES, default='color', db_index=True)
    color = models.CharField(max_length=10, blank=True, null=True, db_index=True)
    number = models.IntegerField(blank=True, null=True)  # 0-9
    amount = models.IntegerField(default=0)
    correct = models.BooleanField(default=False, db_index=True)
    payout = models.IntegerField(default=0)  # Amount won
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    def __str__(self):
        bet_on = self.color if self.bet_type == 'color' else self.number
        return f"{self.player.username} bet {self.amount} on {bet_on} ({self.bet_type})"

    def check_win(self, result_number, result_color):
        """Check if this bet won based on the round result"""
        if self.bet_type == 'color':
            self.correct = (self.color == result_color)
            if self.correct:
                # Color bets have 2.5x payout for all colors
                multiplier = 2.5
                self.payout = int(self.amount * multiplier)
        elif self.bet_type == 'number':
            self.correct = (self.number == result_number)
            if self.correct:
                # Number bets have 9x payout
                self.payout = self.amount * 9

        self.save()
        return self.correct

    class Meta:
        ordering = ['-created_at']
        unique_together = [('player', 'round')]  # One bet per player per round
        indexes = [
            models.Index(fields=['player', 'created_at']),
            models.Index(fields=['round', 'player']),
            models.Index(fields=['bet_type', 'color']),
            models.Index(fields=['correct', 'created_at']),
            models.Index(fields=['player', 'correct']),
            models.Index(fields=['round', 'bet_type']),
            models.Index(fields=['player', 'round'], name='unique_player_round_idx'),  # Enforce uniqueness with index
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['player', 'round'],
                name='unique_player_round_bet',
                violation_error_message='You can only place one bet per round.'
            )
        ]


class Admin(models.Model):
    """Admin user model for game management"""
    username = models.CharField(max_length=50, unique=True)
    password_hash = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    balance = models.IntegerField(default=0)  # Master wallet balance
    created_at = models.DateTimeField(auto_now_add=True)
    last_login = models.DateTimeField(null=True, blank=True)

    def set_password(self, password):
        """Set password with hashing"""
        self.password_hash = make_password(password)

    def check_password(self, password):
        """Check if provided password matches"""
        return check_password(password, self.password_hash)

    def credit_master_wallet(self, amount, description="", bet=None):
        """
        Credit amount to master wallet with transaction logging
        """
        from django.db import transaction as db_transaction

        if amount <= 0:
            raise ValueError("Credit amount must be positive")

        with db_transaction.atomic():
            # Refresh from database to get latest balance
            self.refresh_from_db()

            balance_before = self.balance
            self.balance += amount
            self.save()

            # Create master wallet transaction record
            master_wallet = MasterWallet.objects.first()
            if master_wallet:
                MasterWalletTransaction.objects.create(
                    master_wallet=master_wallet,
                    transaction_type='credit',
                    amount=amount,
                    balance_after=master_wallet.available_balance,
                    description=description
                )

            return True

    def debit_master_wallet(self, amount, description="", bet=None):
        """
        Debit amount from master wallet with transaction logging
        Returns True if successful, False if insufficient balance
        """
        from django.db import transaction as db_transaction

        if amount <= 0:
            raise ValueError("Debit amount must be positive")

        with db_transaction.atomic():
            # Refresh from database to get latest balance
            self.refresh_from_db()

            if self.balance < amount:
                return False

            balance_before = self.balance
            self.balance -= amount
            self.save()

            # Create master wallet transaction record
            master_wallet = MasterWallet.objects.first()
            if master_wallet:
                MasterWalletTransaction.objects.create(
                    master_wallet=master_wallet,
                    transaction_type='debit',
                    amount=amount,
                    balance_after=master_wallet.available_balance,
                    description=description
                )

            return True

    def __str__(self):
        return self.username


class GameControl(models.Model):
    """Model to control game settings and manual results"""
    game_type = models.CharField(max_length=20, default='parity')
    is_active = models.BooleanField(default=True)
    auto_result = models.BooleanField(default=True)  # Auto generate results or manual
    manual_result_number = models.IntegerField(null=True, blank=True)  # For manual control
    manual_result_color = models.CharField(max_length=10, null=True, blank=True)  # Admin selected color
    round_duration = models.IntegerField(default=180)  # Duration in seconds
    betting_duration = models.IntegerField(default=150)  # Betting allowed duration
    admin_control_interval = models.IntegerField(default=10)  # Admin selection interval in seconds
    use_minimum_selection = models.BooleanField(default=True)  # Use minimum selected color as default
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['game_type']

    def __str__(self):
        return f"Control for {self.game_type} - {'Active' if self.is_active else 'Inactive'}"


class AdminColorSelection(models.Model):
    """Model to track admin color selections for each round"""
    round = models.OneToOneField(GameRound, on_delete=models.CASCADE)
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, null=True, blank=True)
    selected_color = models.CharField(max_length=10, null=True, blank=True)  # green, red, violet
    selection_time = models.DateTimeField(auto_now_add=True)
    is_auto_selected = models.BooleanField(default=False)  # True if auto-selected (minimum bets)
    verification_hash = models.CharField(max_length=64, null=True, blank=True)  # For audit trail

    def __str__(self):
        return f"Round {self.round.period_id} - {self.selected_color} ({'Auto' if self.is_auto_selected else 'Manual'})"


class Transaction(models.Model):
    """Model to track all financial transactions"""
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('bet', 'Bet Placed'),
        ('win', 'Bet Won'),
        ('admin_adjust', 'Admin Adjustment'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.IntegerField()  # Positive for credits, negative for debits
    balance_before = models.IntegerField()
    balance_after = models.IntegerField()
    description = models.TextField(blank=True)
    admin = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True)
    bet = models.ForeignKey('Bet', on_delete=models.SET_NULL, null=True, blank=True)  # Link to bet if applicable
    payment_transaction = models.ForeignKey('PaymentTransaction', on_delete=models.SET_NULL, null=True, blank=True)  # Link to payment gateway transaction
    created_at = models.DateTimeField(auto_now_add=True)

    # Security and audit fields
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    is_verified = models.BooleanField(default=True)  # For transactions requiring verification
    verification_code = models.CharField(max_length=50, blank=True)  # For transaction verification

    def __str__(self):
        return f"{self.player.username} - {self.transaction_type}: {self.amount}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['player', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
            models.Index(fields=['player', 'transaction_type']),
            models.Index(fields=['bet', 'transaction_type']),
            models.Index(fields=['payment_transaction']),
            models.Index(fields=['is_verified', 'created_at']),
        ]


class MasterWalletTransaction(models.Model):
    """Model to track master wallet transactions"""
    TRANSACTION_TYPES = [
        ('credit', 'Credit'),
        ('debit', 'Debit'),
        ('reserve', 'Reserve'),
        ('release', 'Release'),
    ]

    master_wallet = models.ForeignKey('MasterWallet', on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    balance_after = models.DecimalField(max_digits=15, decimal_places=2)
    description = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"Master Wallet - {self.transaction_type}: {self.amount}"

    class Meta:
        db_table = 'master_wallet_transactions'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['master_wallet', 'created_at']),
            models.Index(fields=['transaction_type', 'created_at']),
        ]


class PaymentTransaction(models.Model):
    """Model to track payment gateway transactions"""
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('canceled', 'Canceled'),
        ('processing', 'Processing'),
    ]

    player = models.ForeignKey(Player, on_delete=models.CASCADE)
    razorpay_order_id = models.CharField(max_length=255, unique=True, null=True, blank=True)  # Razorpay Order ID
    razorpay_payment_id = models.CharField(max_length=255, null=True, blank=True)  # Razorpay Payment ID
    razorpay_signature = models.CharField(max_length=255, null=True, blank=True)  # Razorpay Signature for verification
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # Use decimal for precise money handling
    currency = models.CharField(max_length=3, default='INR')  # Default to INR for Razorpay
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    error_message = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    bank_account_info = models.TextField(blank=True)  # JSON string for withdrawal bank details
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Security and audit fields
    user_agent = models.TextField(blank=True)
    fraud_score = models.IntegerField(default=0)  # 0-100 fraud risk score
    is_flagged = models.BooleanField(default=False)
    admin_notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.player.username} - {self.transaction_type}: ${self.amount} ({self.status})"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['player', 'created_at']),
            models.Index(fields=['transaction_type', 'status']),
            models.Index(fields=['razorpay_order_id']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['player', 'transaction_type', 'status']),
        ]


class AdminLog(models.Model):
    """Log admin actions for audit trail"""
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.admin.username} - {self.action}"

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['admin', 'created_at']),
            models.Index(fields=['action', 'created_at']),
        ]


# Removed unnecessary gamification models:
# - Achievement: Not used in current simple UI design
# - PlayerAchievement: Not used in current simple UI design
# - DailyBonus: Not used in current simple UI design
# - PlayerStats: Not used in current simple UI design
# These models added complexity without being utilized in the current implementation


class OTPVerification(models.Model):
    """
    Model to store OTP verification codes for email verification
    """
    email = models.EmailField(db_index=True)
    otp_code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    attempts = models.IntegerField(default=0)
    max_attempts = models.IntegerField(default=3)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'created_at']),
            models.Index(fields=['otp_code', 'expires_at']),
        ]

    def save(self, *args, **kwargs):
        if not self.expires_at:
            # OTP expires in 10 minutes
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)

    def is_expired(self):
        """Check if OTP has expired"""
        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if OTP is valid (not expired, not used, attempts not exceeded)"""
        return not self.is_expired() and not self.is_used and self.attempts < self.max_attempts

    def increment_attempts(self):
        """Increment the number of verification attempts"""
        self.attempts += 1
        self.save()

    def mark_as_used(self):
        """Mark OTP as used"""
        self.is_used = True
        self.save()

    @classmethod
    def generate_otp(cls, email):
        """Generate a new 6-digit OTP for the given email"""
        # Invalidate any existing OTPs for this email
        cls.objects.filter(email=email, is_used=False).update(is_used=True)

        # Generate new 6-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=6))

        # Create new OTP record
        otp = cls.objects.create(
            email=email,
            otp_code=otp_code
        )

        return otp

    @classmethod
    def verify_otp(cls, email, otp_code):
        """Verify OTP code for the given email"""
        try:
            otp = cls.objects.get(
                email=email,
                otp_code=otp_code,
                is_used=False
            )

            if not otp.is_valid():
                return False, "OTP has expired or maximum attempts exceeded"

            otp.mark_as_used()
            return True, "OTP verified successfully"

        except cls.DoesNotExist:
            return False, "Invalid OTP code"

    def __str__(self):
        return f"OTP for {self.email} - {self.otp_code} ({'Used' if self.is_used else 'Active'})"


class NotificationType(models.Model):
    """
    Model to define different types of notifications
    """
    CATEGORY_CHOICES = [
        ('game', 'Game Events'),
        ('wallet', 'Wallet & Transactions'),
        ('account', 'Account Activities'),
        ('system', 'System Announcements'),
        ('security', 'Security Alerts'),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    default_enabled = models.BooleanField(default=True)  # Default preference for new users

    # Delivery method defaults
    email_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return f"{self.get_category_display()} - {self.name}"


class UserNotificationPreference(models.Model):
    """
    Model to store user preferences for different notification types
    """
    DELIVERY_CHOICES = [
        ('email', 'Email'),
        ('in_app', 'In-App'),
        ('both', 'Both'),
        ('none', 'None'),
    ]

    user = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='notification_preferences')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)
    delivery_method = models.CharField(max_length=10, choices=DELIVERY_CHOICES, default='both')
    is_enabled = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'notification_type']
        indexes = [
            models.Index(fields=['user', 'is_enabled']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.notification_type.name} - {self.delivery_method}"


class Notification(models.Model):
    """
    Model to store individual notifications sent to users
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
    ]

    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]

    user = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.ForeignKey(NotificationType, on_delete=models.CASCADE)

    title = models.CharField(max_length=200)
    message = models.TextField()
    html_message = models.TextField(blank=True)  # For rich HTML content

    # Metadata
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='normal')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    # Delivery tracking
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    in_app_delivered = models.BooleanField(default=False)
    in_app_delivered_at = models.DateTimeField(null=True, blank=True)

    # User interaction
    read_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)

    # Additional data (JSON field for flexible data storage)
    extra_data = models.JSONField(default=dict, blank=True)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True)  # For temporary notifications

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', 'created_at']),
            models.Index(fields=['notification_type', 'status']),
            models.Index(fields=['priority', 'created_at']),
            models.Index(fields=['expires_at']),
        ]

    def mark_as_read(self):
        """Mark notification as read"""
        if not self.read_at:
            self.read_at = timezone.now()
            self.status = 'read'
            self.save(update_fields=['read_at', 'status', 'updated_at'])

    def mark_as_clicked(self):
        """Mark notification as clicked"""
        if not self.clicked_at:
            self.clicked_at = timezone.now()
            self.save(update_fields=['clicked_at', 'updated_at'])
        if not self.read_at:
            self.mark_as_read()

    def is_expired(self):
        """Check if notification has expired"""
        return self.expires_at and timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.user.username} - {self.title} ({self.status})"


# Real Money Wallet System Models

class MasterWallet(models.Model):
    """
    Master wallet that holds all platform money
    Like the main account of betting company
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Balance tracking
    total_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    available_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    reserved_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)  # For pending withdrawals

    # Bank account details
    bank_account_number = models.CharField(max_length=50, null=True, blank=True)
    bank_ifsc_code = models.CharField(max_length=20, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    account_holder_name = models.CharField(max_length=100, null=True, blank=True)

    # Razorpay integration
    razorpay_account_id = models.CharField(max_length=100, null=True, blank=True)
    razorpay_settlement_account = models.CharField(max_length=100, null=True, blank=True)

    # Statistics
    total_deposits_received = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_withdrawals_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_game_winnings_paid = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    total_game_losses_collected = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    # Metadata
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'master_wallet'

    def __str__(self):
        return f"Master Wallet - Balance: ₹{self.available_balance}"

    def credit_deposit(self, amount, description="Deposit received"):
        """Credit money from user deposit"""
        self.total_balance += amount
        self.available_balance += amount
        self.total_deposits_received += amount
        self.save()

        # Create transaction record
        MasterWalletTransaction.objects.create(
            master_wallet=self,
            transaction_type='credit',
            amount=amount,
            description=description,
            balance_after=self.available_balance
        )

    def debit_withdrawal(self, amount, description="Withdrawal paid"):
        """Debit money for user withdrawal"""
        if self.available_balance >= amount:
            self.total_balance -= amount
            self.available_balance -= amount
            self.total_withdrawals_paid += amount
            self.save()

            # Create transaction record
            MasterWalletTransaction.objects.create(
                master_wallet=self,
                transaction_type='debit',
                amount=amount,
                balance_after=self.available_balance,
                description=description
            )
            return True
        return False

    def reserve_for_withdrawal(self, amount):
        """Reserve money for pending withdrawal"""
        if self.available_balance >= amount:
            self.available_balance -= amount
            self.reserved_balance += amount
            self.save()
            return True
        return False

    def release_reserved_amount(self, amount):
        """Release reserved money (withdrawal cancelled)"""
        self.available_balance += amount
        self.reserved_balance -= amount
        self.save()


# Duplicate MasterWalletTransaction model removed - using the one defined earlier at line 571


class WithdrawalRequest(models.Model):
    """
    User withdrawal requests that need admin approval
    """
    STATUS_CHOICES = [
        ('pending', 'Pending Admin Approval'),
        ('approved', 'Approved by Admin'),
        ('processing', 'Processing Payment'),
        ('completed', 'Payment Completed'),
        ('rejected', 'Rejected by Admin'),
        ('failed', 'Payment Failed'),
        ('cancelled', 'Cancelled by User'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User details
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='withdrawal_requests')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('20'))])

    # Bank details
    bank_account_number = models.CharField(max_length=50)
    bank_ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    account_holder_name = models.CharField(max_length=100)

    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    admin_notes = models.TextField(null=True, blank=True)
    rejection_reason = models.TextField(null=True, blank=True)

    # Admin approval
    approved_by = models.ForeignKey(Admin, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_withdrawals')
    approved_at = models.DateTimeField(null=True, blank=True)

    # Payment processing
    payment_reference = models.CharField(max_length=100, null=True, blank=True)  # Bank transfer reference
    payment_gateway_response = models.JSONField(null=True, blank=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'withdrawal_requests'
        ordering = ['-created_at']

    def __str__(self):
        return f"Withdrawal ₹{self.amount} - {self.player.username} - {self.status}"

    def approve(self, admin, notes=""):
        """Admin approves withdrawal"""
        if self.status == 'pending':
            self.status = 'approved'
            self.approved_by = admin
            self.approved_at = timezone.now()
            self.admin_notes = notes
            self.save()

            # Reserve money in master wallet
            master_wallet = MasterWallet.objects.first()
            if master_wallet and master_wallet.reserve_for_withdrawal(self.amount):
                return True
            else:
                # Revert approval if insufficient funds and restore player balance
                self.status = 'pending'
                self.approved_by = None
                self.approved_at = None
                self.save()

                # Restore player balance since withdrawal can't be processed
                self.player.credit_wallet(
                    amount=self.amount,
                    transaction_type='withdrawal_reversal',
                    description=f'Withdrawal reversal - insufficient master wallet funds for request {self.id}'
                )
                return False
        return False

    def reject(self, admin, reason):
        """Admin rejects withdrawal"""
        if self.status == 'pending':
            self.status = 'rejected'
            self.approved_by = admin
            self.approved_at = timezone.now()
            self.rejection_reason = reason
            self.save()

            # Refund to user wallet
            self.player.credit_wallet(
                amount=self.amount,
                transaction_type='refund',
                description=f'Withdrawal rejection refund - {reason}',
                involves_real_money=False
            )
            return True
        return False

    def approve_with_razorpay(self, admin, notes=""):
        """Admin approves withdrawal with Razorpay integration"""
        if self.status != 'pending':
            return False, "Withdrawal is not in pending status"

        try:
            import razorpay
            from django.conf import settings

            # Check if Razorpay is properly configured
            if not all([
                getattr(settings, 'RAZORPAY_KEY_ID', ''),
                getattr(settings, 'RAZORPAY_KEY_SECRET', ''),
                getattr(settings, 'RAZORPAY_ACCOUNT_NUMBER', '')
            ]):
                return False, "Razorpay configuration incomplete. Missing KEY_ID, KEY_SECRET, or ACCOUNT_NUMBER."

            # Initialize Razorpay client
            razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

            # For production betting platform, use secure manual approval with proper accounting
            # This ensures compliance and security for real money transfers

            # Approve withdrawal in system
            self.status = 'approved'
            self.approved_by = admin
            self.approved_at = timezone.now()
            self.admin_notes = f"{notes}. Approved for manual bank transfer."
            self.save()

            # Debit from master wallet (accounting - money is committed for transfer)
            master_wallet = MasterWallet.objects.first()
            if master_wallet:
                master_wallet.debit_withdrawal(
                    amount=self.amount,
                    description=f"Withdrawal approved for {self.player.username} - Manual transfer required"
                )

            # Generate transfer reference for tracking
            transfer_ref = f"TXN{self.id.hex[:8].upper()}"
            self.payment_reference = transfer_ref
            self.save()

            return True, f"Withdrawal approved for manual processing. Transfer ₹{self.amount} to {self.account_holder_name} - {self.bank_name} (****{self.bank_account_number[-4:]}). Reference: {transfer_ref}"



        except Exception as e:
            # Log the error and keep withdrawal as pending
            self.admin_notes = f"Razorpay error: {str(e)}"
            self.save()
            return False, f"Razorpay error: {str(e)}"

    def complete_payment(self, payment_reference, gateway_response=None):
        """Mark payment as completed"""
        if self.status in ['approved', 'processing']:
            self.status = 'completed'
            self.payment_reference = payment_reference
            self.payment_gateway_response = gateway_response
            self.processed_at = timezone.now()
            self.save()
            return True
        return False

    def mark_transfer_completed(self, admin, bank_reference="", notes=""):
        """Mark manual bank transfer as completed"""
        if self.status == 'approved':
            self.status = 'completed'
            self.processed_at = timezone.now()
            self.admin_notes = f"{self.admin_notes}\nTransfer completed by {admin.username}. Bank Reference: {bank_reference}. Notes: {notes}"
            self.save()
            return True
        return False

    def check_payout_status(self):
        """Check the status of Razorpay payout"""
        if not self.payment_reference:
            return False, "No payment reference found"

        try:
            import razorpay
            from django.conf import settings

            razorpay_client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
            payout = razorpay_client.payout.fetch(self.payment_reference)

            # Update status based on Razorpay response
            if payout['status'] == 'processed':
                self.status = 'completed'
                self.processed_at = timezone.now()
                self.save()
                return True, "Payout completed successfully"
            elif payout['status'] == 'failed':
                self.status = 'failed'
                self.save()
                # Refund to user wallet
                self.player.credit_wallet(
                    amount=self.amount,
                    transaction_type='refund',
                    description=f'Withdrawal failed - refund',
                    involves_real_money=False
                )
                return False, "Payout failed, amount refunded to wallet"
            else:
                return True, f"Payout status: {payout['status']}"

        except Exception as e:
            return False, f"Error checking payout status: {str(e)}"

    def handle_payout_webhook(self, webhook_data):
        """Handle Razorpay payout webhook"""
        try:
            payout_id = webhook_data.get('payload', {}).get('payout', {}).get('entity', {}).get('id')
            if payout_id != self.payment_reference:
                return False, "Payout ID mismatch"

            status = webhook_data.get('payload', {}).get('payout', {}).get('entity', {}).get('status')

            if status == 'processed':
                self.status = 'completed'
                self.processed_at = timezone.now()
                self.save()
                return True, "Withdrawal completed via webhook"
            elif status == 'failed':
                self.status = 'failed'
                self.save()
                # Refund to user wallet
                self.player.credit_wallet(
                    amount=self.amount,
                    transaction_type='refund',
                    description=f'Withdrawal failed - refund',
                    involves_real_money=False
                )
                return True, "Withdrawal failed, amount refunded"

            return True, f"Webhook processed, status: {status}"

        except Exception as e:
            return False, f"Error processing webhook: {str(e)}"


class BankAccount(models.Model):
    """
    User bank accounts for withdrawals
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='bank_accounts')

    account_number = models.CharField(max_length=50)
    ifsc_code = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)
    account_holder_name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=20, choices=[('savings', 'Savings'), ('current', 'Current')], default='savings')

    # Verification
    is_verified = models.BooleanField(default=False)
    verification_method = models.CharField(max_length=50, null=True, blank=True)  # penny_drop, manual, etc.
    verified_at = models.DateTimeField(null=True, blank=True)

    # Usage tracking
    is_primary = models.BooleanField(default=False)
    last_used_at = models.DateTimeField(null=True, blank=True)
    total_withdrawals = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_bank_accounts'
        unique_together = ['player', 'account_number']

    def __str__(self):
        return f"{self.account_holder_name} - {self.account_number[-4:]}"


class WalletTransaction(models.Model):
    """
    Enhanced wallet transactions with real money tracking
    """
    TRANSACTION_TYPES = [
        ('deposit', 'Deposit'),
        ('withdrawal', 'Withdrawal'),
        ('bet_placed', 'Bet Placed'),
        ('bet_won', 'Bet Won'),
        ('bet_lost', 'Bet Lost'),
        ('refund', 'Refund'),
        ('bonus', 'Bonus'),
        ('penalty', 'Penalty'),
        ('transfer_in', 'Transfer In'),
        ('transfer_out', 'Transfer Out'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    player = models.ForeignKey(Player, on_delete=models.CASCADE, related_name='wallet_transactions')

    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()

    # References
    payment_transaction_id = models.CharField(max_length=100, null=True, blank=True)
    withdrawal_request_id = models.CharField(max_length=100, null=True, blank=True)
    bet_id = models.CharField(max_length=100, null=True, blank=True)

    # Real money tracking
    involves_real_money = models.BooleanField(default=True)  # False for bonuses, penalties
    master_wallet_transaction_id = models.CharField(max_length=100, null=True, blank=True)

    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'wallet_transactions'
        ordering = ['-created_at']