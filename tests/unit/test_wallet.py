"""
Test cases for the wallet system
"""
from django.test import TestCase
from django.utils import timezone
from .models import Player, GameRound, Bet, Transaction, Admin, MasterWalletTransaction
from .wallet_utils import (
    place_bet_with_wallet, process_bet_result, validate_bet_amount,
    get_wallet_balance, admin_adjust_wallet, get_betting_statistics,
    process_bet_result_with_master_wallet, transfer_to_master_wallet,
    get_master_wallet_balance, get_master_wallet_statistics
)


class WalletSystemTest(TestCase):
    """Test cases for wallet system functionality"""
    
    def setUp(self):
        """Set up test data"""
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000
        )
        
        self.admin = Admin.objects.create(
            username='admin',
            password_hash='hashed_password'
        )
        
        self.game_round = GameRound.objects.create(
            room='test_room',
            period_id='TEST001',
            start_time=timezone.now()
        )
    
    def test_debit_wallet_success(self):
        """Test successful wallet debit"""
        initial_balance = self.player.balance
        amount = 100
        
        success = self.player.debit_wallet(
            amount=amount,
            transaction_type='bet',
            description='Test bet'
        )
        
        self.assertTrue(success)
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance - amount)
        
        # Check transaction record
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='bet'
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, -amount)
        self.assertEqual(transaction.balance_before, initial_balance)
        self.assertEqual(transaction.balance_after, initial_balance - amount)
    
    def test_debit_wallet_insufficient_balance(self):
        """Test wallet debit with insufficient balance"""
        amount = 1500  # More than player's balance
        
        success = self.player.debit_wallet(
            amount=amount,
            transaction_type='bet',
            description='Test bet'
        )
        
        self.assertFalse(success)
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 1000)  # Balance unchanged
        
        # No transaction should be created
        transaction_count = Transaction.objects.filter(
            player=self.player,
            transaction_type='bet'
        ).count()
        
        self.assertEqual(transaction_count, 0)
    
    def test_credit_wallet(self):
        """Test wallet credit"""
        initial_balance = self.player.balance
        amount = 250
        
        success = self.player.credit_wallet(
            amount=amount,
            transaction_type='win',
            description='Test win'
        )
        
        self.assertTrue(success)
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance + amount)
        
        # Check transaction record
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='win'
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.balance_before, initial_balance)
        self.assertEqual(transaction.balance_after, initial_balance + amount)
    
    def test_place_bet_with_wallet_success(self):
        """Test successful bet placement with wallet"""
        initial_balance = self.player.balance
        amount = 100
        
        success, bet, error = place_bet_with_wallet(
            self.player, self.game_round, 'color', 'red', None, amount
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(bet)
        self.assertIsNone(error)
        
        # Check bet object
        self.assertEqual(bet.player, self.player)
        self.assertEqual(bet.round, self.game_round)
        self.assertEqual(bet.bet_type, 'color')
        self.assertEqual(bet.color, 'red')
        self.assertEqual(bet.amount, amount)
        
        # Check wallet debit
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance - amount)
        
        # Check transaction record
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='bet',
            bet=bet
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, -amount)
    
    def test_place_bet_insufficient_balance(self):
        """Test bet placement with insufficient balance"""
        amount = 1500  # More than player's balance
        
        success, bet, error = place_bet_with_wallet(
            self.player, self.game_round, 'color', 'red', None, amount
        )
        
        self.assertFalse(success)
        self.assertIsNone(bet)
        self.assertEqual(error, "Insufficient balance")
        
        # Balance should be unchanged
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 1000)
    
    def test_process_winning_bet(self):
        """Test processing a winning bet"""
        # Create a bet first
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='color',
            color='red',
            amount=100
        )
        
        initial_balance = self.player.balance
        
        # Process winning result
        won, payout = process_bet_result(bet, 2, 'red')  # Red number = red color
        
        self.assertTrue(won)
        self.assertEqual(payout, 250)  # 100 * 2.5 multiplier
        
        # Check wallet credit
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance + payout)
        
        # Check transaction record
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='win',
            bet=bet
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, payout)
    
    def test_process_losing_bet(self):
        """Test processing a losing bet"""
        # Create a bet first
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='color',
            color='red',
            amount=100
        )
        
        initial_balance = self.player.balance
        
        # Process losing result
        won, payout = process_bet_result(bet, 1, 'green')  # Green number != red color
        
        self.assertFalse(won)
        self.assertEqual(payout, 0)
        
        # Balance should be unchanged (no credit for losing)
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance)
        
        # No win transaction should be created
        transaction_count = Transaction.objects.filter(
            player=self.player,
            transaction_type='win',
            bet=bet
        ).count()
        
        self.assertEqual(transaction_count, 0)
    
    def test_validate_bet_amount(self):
        """Test bet amount validation"""
        player_balance = 1000
        
        # Valid amount
        valid, error = validate_bet_amount(100, player_balance)
        self.assertTrue(valid)
        self.assertIsNone(error)
        
        # Invalid amount - negative
        valid, error = validate_bet_amount(-50, player_balance)
        self.assertFalse(valid)
        self.assertEqual(error, "Bet amount must be positive")
        
        # Invalid amount - too high
        valid, error = validate_bet_amount(15000, player_balance)
        self.assertFalse(valid)
        self.assertEqual(error, "Bet amount too high (max: 10000)")
        
        # Invalid amount - insufficient balance
        valid, error = validate_bet_amount(1500, player_balance)
        self.assertFalse(valid)
        self.assertEqual(error, "Insufficient balance (available: 1000)")
    
    def test_admin_adjust_wallet_credit(self):
        """Test admin wallet adjustment - credit"""
        initial_balance = self.player.balance
        amount = 500
        description = "Admin bonus"
        
        success, error = admin_adjust_wallet(
            self.player, amount, description, self.admin
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        # Check balance
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance + amount)
        
        # Check transaction
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='admin_adjust',
            admin=self.admin
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.description, description)
    
    def test_admin_adjust_wallet_debit(self):
        """Test admin wallet adjustment - debit"""
        initial_balance = self.player.balance
        amount = -200  # Negative for debit
        description = "Admin penalty"
        
        success, error = admin_adjust_wallet(
            self.player, amount, description, self.admin
        )
        
        self.assertTrue(success)
        self.assertIsNone(error)
        
        # Check balance
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_balance + amount)  # amount is negative
        
        # Check transaction
        transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='admin_adjust',
            admin=self.admin
        ).first()
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, amount)
    
    def test_get_betting_statistics(self):
        """Test getting betting statistics"""
        # Create some transactions
        Transaction.objects.create(
            player=self.player,
            transaction_type='deposit',
            amount=500,
            balance_before=1000,
            balance_after=1500,
            description='Deposit'
        )
        
        Transaction.objects.create(
            player=self.player,
            transaction_type='bet',
            amount=-100,
            balance_before=1500,
            balance_after=1400,
            description='Bet placed'
        )
        
        Transaction.objects.create(
            player=self.player,
            transaction_type='win',
            amount=250,
            balance_before=1400,
            balance_after=1650,
            description='Bet won'
        )
        
        stats = get_betting_statistics(self.player)
        
        self.assertEqual(stats['total_deposits'], 500)
        self.assertEqual(stats['total_bet_amount'], 100)
        self.assertEqual(stats['total_winnings'], 250)
        self.assertEqual(stats['profit_loss'], 150)  # 250 + (-100)


