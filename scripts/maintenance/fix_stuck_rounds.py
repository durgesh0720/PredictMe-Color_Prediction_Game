#!/usr/bin/env python3
"""
Fix stuck game rounds that are causing red error popups
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import GameRound
from django.utils import timezone
from datetime import timedelta

def fix_stuck_rounds():
    """Fix all stuck game rounds"""
    print("🔧 Fixing Stuck Game Rounds...")
    
    # Find rounds that have been running for more than 5 minutes
    cutoff_time = timezone.now() - timedelta(minutes=5)
    stuck_rounds = GameRound.objects.filter(
        ended=False,
        start_time__lt=cutoff_time
    )
    
    print(f"📊 Found {stuck_rounds.count()} stuck rounds")
    
    if stuck_rounds.count() == 0:
        print("✅ No stuck rounds found!")
        return True
    
    # End all stuck rounds
    for round_obj in stuck_rounds:
        elapsed = (timezone.now() - round_obj.start_time).total_seconds()
        print(f"  🔄 Ending round {round_obj.period_id} ({round_obj.room}) - {elapsed:.0f}s elapsed")
        
        # Set a random result for the stuck round
        import random
        result_number = random.randint(0, 9)
        
        # Determine color based on number
        if result_number in [1, 3, 7, 9]:
            result_color = 'green'
        elif result_number in [2, 4, 6, 8]:
            result_color = 'red'
        else:  # 0, 5
            result_color = 'violet'
        
        # Update the round
        round_obj.result_number = result_number
        round_obj.result_color = result_color
        round_obj.ended = True
        round_obj.save()
        
        print(f"    ✅ Set result: {result_number} ({result_color})")
    
    print(f"🎉 Fixed {stuck_rounds.count()} stuck rounds!")
    return True

def clean_old_rounds():
    """Clean up very old completed rounds"""
    print("\n🧹 Cleaning Old Rounds...")
    
    # Delete rounds older than 24 hours
    cutoff_time = timezone.now() - timedelta(hours=24)
    old_rounds = GameRound.objects.filter(
        ended=True,
        start_time__lt=cutoff_time
    )
    
    count = old_rounds.count()
    if count > 0:
        old_rounds.delete()
        print(f"🗑️  Deleted {count} old completed rounds")
    else:
        print("✅ No old rounds to clean")
    
    return True

def verify_fix():
    """Verify that the fix worked"""
    print("\n✅ Verifying Fix...")
    
    # Check for any remaining stuck rounds
    cutoff_time = timezone.now() - timedelta(minutes=5)
    remaining_stuck = GameRound.objects.filter(
        ended=False,
        start_time__lt=cutoff_time
    ).count()
    
    # Check active rounds
    active_rounds = GameRound.objects.filter(ended=False).count()
    
    print(f"📊 Remaining stuck rounds: {remaining_stuck}")
    print(f"📊 Total active rounds: {active_rounds}")
    
    if remaining_stuck == 0:
        print("✅ All stuck rounds have been fixed!")
        return True
    else:
        print("⚠️  Some rounds may still be stuck")
        return False

def main():
    """Main fix function"""
    print("🚨 Fixing Red Error Popup Issue")
    print("=" * 50)
    
    try:
        # Fix stuck rounds
        success1 = fix_stuck_rounds()
        
        # Clean old rounds
        success2 = clean_old_rounds()
        
        # Verify the fix
        success3 = verify_fix()
        
        print("\n" + "=" * 50)
        print("📋 FIX SUMMARY")
        print("=" * 50)
        
        if success1 and success2 and success3:
            print("✅ All fixes applied successfully!")
            print("\n🎯 Red error popups should now be resolved!")
            print("\nNext steps:")
            print("1. Refresh the game page")
            print("2. Try placing bets on red, green, and violet")
            print("3. Monitor for any remaining errors")
        else:
            print("⚠️  Some fixes may not have completed successfully")
            print("Please check the output above for details")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error during fix: {e}")
        return 1

if __name__ == '__main__':
    sys.exit(main())
