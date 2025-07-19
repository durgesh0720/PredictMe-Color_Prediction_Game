from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from polling.models import WithdrawalRequest
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Check status of pending Razorpay payouts'

    def add_arguments(self, parser):
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Check payouts from last N hours (default: 24)'
        )

    def handle(self, *args, **options):
        hours = options['hours']
        cutoff_time = timezone.now() - timedelta(hours=hours)
        
        # Get pending withdrawals with payment references
        pending_withdrawals = WithdrawalRequest.objects.filter(
            status='approved',
            payment_reference__isnull=False,
            approved_at__gte=cutoff_time
        )
        
        self.stdout.write(f"Checking {pending_withdrawals.count()} pending payouts...")
        
        updated_count = 0
        failed_count = 0
        
        for withdrawal in pending_withdrawals:
            try:
                success, message = withdrawal.check_payout_status()
                if success:
                    if 'completed' in message.lower():
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f"✅ Withdrawal {withdrawal.id}: {message}")
                        )
                    elif 'failed' in message.lower():
                        failed_count += 1
                        self.stdout.write(
                            self.style.ERROR(f"❌ Withdrawal {withdrawal.id}: {message}")
                        )
                    else:
                        self.stdout.write(f"ℹ️ Withdrawal {withdrawal.id}: {message}")
                else:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ Withdrawal {withdrawal.id}: {message}")
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Error checking withdrawal {withdrawal.id}: {str(e)}")
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✅ Payout status check complete:\n"
                f"   - {updated_count} completed\n"
                f"   - {failed_count} failed\n"
                f"   - {pending_withdrawals.count() - updated_count - failed_count} still pending"
            )
        )
