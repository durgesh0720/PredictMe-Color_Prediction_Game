# Test cases for Color Prediction Game models

from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from polling.models import Player, GameRound, Bet, Admin, Transaction, AdminColorSelection
from polling.security import PasswordSecurity, InputValidator


class PlayerModelTest(TestCase):
    """Test cases for Player model"""
    
    def setUp(self):
        """Set up test data"""
        self.player_data = {
            'username': 'testuser',
            'email': 'test@example.com',
            'first_name': 'Test',
            'last_name': 'User',
            'phone_number': '+1234567890'
        }
    
    def test_create_player(self):
        """Test creating a new player"""
        player = Player.objects.create(**self.player_data)
        
        self.assertEqual(player.username, 'testuser')
        self.assertEqual(player.email, 'test@example.com')
        self.assertEqual(player.balance, 0)  # Default balance is 0 - users must deposit first
        self.assertTrue(player.is_active)
        self.assertFalse(player.is_verified)
    
    def test_player_password_methods(self):
        """Test password setting and checking"""
        player = Player.objects.create(**self.player_data)
        
        # Test setting password
        password = 'TestPassword123!'
        player.set_password(password)
        self.assertIsNotNone(player.password_hash)
        
        # Test checking password
        self.assertTrue(player.check_password(password))
        self.assertFalse(player.check_password('wrongpassword'))
    
    def test_player_properties(self):
        """Test player property methods"""
        player = Player.objects.create(**self.player_data)
        
        # Test full_name property
        self.assertEqual(player.full_name, 'Test User')
        
        # Test display_name property
        self.assertEqual(player.display_name, 'Test User')
        
        # Test win_rate with no bets
        self.assertEqual(player.win_rate, 0)
    
    def test_player_win_rate_calculation(self):
        """Test win rate calculation with bets"""
        player = Player.objects.create(**self.player_data)

        # Create different game rounds for each bet (due to unique constraint)
        game_round1 = GameRound.objects.create(room='test1')
        game_round2 = GameRound.objects.create(room='test2')
        game_round3 = GameRound.objects.create(room='test3')

        # Create some bets in different rounds
        Bet.objects.create(player=player, round=game_round1, amount=100, correct=True)
        Bet.objects.create(player=player, round=game_round2, amount=100, correct=False)
        Bet.objects.create(player=player, round=game_round3, amount=100, correct=True)

        # Update player stats
        player.total_bets = 3
        player.total_wins = 2
        player.save()

        self.assertEqual(player.win_rate, 66.67)
    
    def test_update_last_login(self):
        """Test updating last login timestamp"""
        player = Player.objects.create(**self.player_data)
        
        # Initially no last login
        self.assertIsNone(player.last_login)
        
        # Update last login
        player.update_last_login()
        self.assertIsNotNone(player.last_login)
        
        # Check that it's recent
        time_diff = timezone.now() - player.last_login
        self.assertLess(time_diff.total_seconds(), 5)
    
    def test_unique_constraints(self):
        """Test unique constraints"""
        Player.objects.create(**self.player_data)
        
        # Try to create another player with same username
        with self.assertRaises(Exception):
            Player.objects.create(
                username='testuser',
                email='different@example.com'
            )
        
        # Try to create another player with same email
        with self.assertRaises(Exception):
            Player.objects.create(
                username='differentuser',
                email='test@example.com'
            )


