"""
Comprehensive Error Recovery System
Handles failed bet processing, stuck rounds, and system failures
"""
import asyncio
import logging
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from django.db import transaction
from django.utils import timezone
from datetime import timedelta
from .models import GameRound, Bet, Player, Transaction

logger = logging.getLogger(__name__)

@dataclass
class RecoveryAction:
    """Represents a recovery action to be taken"""
    action_type: str
    target_id: str
    description: str
    priority: int  # 1=critical, 2=high, 3=medium, 4=low
    timestamp: float
    retry_count: int = 0
    max_retries: int = 3

class ErrorRecoveryManager:
    """
    Manages error recovery for game state corruption and failures
    """
    
    def __init__(self):
        self.pending_recoveries: Dict[str, RecoveryAction] = {}
        self.recovery_task: Optional[asyncio.Task] = None
        self.monitoring_task: Optional[asyncio.Task] = None
        
        # Configuration
        self.check_interval = 30  # seconds
        self.stuck_round_threshold = 300  # 5 minutes
        self.failed_bet_threshold = 60   # 1 minute
        
        # Start monitoring
        self.start_monitoring()
    
    def start_monitoring(self):
        """Start background monitoring tasks"""
        if not self.recovery_task or self.recovery_task.done():
            self.recovery_task = asyncio.create_task(self._recovery_loop())
        
        if not self.monitoring_task or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
    
    async def _monitoring_loop(self):
        """Background monitoring for system issues"""
        while True:
            try:
                await asyncio.sleep(self.check_interval)
                
                # Check for stuck rounds
                await self._check_stuck_rounds()
                
                # Check for failed bets
                await self._check_failed_bets()
                
                # Check for orphaned transactions
                await self._check_orphaned_transactions()
                
                # Check for inconsistent player balances
                await self._check_player_balance_consistency()
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
    
    async def _recovery_loop(self):
        """Background recovery processing"""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                
                # Process pending recoveries by priority
                sorted_recoveries = sorted(
                    self.pending_recoveries.values(),
                    key=lambda x: (x.priority, x.timestamp)
                )
                
                for recovery in sorted_recoveries[:5]:  # Process max 5 at a time
                    try:
                        success = await self._execute_recovery(recovery)
                        
                        if success:
                            del self.pending_recoveries[recovery.target_id]
                            logger.info(f"Recovery completed: {recovery.description}")
                        else:
                            recovery.retry_count += 1
                            if recovery.retry_count >= recovery.max_retries:
                                logger.error(f"Recovery failed after {recovery.max_retries} attempts: {recovery.description}")
                                del self.pending_recoveries[recovery.target_id]
                    
                    except Exception as e:
                        logger.error(f"Error executing recovery {recovery.target_id}: {e}")
                
            except Exception as e:
                logger.error(f"Error in recovery loop: {e}")
    
    async def _check_stuck_rounds(self):
        """Check for rounds that are stuck and need recovery"""
        try:
            cutoff_time = timezone.now() - timedelta(seconds=self.stuck_round_threshold)
            
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT id, period_id, start_time, room
                    FROM polling_gameround 
                    WHERE ended = FALSE 
                    AND start_time < %s
                """, [cutoff_time])
                
                stuck_rounds = cursor.fetchall()
            
            for round_data in stuck_rounds:
                round_id, period_id, start_time, room = round_data
                
                recovery_id = f"stuck_round_{round_id}"
                if recovery_id not in self.pending_recoveries:
                    self.pending_recoveries[recovery_id] = RecoveryAction(
                        action_type="fix_stuck_round",
                        target_id=str(round_id),
                        description=f"Fix stuck round {period_id} in room {room}",
                        priority=1,  # Critical
                        timestamp=time.time()
                    )
                    logger.warning(f"Detected stuck round: {period_id}")
        
        except Exception as e:
            logger.error(f"Error checking stuck rounds: {e}")
    
    async def _check_failed_bets(self):
        """Check for bets that failed to process correctly"""
        try:
            # Check for bets without corresponding transactions
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT b.id, b.player_id, b.amount, b.round_id
                    FROM polling_bet b
                    LEFT JOIN polling_transaction t ON b.id = t.bet_id
                    WHERE t.id IS NULL
                    AND b.created_at > %s
                """, [timezone.now() - timedelta(minutes=10)])
                
                failed_bets = cursor.fetchall()
            
            for bet_data in failed_bets:
                bet_id, player_id, amount, round_id = bet_data
                
                recovery_id = f"failed_bet_{bet_id}"
                if recovery_id not in self.pending_recoveries:
                    self.pending_recoveries[recovery_id] = RecoveryAction(
                        action_type="fix_failed_bet",
                        target_id=str(bet_id),
                        description=f"Fix failed bet processing for bet {bet_id}",
                        priority=2,  # High
                        timestamp=time.time()
                    )
                    logger.warning(f"Detected failed bet: {bet_id}")
        
        except Exception as e:
            logger.error(f"Error checking failed bets: {e}")
    
    async def _check_orphaned_transactions(self):
        """Check for transactions without proper references"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # Check for transactions with invalid bet references
                cursor.execute("""
                    SELECT t.id, t.bet_id, t.amount
                    FROM polling_transaction t
                    LEFT JOIN polling_bet b ON t.bet_id = b.id
                    WHERE t.bet_id IS NOT NULL 
                    AND b.id IS NULL
                    AND t.created_at > %s
                """, [timezone.now() - timedelta(hours=1)])
                
                orphaned_transactions = cursor.fetchall()
            
            for trans_data in orphaned_transactions:
                trans_id, bet_id, amount = trans_data
                
                recovery_id = f"orphaned_transaction_{trans_id}"
                if recovery_id not in self.pending_recoveries:
                    self.pending_recoveries[recovery_id] = RecoveryAction(
                        action_type="fix_orphaned_transaction",
                        target_id=str(trans_id),
                        description=f"Fix orphaned transaction {trans_id}",
                        priority=3,  # Medium
                        timestamp=time.time()
                    )
                    logger.warning(f"Detected orphaned transaction: {trans_id}")
        
        except Exception as e:
            logger.error(f"Error checking orphaned transactions: {e}")
    
    async def _check_player_balance_consistency(self):
        """Check for player balance inconsistencies"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # Check if player balances match transaction history
                cursor.execute("""
                    SELECT p.id, p.username, p.balance,
                           COALESCE(SUM(CASE WHEN t.transaction_type IN ('deposit', 'win', 'refund') THEN t.amount ELSE 0 END), 0) as credits,
                           COALESCE(SUM(CASE WHEN t.transaction_type IN ('bet', 'withdrawal') THEN t.amount ELSE 0 END), 0) as debits
                    FROM polling_player p
                    LEFT JOIN polling_transaction t ON p.id = t.player_id
                    GROUP BY p.id, p.username, p.balance
                    HAVING p.balance != (credits - debits)
                    LIMIT 10
                """)
                
                inconsistent_players = cursor.fetchall()
            
            for player_data in inconsistent_players:
                player_id, username, balance, credits, debits = player_data
                expected_balance = credits - debits
                
                recovery_id = f"balance_inconsistency_{player_id}"
                if recovery_id not in self.pending_recoveries:
                    self.pending_recoveries[recovery_id] = RecoveryAction(
                        action_type="fix_balance_inconsistency",
                        target_id=str(player_id),
                        description=f"Fix balance inconsistency for {username}: {balance} vs {expected_balance}",
                        priority=2,  # High
                        timestamp=time.time()
                    )
                    logger.warning(f"Detected balance inconsistency for {username}")
        
        except Exception as e:
            logger.error(f"Error checking balance consistency: {e}")
    
    async def _execute_recovery(self, recovery: RecoveryAction) -> bool:
        """Execute a specific recovery action"""
        try:
            if recovery.action_type == "fix_stuck_round":
                return await self._fix_stuck_round(recovery.target_id)
            elif recovery.action_type == "fix_failed_bet":
                return await self._fix_failed_bet(recovery.target_id)
            elif recovery.action_type == "fix_orphaned_transaction":
                return await self._fix_orphaned_transaction(recovery.target_id)
            elif recovery.action_type == "fix_balance_inconsistency":
                return await self._fix_balance_inconsistency(recovery.target_id)
            else:
                logger.error(f"Unknown recovery action type: {recovery.action_type}")
                return False
        
        except Exception as e:
            logger.error(f"Error executing recovery {recovery.action_type}: {e}")
            return False
    
    async def _fix_stuck_round(self, round_id: str) -> bool:
        """Fix a stuck game round"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                # End the stuck round with a random result
                import secrets
                result_number = secrets.randbelow(10)
                
                # Determine color based on number
                if result_number in [1, 3, 7, 9]:
                    result_color = 'green'
                elif result_number in [2, 8]:
                    result_color = 'red'
                elif result_number in [0, 5]:
                    result_color = 'violet'
                else:  # 4, 6
                    result_color = 'blue'
                
                cursor.execute("""
                    UPDATE polling_gameround 
                    SET ended = TRUE, result_number = %s, result_color = %s
                    WHERE id = %s AND ended = FALSE
                """, [result_number, result_color, round_id])
                
                if cursor.rowcount > 0:
                    logger.info(f"Fixed stuck round {round_id} with result {result_number} ({result_color})")
                    return True
                
            return False
        
        except Exception as e:
            logger.error(f"Error fixing stuck round {round_id}: {e}")
            return False
    
    async def _fix_failed_bet(self, bet_id: str) -> bool:
        """Fix a failed bet by creating missing transaction"""
        try:
            with transaction.atomic():
                bet = Bet.objects.get(id=bet_id)
                
                # Create the missing debit transaction
                Transaction.objects.create(
                    player=bet.player,
                    amount=bet.amount,
                    transaction_type='bet',
                    description=f'Recovery: Bet placed on {bet.color or bet.number} for round {bet.round.period_id}',
                    bet=bet
                )
                
                logger.info(f"Fixed failed bet {bet_id} by creating missing transaction")
                return True
        
        except Exception as e:
            logger.error(f"Error fixing failed bet {bet_id}: {e}")
            return False
    
    async def _fix_orphaned_transaction(self, transaction_id: str) -> bool:
        """Fix an orphaned transaction"""
        try:
            with transaction.atomic():
                # For now, just log and mark for manual review
                logger.warning(f"Orphaned transaction {transaction_id} requires manual review")
                return True
        
        except Exception as e:
            logger.error(f"Error fixing orphaned transaction {transaction_id}: {e}")
            return False
    
    async def _fix_balance_inconsistency(self, player_id: str) -> bool:
        """Fix player balance inconsistency"""
        try:
            with transaction.atomic():
                player = Player.objects.get(id=player_id)
                
                # Recalculate balance from transactions
                from django.db.models import Sum, Q
                credits = Transaction.objects.filter(
                    player=player,
                    transaction_type__in=['deposit', 'win', 'refund']
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                debits = Transaction.objects.filter(
                    player=player,
                    transaction_type__in=['bet', 'withdrawal']
                ).aggregate(Sum('amount'))['amount__sum'] or 0
                
                correct_balance = credits - debits
                
                if player.balance != correct_balance:
                    old_balance = player.balance
                    player.balance = correct_balance
                    player.save()
                    
                    # Create adjustment transaction
                    adjustment = correct_balance - old_balance
                    Transaction.objects.create(
                        player=player,
                        amount=abs(adjustment),
                        transaction_type='admin_adjust',
                        description=f'Recovery: Balance correction from {old_balance} to {correct_balance}'
                    )
                    
                    logger.info(f"Fixed balance inconsistency for {player.username}: {old_balance} -> {correct_balance}")
                
                return True
        
        except Exception as e:
            logger.error(f"Error fixing balance inconsistency for player {player_id}: {e}")
            return False
    
    def add_manual_recovery(self, action_type: str, target_id: str, description: str, priority: int = 3):
        """Manually add a recovery action"""
        recovery_id = f"manual_{action_type}_{target_id}"
        self.pending_recoveries[recovery_id] = RecoveryAction(
            action_type=action_type,
            target_id=target_id,
            description=description,
            priority=priority,
            timestamp=time.time()
        )
        logger.info(f"Added manual recovery: {description}")
    
    def get_recovery_stats(self) -> dict:
        """Get recovery system statistics"""
        return {
            'pending_recoveries': len(self.pending_recoveries),
            'critical_recoveries': sum(1 for r in self.pending_recoveries.values() if r.priority == 1),
            'high_priority_recoveries': sum(1 for r in self.pending_recoveries.values() if r.priority == 2),
            'recovery_task_running': not (self.recovery_task and self.recovery_task.done()),
            'monitoring_task_running': not (self.monitoring_task and self.monitoring_task.done())
        }
    
    async def shutdown(self):
        """Gracefully shutdown the recovery system"""
        if self.recovery_task and not self.recovery_task.done():
            self.recovery_task.cancel()
        
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
        
        logger.info("Error recovery system shutdown")

# Global instance
error_recovery = ErrorRecoveryManager()
