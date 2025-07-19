"""
Wallet utility functions for handling betting transactions
"""
from django.db import transaction
from django.db.models import Sum
from .models import Player, Transaction, Bet, Admin, MasterWalletTransaction


def place_bet_with_wallet(player, game_round, bet_type, color, number, amount):
    """
    Place a bet and debit wallet with proper transaction logging
    Returns (success, bet_object, error_message)
    """
    try:
        with transaction.atomic():
            # Refresh player from database to get latest balance
            player.refresh_from_db()

            # Check if player already has a bet for this round (with select_for_update to prevent race conditions)
            existing_bet = Bet.objects.select_for_update().filter(player=player, round=game_round).first()
            if existing_bet:
                return False, None, "You can only place one bet per round. Wait for the next round to place another bet."

            # Check if player has sufficient balance
            if player.balance < amount:
                return False, None, "Insufficient balance"

            # Create bet object first
            bet_data = {
                'player': player,
                'round': game_round,
                'bet_type': bet_type,
                'amount': amount
            }

            if bet_type == 'color':
                bet_data['color'] = color
            elif bet_type == 'number':
                bet_data['number'] = number

            bet = Bet.objects.create(**bet_data)

            # Debit wallet using the player method
            success = player.debit_wallet(
                amount=amount,
                transaction_type='bet',
                description=f'Bet placed on {color or number} for round {game_round.period_id}',
                bet=bet
            )

            if not success:
                # This shouldn't happen due to the balance check above, but just in case
                return False, None, "Failed to debit wallet"

            return True, bet, None

    except Exception as e:
        # Handle unique constraint violation specifically
        if 'unique constraint' in str(e).lower() or 'duplicate' in str(e).lower():
            return False, None, "You can only place one bet per round. Wait for the next round to place another bet."
        return False, None, f"Error placing bet: {str(e)}"


def process_bet_result(bet, result_number, result_color):
    """
    Process bet result and handle wallet transactions for wins
    Returns (won, payout_amount)
    """
    try:
        with transaction.atomic():
            # Check if bet won using the existing method
            won = bet.check_win(result_number, result_color)
            
            if won and bet.payout > 0:
                # Credit wallet for winning
                bet.player.credit_wallet(
                    amount=bet.payout,
                    transaction_type='win',
                    description=f'Won bet on {bet.color or bet.number} for round {bet.round.period_id}',
                    bet=bet
                )
                return True, bet.payout
            
            return won, 0
            
    except Exception as e:
        print(f"Error processing bet result: {e}")
        return False, 0


def get_wallet_balance(player):
    """
    Get current wallet balance with refresh from database
    """
    player.refresh_from_db()
    return player.balance


def get_transaction_history(player, transaction_type=None, limit=None):
    """
    Get transaction history for a player
    """
    query = Transaction.objects.filter(player=player)
    
    if transaction_type:
        query = query.filter(transaction_type=transaction_type)
    
    query = query.order_by('-created_at')
    
    if limit:
        query = query[:limit]
    
    return query


def validate_bet_amount(amount, player_balance):
    """
    Validate bet amount against player balance and limits
    Returns (is_valid, error_message)
    """
    try:
        amount = int(amount)
    except (ValueError, TypeError):
        return False, "Invalid bet amount"

    if amount <= 0:
        return False, "Bet amount must be positive"

    if amount > 10000:  # Maximum bet limit
        return False, "Bet amount too high (max: 10000)"

    # Check if player has any balance at all (must deposit first)
    if player_balance <= 0:
        return False, "You must deposit money before placing bets. Click 'Add Money' to make a deposit."

    if amount > player_balance:
        return False, f"Insufficient balance (available: {player_balance})"

    return True, None


def calculate_payout(bet_type, amount, color=None):
    """
    Calculate payout for a bet based on type and color
    """
    if bet_type == 'color':
        # Color bets have 2.5x payout for all colors
        return int(amount * 2.5)
    elif bet_type == 'number':
        # Number bets have 9x payout
        return amount * 9
    
    return 0