class GameRoundModelTest(TestCase):
    """Test cases for GameRound model"""
    
    def test_create_game_round(self):
        """Test creating a new game round"""
        round_obj = GameRound.objects.create(room='test_room')
        
        self.assertEqual(round_obj.room, 'test_room')
        self.assertEqual(round_obj.game_type, 'parity')  # Default
        self.assertFalse(round_obj.ended)
        self.assertIsNotNone(round_obj.period_id)
    
    def test_period_id_generation(self):
        """Test automatic period ID generation"""
        round_obj = GameRound.objects.create(room='test_room')
        
        # Period ID should be generated based on timestamp
        expected_format = timezone.now().strftime('%Y%m%d%H%M')
        self.assertTrue(round_obj.period_id.startswith(expected_format[:8]))  # Date part
    
    def test_result_color_from_number(self):
        """Test color determination from result number"""
        round_obj = GameRound.objects.create(room='test_room')
        
        # Test green numbers (1, 3, 7, 9)
        for number in [1, 3, 7, 9]:
            round_obj.result_number = number
            self.assertEqual(round_obj.result_color_from_number, 'green')
        
        # Test red numbers (2, 4, 6, 8)
        for number in [2, 4, 6, 8]:
            round_obj.result_number = number
            self.assertEqual(round_obj.result_color_from_number, 'red')
        
        # Test violet numbers (0, 5)
        for number in [0, 5]:
            round_obj.result_number = number
            self.assertEqual(round_obj.result_color_from_number, 'violet')
        
        # Test None result
        round_obj.result_number = None
        self.assertIsNone(round_obj.result_color_from_number)


class BetModelTest(TestCase):
    """Test cases for Bet model"""
    
    def setUp(self):
        """Set up test data"""
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com'
        )
        self.game_round = GameRound.objects.create(room='test_room')
    
    def test_create_color_bet(self):
        """Test creating a color bet"""
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='color',
            color='red',
            amount=100
        )
        
        self.assertEqual(bet.bet_type, 'color')
        self.assertEqual(bet.color, 'red')
        self.assertEqual(bet.amount, 100)
        self.assertFalse(bet.correct)
        self.assertEqual(bet.payout, 0)
    
    def test_create_number_bet(self):
        """Test creating a number bet"""
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='number',
            number=5,
            amount=50
        )
        
        self.assertEqual(bet.bet_type, 'number')
        self.assertEqual(bet.number, 5)
        self.assertEqual(bet.amount, 50)
    
    def test_check_win_color_bet(self):
        """Test checking win for color bet"""
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='color',
            color='red',
            amount=100
        )
        
        # Test winning bet
        result = bet.check_win(result_number=2, result_color='red')
        self.assertTrue(result)
        self.assertTrue(bet.correct)
        self.assertEqual(bet.payout, 250)  # 100 * 2.5
        
        # Reset bet
        bet.correct = False
        bet.payout = 0
        bet.save()
        
        # Test losing bet
        result = bet.check_win(result_number=1, result_color='green')
        self.assertFalse(result)
        self.assertFalse(bet.correct)
        self.assertEqual(bet.payout, 0)
    
    def test_check_win_number_bet(self):
        """Test checking win for number bet"""
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='number',
            number=5,
            amount=100
        )
        
        # Test winning bet
        result = bet.check_win(result_number=5, result_color='violet')
        self.assertTrue(result)
        self.assertTrue(bet.correct)
        self.assertEqual(bet.payout, 900)  # 100 * 9
        
        # Reset bet
        bet.correct = False
        bet.payout = 0
        bet.save()
        
        # Test losing bet
        result = bet.check_win(result_number=3, result_color='green')
        self.assertFalse(result)
        self.assertFalse(bet.correct)
        self.assertEqual(bet.payout, 0)


class AdminModelTest(TestCase):
    """Test cases for Admin model"""
    
    def test_create_admin(self):
        """Test creating a new admin"""
        admin = Admin.objects.create(username='admin_user')
        
        self.assertEqual(admin.username, 'admin_user')
        self.assertTrue(admin.is_active)
        self.assertIsNone(admin.last_login)
    
    def test_admin_password_methods(self):
        """Test admin password setting and checking"""
        admin = Admin.objects.create(username='admin_user')
        
        # Test setting password
        password = 'AdminPassword123!'
        admin.set_password(password)
        self.assertIsNotNone(admin.password_hash)
        
        # Test checking password
        self.assertTrue(admin.check_password(password))
        self.assertFalse(admin.check_password('wrongpassword'))


