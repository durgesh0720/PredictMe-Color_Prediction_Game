#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player, GameRound, Bet
from django.utils import timezone
from django.contrib.auth.models import User
import random

def create_test_data():
    print("Creating test data...")
    
    # Create superuser if it doesn't exist
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
        print("Created admin user (username: admin, password: admin123)")
    
    # Create test players
    test_players = [
        {'username': 'Alice', 'balance': 1500, 'score': 150},
        {'username': 'Bob', 'balance': 800, 'score': 80},
        {'username': 'Charlie', 'balance': 2000, 'score': 200},
        {'username': 'Diana', 'balance': 1200, 'score': 120},
        {'username': 'Eve', 'balance': 900, 'score': 90},
    ]
    
    for player_data in test_players:
        player, created = Player.objects.get_or_create(
            username=player_data['username'],
            defaults={
                'balance': player_data['balance'],
                'score': player_data['score'],
                'total_bets': random.randint(10, 50),
                'total_wins': random.randint(5, 25)
            }
        )
        if created:
            print(f"Created player: {player.username}")
    
    # Create test game rounds
    rooms = ['main', 'vip', 'beginner', 'high-stakes']
    colors = ['Red', 'Green', 'Blue']
    
    for i in range(10):
        room = random.choice(rooms)
        result_color = random.choice(colors)
        
        game_round = GameRound.objects.create(
            room=room,
            start_time=timezone.now() - timezone.timedelta(hours=i),
            result_color=result_color,
            ended=True
        )
        
        # Create some bets for this round
        players = Player.objects.all()
        for player in random.sample(list(players), random.randint(2, 4)):
            bet_color = random.choice(colors)
            bet_amount = random.randint(10, 100)
            correct = bet_color == result_color
            
            Bet.objects.create(
                player=player,
                round=game_round,
                color=bet_color,
                amount=bet_amount,
                correct=correct
            )
        
        print(f"Created game round #{game_round.id} in {room} room")
    
    print("Test data created successfully!")
    print("\nYou can now:")
    print("1. Visit http://127.0.0.1:8000/ to play the game")
    print("2. Visit http://127.0.0.1:8000/admin/ to access admin panel")
    print("3. Visit http://127.0.0.1:8000/history/ to see game history")
    print("\nAdmin credentials: username=admin, password=admin123")

if __name__ == '__main__':
    create_test_data()
