#!/usr/bin/env python3
"""
Diagnostic script to identify red error popup issues
"""
import os
import django
import sys

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'server.settings')
django.setup()

from polling.models import Player, GameRound, Bet
from django.utils import timezone
from datetime import timedelta

def check_recent_errors():
    """Check for recent betting errors"""
    print("🔍 Checking Recent Betting Activity...")
    
    # Check recent bets
    recent_bets = Bet.objects.filter(
        created_at__gte=timezone.now() - timedelta(hours=1)
    ).order_by('-created_at')[:10]
    
    print(f"📊 Recent bets (last hour): {recent_bets.count()}")
    
    for bet in recent_bets:
        status = "✅ Success" if bet.correct is not None else "⏳ Pending"
        print(f"  - {bet.player.username}: {bet.color or bet.number} (${bet.amount}) - {status}")
    
    return recent_bets.count() > 0

def check_color_distribution():
    """Check color betting distribution"""
    print("\n🎨 Color Betting Distribution:")
    
    color_stats = {}
    for color in ['red', 'green', 'violet']:
        count = Bet.objects.filter(color=color).count()
        color_stats[color] = count
        print(f"  - {color.upper()}: {count} bets")
    
    return color_stats

def check_failed_bets():
    """Check for failed or problematic bets"""
    print("\n❌ Checking for Failed Bets:")
    
    # Check bets with zero payout that should have won
    recent_rounds = GameRound.objects.filter(
        ended=True,
        start_time__gte=timezone.now() - timedelta(hours=1)
    )
    
    issues_found = 0
    
    for round_obj in recent_rounds:
        if round_obj.result_color:
            # Check bets that should have won but didn't get payout
            winning_bets = Bet.objects.filter(
                round=round_obj,
                color=round_obj.result_color,
                payout=0
            )
            
            if winning_bets.exists():
                print(f"  ⚠️  Round {round_obj.period_id}: {winning_bets.count()} winning bets with no payout")
                issues_found += winning_bets.count()
    
    if issues_found == 0:
        print("  ✅ No failed bet issues found")
    
    return issues_found

def check_player_balances():
    """Check for players with negative or zero balances"""
    print("\n💰 Checking Player Balances:")
    
    zero_balance = Player.objects.filter(balance=0).count()
    negative_balance = Player.objects.filter(balance__lt=0).count()
    
    print(f"  - Players with zero balance: {zero_balance}")
    print(f"  - Players with negative balance: {negative_balance}")
    
    if negative_balance > 0:
        print("  ⚠️  Negative balances found - this could cause betting errors")
        neg_players = Player.objects.filter(balance__lt=0)[:5]
        for player in neg_players:
            print(f"    - {player.username}: ${player.balance}")
    
    return negative_balance

def check_active_rounds():
    """Check for active game rounds"""
    print("\n🎮 Checking Active Game Rounds:")
    
    active_rounds = GameRound.objects.filter(ended=False)
    print(f"  - Active rounds: {active_rounds.count()}")
    
    for round_obj in active_rounds:
        elapsed = (timezone.now() - round_obj.start_time).total_seconds()
        print(f"    - Round {round_obj.period_id} ({round_obj.room}): {elapsed:.0f}s elapsed")
        
        # Check if round is stuck (running too long)
        if elapsed > 300:  # 5 minutes
            print(f"      ⚠️  Round may be stuck (running for {elapsed:.0f}s)")
    
    return active_rounds.count()

def check_websocket_issues():
    """Check for potential WebSocket authentication issues"""
    print("\n🔌 Checking WebSocket Authentication:")
    
    # Check for players without proper authentication fields
    players_no_auth = Player.objects.filter(
        models.Q(username__isnull=True) | models.Q(username='')
    ).count()
    
    print(f"  - Players with missing usernames: {players_no_auth}")
    
    # Check for inactive players
    inactive_players = Player.objects.filter(is_active=False).count()
    print(f"  - Inactive players: {inactive_players}")
    
    return players_no_auth + inactive_players

def main():
    """Run all diagnostic checks"""
    print("🚨 Red Error Popup Diagnostic")
    print("=" * 50)
    
    issues_found = 0
    
    # Run all checks
    issues_found += 0 if check_recent_errors() else 1
    color_stats = check_color_distribution()
    issues_found += check_failed_bets()
    issues_found += check_player_balances()
    issues_found += 0 if check_active_rounds() >= 0 else 1
    issues_found += check_websocket_issues()
    
    print("\n" + "=" * 50)
    print("📋 DIAGNOSTIC SUMMARY")
    print("=" * 50)
    
    if issues_found == 0:
        print("✅ No major issues detected!")
        print("\nPossible causes of red error popups:")
        print("1. WebSocket authentication timeouts")
        print("2. Network connectivity issues")
        print("3. Browser console errors")
        print("4. Session expiration")
    else:
        print(f"⚠️  {issues_found} potential issues found")
        print("\nRecommended actions:")
        print("1. Check server logs for WebSocket errors")
        print("2. Verify user authentication")
        print("3. Check browser console for JavaScript errors")
        print("4. Test betting functionality manually")
    
    print(f"\n🎨 Color Distribution:")
    for color, count in color_stats.items():
        print(f"   {color.upper()}: {count} bets")
    
    return issues_found

if __name__ == '__main__':
    try:
        from django.db import models
        sys.exit(main())
    except Exception as e:
        print(f"❌ Error running diagnostic: {e}")
        sys.exit(1)