def get_betting_statistics(player):
    """
    Get comprehensive betting statistics for a player
    """
    # Get all transactions for this player
    all_transactions = Transaction.objects.filter(player=player)
    
    # Calculate totals
    total_deposits = all_transactions.filter(
        transaction_type='deposit'
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_bets = all_transactions.filter(
        transaction_type='bet'
    ).aggregate(total=Sum('amount'))['total'] or 0

    total_wins = all_transactions.filter(
        transaction_type='win'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    # Calculate profit/loss
    profit_loss = total_wins + total_bets  # total_bets is negative
    
    return {
        'total_deposits': total_deposits,
        'total_bet_amount': abs(total_bets),
        'total_winnings': total_wins,
        'profit_loss': profit_loss,
        'current_balance': player.balance,
        'total_bets_count': player.total_bets,
        'total_wins_count': player.total_wins,
        'win_rate': player.win_rate
    }


def admin_adjust_wallet(player, amount, description, admin):
    """
    Admin function to adjust player wallet balance
    Returns (success, error_message)
    """
    try:
        if amount > 0:
            # Credit wallet
            player.credit_wallet(
                amount=amount,
                transaction_type='admin_adjust',
                description=description,
                admin=admin
            )
        elif amount < 0:
            # Debit wallet
            success = player.debit_wallet(
                amount=abs(amount),
                transaction_type='admin_adjust',
                description=description,
                admin=admin
            )
            if not success:
                return False, "Insufficient balance for debit"
        
        return True, None

    except Exception as e:
        return False, f"Error adjusting wallet: {str(e)}"


def get_master_admin():
    """
    Get the master admin (first admin or create one if none exists)
    """
    try:
        # Get the first admin or create a master admin
        admin = Admin.objects.filter(is_active=True).first()
        if not admin:
            admin = Admin.objects.create(
                username='master',
                password_hash='',  # No password needed for master wallet
                is_active=True,
                balance=0
            )
        return admin
    except Exception as e:
        print(f"Error getting master admin: {e}")
        return None


def transfer_to_master_wallet(bet_amount, bet, description=""):
    """
    Transfer losing bet amount to master wallet
    Returns (success, error_message)
    """
    try:
        with transaction.atomic():
            master_admin = get_master_admin()
            if not master_admin:
                return False, "Master admin not found"

            # Credit the master wallet
            master_admin.credit_master_wallet(
                amount=bet_amount,
                description=description or f"House earning from losing bet on round {bet.round.period_id}",
                bet=bet
            )

            return True, None

    except Exception as e:
        return False, f"Error transferring to master wallet: {str(e)}"


def process_bet_result_with_master_wallet(bet, result_number, result_color):
    """
    Process bet result with master wallet handling
    - If user wins: Credit user wallet with winnings
    - If user loses: Transfer bet amount to master wallet
    Returns (won, payout_amount)
    """
    try:
        with transaction.atomic():
            # Check if bet won using the existing method
            won = bet.check_win(result_number, result_color)

            if won and bet.payout > 0:
                # User won - credit wallet for winning
                bet.player.credit_wallet(
                    amount=bet.payout,
                    transaction_type='win',
                    description=f'Won bet on {bet.color or bet.number} for round {bet.round.period_id}',
                    bet=bet
                )
                return True, bet.payout
            else:
                # User lost - transfer bet amount to master wallet
                success, error = transfer_to_master_wallet(
                    bet_amount=bet.amount,
                    bet=bet,
                    description=f"House earning from losing bet by {bet.player.username}"
                )

                if not success:
                    print(f"Error transferring to master wallet: {error}")

                return False, 0

    except Exception as e:
        print(f"Error processing bet result with master wallet: {e}")
        return False, 0


def get_master_wallet_balance():
    """
    Get current master wallet balance
    """
    try:
        master_admin = get_master_admin()
        if master_admin:
            master_admin.refresh_from_db()
            return master_admin.balance
        return 0
    except Exception as e:
        print(f"Error getting master wallet balance: {e}")
        return 0


def get_master_wallet_statistics():
    """
    Get comprehensive master wallet statistics
    """
    try:
        master_admin = get_master_admin()
        if not master_admin:
            return {
                'current_balance': 0,
                'total_earnings': 0,
                'total_payouts': 0,
                'net_profit': 0,
                'total_transactions': 0
            }

        # Get all master wallet transactions
        all_transactions = MasterWalletTransaction.objects.filter(admin=master_admin)

        # Calculate totals
        total_earnings = all_transactions.filter(
            transaction_type='house_earning'
        ).aggregate(total=Sum('amount'))['total'] or 0

        total_payouts = all_transactions.filter(
            transaction_type='house_payout'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Calculate net profit (earnings - payouts)
        net_profit = total_earnings + total_payouts  # total_payouts is negative

        return {
            'current_balance': master_admin.balance,
            'total_earnings': total_earnings,
            'total_payouts': abs(total_payouts),  # Make positive for display
            'net_profit': net_profit,
            'total_transactions': all_transactions.count()
        }

    except Exception as e:
        print(f"Error getting master wallet statistics: {e}")
        return {
            'current_balance': 0,
            'total_earnings': 0,
            'total_payouts': 0,
            'net_profit': 0,
            'total_transactions': 0
        }


def get_master_wallet_transactions(limit=None):
    """
    Get master wallet transaction history
    """
    try:
        master_admin = get_master_admin()
        if not master_admin:
            return []

        query = MasterWalletTransaction.objects.filter(admin=master_admin).order_by('-created_at')

        if limit:
            query = query[:limit]

        return query

    except Exception as e:
        print(f"Error getting master wallet transactions: {e}")
        return []