class TransactionModelTest(TestCase):
    """Test cases for Transaction model"""
    
    def setUp(self):
        """Set up test data"""
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000
        )
    
    def test_create_transaction(self):
        """Test creating a transaction"""
        transaction = Transaction.objects.create(
            player=self.player,
            transaction_type='deposit',
            amount=500,
            balance_before=1000,
            balance_after=1500,
            description='Test deposit'
        )
        
        self.assertEqual(transaction.transaction_type, 'deposit')
        self.assertEqual(transaction.amount, 500)
        self.assertEqual(transaction.balance_before, 1000)
        self.assertEqual(transaction.balance_after, 1500)


class SecurityTest(TestCase):
    """Test cases for security utilities"""
    
    def test_password_strength_validation(self):
        """Test password strength validation"""
        # Test weak passwords
        weak_passwords = [
            'password',
            '123456',
            'abc',
            'PASSWORD',
            'password123'
        ]
        
        for password in weak_passwords:
            errors = PasswordSecurity.validate_password_strength(password)
            self.assertGreater(len(errors), 0)
        
        # Test strong password
        strong_password = 'StrongPassword123!'
        errors = PasswordSecurity.validate_password_strength(strong_password)
        self.assertEqual(len(errors), 0)
    
    def test_input_validation(self):
        """Test input validation utilities"""
        # Test username validation
        valid, result = InputValidator.validate_username('validuser')
        self.assertTrue(valid)
        self.assertEqual(result, 'validuser')
        
        valid, result = InputValidator.validate_username('invalid user!')
        self.assertFalse(valid)
        
        # Test email validation
        valid, result = InputValidator.validate_email('test@example.com')
        self.assertTrue(valid)
        self.assertEqual(result, 'test@example.com')
        
        valid, result = InputValidator.validate_email('invalid-email')
        self.assertFalse(valid)
        
        # Test phone validation
        valid, result = InputValidator.validate_phone('+1234567890')
        self.assertTrue(valid)
        
        valid, result = InputValidator.validate_phone('invalid-phone')
        self.assertFalse(valid)
    
    def test_secure_token_generation(self):
        """Test secure token generation"""
        token1 = PasswordSecurity.generate_secure_token()
        token2 = PasswordSecurity.generate_secure_token()
        
        # Tokens should be different
        self.assertNotEqual(token1, token2)
        
        # Tokens should have reasonable length
        self.assertGreater(len(token1), 20)
        self.assertGreater(len(token2), 20)


class ModelIntegrationTest(TestCase):
    """Integration tests for model interactions"""
    
    def setUp(self):
        """Set up test data"""
        self.player = Player.objects.create(
            username='testuser',
            email='test@example.com',
            balance=1000
        )
        self.admin = Admin.objects.create(username='admin_user')
        self.game_round = GameRound.objects.create(room='test_room')
    
    def test_complete_betting_flow(self):
        """Test complete betting flow"""
        # Player places a bet
        bet = Bet.objects.create(
            player=self.player,
            round=self.game_round,
            bet_type='color',
            color='red',
            amount=100
        )
        
        # Update player balance
        self.player.balance -= bet.amount
        self.player.total_bets += 1
        self.player.save()
        
        # Admin selects color
        admin_selection = AdminColorSelection.objects.create(
            round=self.game_round,
            admin=self.admin,
            selected_color='red'
        )
        
        # Game round ends with result
        self.game_round.result_number = 2  # Red number
        self.game_round.result_color = 'red'
        self.game_round.ended = True
        self.game_round.save()
        
        # Check bet result
        bet.check_win(self.game_round.result_number, self.game_round.result_color)
        
        # Verify bet won
        self.assertTrue(bet.correct)
        self.assertEqual(bet.payout, 250)
        
        # Update player stats
        self.player.balance += bet.payout
        self.player.total_wins += 1
        self.player.save()
        
        # Create transaction record
        Transaction.objects.create(
            player=self.player,
            transaction_type='win',
            amount=bet.payout,
            balance_before=900,  # 1000 - 100
            balance_after=1150,  # 900 + 250
            description=f'Won bet on round {self.game_round.period_id}'
        )
        
        # Verify final state
        self.player.refresh_from_db()
        self.assertEqual(self.player.balance, 1150)
        self.assertEqual(self.player.total_bets, 1)
        self.assertEqual(self.player.total_wins, 1)
        self.assertEqual(self.player.win_rate, 100.0)
