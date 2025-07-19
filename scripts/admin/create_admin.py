#!/usr/bin/env python
"""
Script to create an initial admin user for the color prediction game admin panel.
"""

import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Admin, GameControl

def create_admin():
    """Create initial admin user and game controls"""
    
    # Create admin user
    admin_username = "admin"
    admin_password = "admin123"  # Change this in production!
    
    # Check if admin already exists
    if Admin.objects.filter(username=admin_username).exists():
        print(f"Admin user '{admin_username}' already exists!")
        admin = Admin.objects.get(username=admin_username)
    else:
        admin = Admin()
        admin.username = admin_username
        admin.set_password(admin_password)
        admin.is_active = True
        admin.save()
        print(f"Created admin user: {admin_username}")
        print(f"Password: {admin_password}")
        print("⚠️  IMPORTANT: Change the password after first login!")
    
    # Create game controls for all game types
    game_types = ['parity', 'sapre', 'bcone', 'noki']
    
    for game_type in game_types:
        control, created = GameControl.objects.get_or_create(
            game_type=game_type,
            defaults={
                'is_active': True,
                'auto_result': True,
                'round_duration': 180,
                'betting_duration': 150,
            }
        )
        
        if created:
            print(f"Created game control for {game_type}")
        else:
            print(f"Game control for {game_type} already exists")
    
    print("\n" + "="*50)
    print("🎮 ADMIN PANEL SETUP COMPLETE!")
    print("="*50)
    print(f"Admin URL: http://localhost:8000/control-panel/")
    print(f"Username: {admin_username}")
    print(f"Password: {admin_password}")
    print("\n📋 Admin Panel Features:")
    print("• Dashboard with game overview")
    print("• Game control (start/stop, manual results)")
    print("• User management")
    print("• Financial management")
    print("• Reports and analytics")
    print("• Activity logs")
    print("\n🔧 Next Steps:")
    print("1. Start the Django server: python manage.py runserver")
    print("2. Visit the admin panel and login")
    print("3. Change the default password")
    print("4. Configure game settings as needed")
    print("="*50)

if __name__ == "__main__":
    create_admin()
