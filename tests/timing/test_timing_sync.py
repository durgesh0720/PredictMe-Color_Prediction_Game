"""
Test timing synchronization between user interface and admin panel
"""

from django.test import TestCase, Client
from django.utils import timezone
from datetime import timedelta
import json

from polling.models import GameRound, Player, Admin
from polling.consumers import ROUND_DURATION, BETTING_DURATION
from polling.admin_views import ROUND_DURATION as ADMIN_ROUND_DURATION, BETTING_DURATION as ADMIN_BETTING_DURATION


class TimingSynchronizationTests(TestCase):
    def setUp(self):
        """Set up test data"""
        # Create test admin
        self.admin = Admin.objects.create(
            username='testadmin',
            is_active=True
        )
        self.admin.set_password('testpass123')
        self.admin.save()
        
        # Create test player
        self.player = Player.objects.create(
            username='testplayer',
            email='player@test.com',
            balance=1000,
            is_active=True,
            email_verified=True
        )
        self.player.set_password('testpass123')
        self.player.save()
        
        self.client = Client()

    def test_timing_constants_consistency(self):
        """Test that timing constants are consistent between user and admin interfaces"""
        # Check that consumers.py and admin_views.py use the same constants
        self.assertEqual(ROUND_DURATION, ADMIN_ROUND_DURATION, 
                        "Round duration must be consistent between user and admin interfaces")
        self.assertEqual(BETTING_DURATION, ADMIN_BETTING_DURATION,
                        "Betting duration must be consistent between user and admin interfaces")
        
        # Verify the expected values
        self.assertEqual(ROUND_DURATION, 50, "Round duration should be 50 seconds")
        self.assertEqual(BETTING_DURATION, 40, "Betting duration should be 40 seconds")

    def test_admin_timer_api_consistency(self):
        """Test that admin timer API returns consistent timing with game logic"""
        # Create a test game round
        start_time = timezone.now() - timedelta(seconds=10)  # Started 10 seconds ago
        game_round = GameRound.objects.create(
            room='main',
            start_time=start_time,
            ended=False
        )
        
        # Login as admin
        session = self.client.session
        session['admin_id'] = self.admin.id
        session['admin_username'] = self.admin.username
        session.save()
        
        # Call admin timer API
        response = self.client.get('/control-panel/api/timer-info/')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check timer info
        timers = data['timers']
        self.assertEqual(len(timers), 1)
        
        timer_info = timers[0]
        self.assertEqual(timer_info['round_id'], game_round.id)
        
        # Time remaining should be approximately 40 seconds (50 - 10)
        expected_time_remaining = 40
        actual_time_remaining = timer_info['time_remaining']
        
        # Allow 2 second tolerance for test execution time
        self.assertAlmostEqual(actual_time_remaining, expected_time_remaining, delta=2,
                              msg=f"Admin timer should show ~{expected_time_remaining}s remaining, got {actual_time_remaining}s")

    def test_admin_selection_during_betting(self):
        """Test that admin can select color during betting period"""
        # Create a round that's in the betting period (20 seconds elapsed)
        start_time = timezone.now() - timedelta(seconds=20)
        game_round = GameRound.objects.create(
            room='main',
            start_time=start_time,
            ended=False
        )

        # Login as admin
        session = self.client.session
        session['admin_id'] = self.admin.id
        session['admin_username'] = self.admin.username
        session.save()

        # Try to select a color (should be allowed)
        response = self.client.post('/control-panel/api/select-color/',
            data=json.dumps({
                'round_id': game_round.id,
                'color': 'red'  # Use 'color' as expected by the API
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Debug the response
        print(f"Response data: {data}")

        self.assertTrue(data.get('success', False),
                       f"Admin should be able to select color during betting period (0-40s). Response: {data}")

    def test_admin_selection_early_betting(self):
        """Test that admin can select color early in betting period"""
        # Create a round that's only 10 seconds in (early betting period)
        start_time = timezone.now() - timedelta(seconds=10)
        game_round = GameRound.objects.create(
            room='main',
            start_time=start_time,
            ended=False
        )

        # Login as admin
        session = self.client.session
        session['admin_id'] = self.admin.id
        session['admin_username'] = self.admin.username
        session.save()

        # Try to select a color (should be allowed)
        response = self.client.post('/control-panel/api/select-color/',
            data=json.dumps({
                'round_id': game_round.id,
                'color': 'red'  # Use 'color' as expected by the API
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data.get('success', False),
                       "Admin should be able to select color anytime during the round")

    def test_admin_selection_too_late(self):
        """Test that admin cannot select color after round ends"""
        # Create a round that's already ended (55 seconds elapsed)
        start_time = timezone.now() - timedelta(seconds=55)
        game_round = GameRound.objects.create(
            room='main',
            start_time=start_time,
            ended=False
        )
        
        # Login as admin
        session = self.client.session
        session['admin_id'] = self.admin.id
        session['admin_username'] = self.admin.username
        session.save()
        
        # Try to select a color (should be rejected)
        response = self.client.post('/control-panel/api/select-color/',
            data=json.dumps({
                'round_id': game_round.id,
                'color': 'red'  # Use 'color' as expected by the API
            }),
            content_type='application/json'
        )

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data.get('success', True),
                        "Admin should NOT be able to select color after round ends")
        self.assertIn('ended', data.get('message', ''))

    def test_timing_calculation_accuracy(self):
        """Test that timing calculations are accurate across different scenarios"""
        test_cases = [
            (5, 45),   # 5 seconds elapsed, 45 remaining
            (20, 30),  # 20 seconds elapsed, 30 remaining
            (40, 10),  # 40 seconds elapsed, 10 remaining (selection window)
            (45, 5),   # 45 seconds elapsed, 5 remaining (selection window)
            (50, 0),   # 50 seconds elapsed, 0 remaining (ended)
            (60, 0),   # 60 seconds elapsed, 0 remaining (ended)
        ]
        
        for elapsed_seconds, expected_remaining in test_cases:
            with self.subTest(elapsed=elapsed_seconds, expected=expected_remaining):
                # Create round with specific elapsed time
                start_time = timezone.now() - timedelta(seconds=elapsed_seconds)
                game_round = GameRound.objects.create(
                    room='main',
                    start_time=start_time,
                    ended=False
                )
                
                # Login as admin
                session = self.client.session
                session['admin_id'] = self.admin.id
                session.save()
                
                # Get timer info
                response = self.client.get('/control-panel/api/timer-info/')
                data = json.loads(response.content)
                
                timer_info = data['timers'][0]
                actual_remaining = timer_info['time_remaining']
                
                # Allow 1 second tolerance
                self.assertAlmostEqual(actual_remaining, expected_remaining, delta=1,
                                     msg=f"After {elapsed_seconds}s elapsed, should have {expected_remaining}s remaining, got {actual_remaining}s")
                
                # Clean up
                game_round.delete()