class MasterWalletSystemTest(TestCase):
    """Test cases for master wallet system functionality"""

    def setUp(self):
        """Set up test data"""
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000
        )

        self.admin = Admin.objects.create(
            username='master',
            password_hash='hashed_password',
            balance=0
        )

        self.game_round = GameRound.objects.create(
            room='test_room',
            period_id='TEST001',
            start_time=timezone.now()
        )

    def test_admin_credit_master_wallet(self):
        """Test crediting master wallet"""
        initial_balance = self.admin.balance
        amount = 500
        description = "Test house earning"

        success = self.admin.credit_master_wallet(
            amount=amount,
            description=description
        )

        self.assertTrue(success)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.balance, initial_balance + amount)

        # Check master wallet transaction record
        transaction = MasterWalletTransaction.objects.filter(
            admin=self.admin,
            transaction_type='house_earning'
        ).first()

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, amount)
        self.assertEqual(transaction.balance_before, initial_balance)
        self.assertEqual(transaction.balance_after, initial_balance + amount)
        self.assertEqual(transaction.description, description)

    def test_admin_debit_master_wallet_success(self):
        """Test successful master wallet debit"""
        # Set initial balance
        self.admin.balance = 1000
        self.admin.save()

        amount = 300
        description = "Test house payout"

        success = self.admin.debit_master_wallet(
            amount=amount,
            description=description
        )

        self.assertTrue(success)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.balance, 700)

        # Check master wallet transaction record
        transaction = MasterWalletTransaction.objects.filter(
            admin=self.admin,
            transaction_type='house_payout'
        ).first()

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, -amount)
        self.assertEqual(transaction.balance_before, 1000)
        self.assertEqual(transaction.balance_after, 700)

    def test_admin_debit_master_wallet_insufficient_balance(self):
        """Test master wallet debit with insufficient balance"""
        # Admin has 0 balance
        amount = 500

        success = self.admin.debit_master_wallet(
            amount=amount,
            description="Test insufficient balance"
        )

        self.assertFalse(success)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.balance, 0)  # Balance unchanged

        # No transaction should be created
        transaction_count = MasterWalletTransaction.objects.filter(
            admin=self.admin,
            transaction_type='house_payout'
        ).count()

        self.assertEqual(transaction_count, 0)

    def test_transfer_to_master_wallet(self):
        """Test transferring losing bet to master wallet"""
        # Create a bet
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='color',
            color='red',
            amount=100
        )

        initial_balance = self.admin.balance

        success, error = transfer_to_master_wallet(
            bet_amount=bet.amount,
            bet=bet,
            description="Test losing bet transfer"
        )

        self.assertTrue(success)
        self.assertIsNone(error)

        # Check admin balance increased
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.balance, initial_balance + bet.amount)

        # Check master wallet transaction
        transaction = MasterWalletTransaction.objects.filter(
            admin=self.admin,
            transaction_type='house_earning',
            bet=bet
        ).first()

        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, bet.amount)

    def test_process_winning_bet_with_master_wallet(self):
        """Test processing winning bet with master wallet system"""
        # Create a bet
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='color',
            color='red',
            amount=100
        )

        initial_player_balance = self.player.balance
        initial_admin_balance = self.admin.balance

        # Process winning result
        won, payout = process_bet_result_with_master_wallet(bet, 2, 'red')  # Red number = red color

        self.assertTrue(won)
        self.assertEqual(payout, 250)  # 100 * 2.5 multiplier

        # Check player wallet credited
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_player_balance + payout)

        # Check admin balance unchanged (no transfer for winning bet)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.balance, initial_admin_balance)

        # Check player transaction record
        player_transaction = Transaction.objects.filter(
            player=self.player,
            transaction_type='win',
            bet=bet
        ).first()

        self.assertIsNotNone(player_transaction)
        self.assertEqual(player_transaction.amount, payout)

        # No master wallet transaction for winning bet
        master_transaction_count = MasterWalletTransaction.objects.filter(
            bet=bet
        ).count()

        self.assertEqual(master_transaction_count, 0)

    def test_process_losing_bet_with_master_wallet(self):
        """Test processing losing bet with master wallet system"""
        # Create a bet
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='color',
            color='red',
            amount=100
        )

        initial_player_balance = self.player.balance
        initial_admin_balance = self.admin.balance

        # Process losing result
        won, payout = process_bet_result_with_master_wallet(bet, 1, 'green')  # Green number != red color

        self.assertFalse(won)
        self.assertEqual(payout, 0)

        # Check player balance unchanged (no credit for losing)
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, initial_player_balance)

        # Check admin balance increased by bet amount
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.balance, initial_admin_balance + bet.amount)

        # Check master wallet transaction
        master_transaction = MasterWalletTransaction.objects.filter(
            admin=self.admin,
            transaction_type='house_earning',
            bet=bet
        ).first()

        self.assertIsNotNone(master_transaction)
        self.assertEqual(master_transaction.amount, bet.amount)

        # No player win transaction for losing bet
        player_transaction_count = Transaction.objects.filter(
            player=self.player,
            transaction_type='win',
            bet=bet
        ).count()

        self.assertEqual(player_transaction_count, 0)

    def test_get_master_wallet_statistics(self):
        """Test getting master wallet statistics"""
        # Create some master wallet transactions
        MasterWalletTransaction.objects.create(
            admin=self.admin,
            transaction_type='house_earning',
            amount=500,
            balance_before=0,
            balance_after=500,
            description='Test earning 1'
        )

        MasterWalletTransaction.objects.create(
            admin=self.admin,
            transaction_type='house_earning',
            amount=300,
            balance_before=500,
            balance_after=800,
            description='Test earning 2'
        )

        MasterWalletTransaction.objects.create(
            admin=self.admin,
            transaction_type='house_payout',
            amount=-200,
            balance_before=800,
            balance_after=600,
            description='Test payout'
        )

        # Update admin balance to match
        self.admin.balance = 600
        self.admin.save()

        stats = get_master_wallet_statistics()

        self.assertEqual(stats['current_balance'], 600)
        self.assertEqual(stats['total_earnings'], 800)  # 500 + 300
        self.assertEqual(stats['total_payouts'], 200)   # abs(-200)
        self.assertEqual(stats['net_profit'], 600)      # 800 + (-200)
        self.assertEqual(stats['total_transactions'], 3)
