"""
Management command for sending bulk notifications
Usage: python manage.py send_notifications --type maintenance --message "Scheduled maintenance tonight"
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from polling.models import Player, NotificationType
from polling.notification_service import NotificationService, notify_system_announcement
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send bulk notifications to users'

    def add_arguments(self, parser):
        parser.add_argument(
            '--type',
            type=str,
            required=True,
            choices=['maintenance', 'announcement', 'feature', 'security'],
            help='Type of notification to send'
        )
        
        parser.add_argument(
            '--title',
            type=str,
            required=True,
            help='Notification title'
        )
        
        parser.add_argument(
            '--message',
            type=str,
            required=True,
            help='Notification message'
        )
        
        parser.add_argument(
            '--priority',
            type=str,
            default='normal',
            choices=['low', 'normal', 'high', 'urgent'],
            help='Notification priority (default: normal)'
        )
        
        parser.add_argument(
            '--verified-only',
            action='store_true',
            help='Send only to email-verified users'
        )
        
        parser.add_argument(
            '--active-only',
            action='store_true',
            default=True,
            help='Send only to active users (default: True)'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be sent without actually sending'
        )

    def handle(self, *args, **options):
        notification_type = options['type']
        title = options['title']
        message = options['message']
        priority = options['priority']
        verified_only = options['verified_only']
        active_only = options['active_only']
        dry_run = options['dry_run']

        # Build user query
        users = Player.objects.all()
        
        if active_only:
            users = users.filter(is_active=True)
        
        if verified_only:
            users = users.filter(email_verified=True)
        
        user_count = users.count()
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING(f'DRY RUN: Would send "{title}" to {user_count} users')
            )
            return
        
        if user_count == 0:
            self.stdout.write(
                self.style.WARNING('No users match the criteria')
            )
            return
        
        # Confirm before sending
        confirm = input(f'Send "{title}" to {user_count} users? (y/N): ')
        if confirm.lower() != 'y':
            self.stdout.write(self.style.WARNING('Cancelled'))
            return
        
        # Send notifications
        success_count = 0
        error_count = 0
        
        self.stdout.write(f'Sending notifications to {user_count} users...')
        
        for user in users:
            try:
                notify_system_announcement(
                    user=user,
                    title=title,
                    message=message,
                    priority=priority
                )
                success_count += 1
                
                if success_count % 100 == 0:
                    self.stdout.write(f'Sent {success_count}/{user_count}...')
                    
            except Exception as e:
                error_count += 1
                logger.error(f'Error sending notification to {user.username}: {e}')
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Notification sending complete!\n'
                f'Success: {success_count}\n'
                f'Errors: {error_count}\n'
                f'Total: {user_count}'
            )
        )
        
        if error_count > 0:
            self.stdout.write(
                self.style.WARNING(f'Check logs for error details')
            )
