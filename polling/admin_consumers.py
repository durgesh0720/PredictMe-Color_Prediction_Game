import json
import asyncio
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db.models import Count, Sum, Q
from datetime import timedelta
from .models import GameRound, AdminColorSelection, Admin, Bet, Player, AdminLog

logger = logging.getLogger(__name__)


class AdminGameConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for admin real-time game control"""

    async def connect(self):
        self.room_group_name = "admin_game_control"

        # Check admin authentication from middleware
        if not self.scope.get('authenticated') or not self.scope.get('admin'):
            logger.warning("Unauthenticated admin WebSocket connection attempt")
            await self.close(code=4001)  # Unauthorized
            return

        admin = self.scope.get('admin')
        self.admin_id = admin.id
        self.admin_username = admin.username

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        logger.info(f"Admin WebSocket connected: {self.admin_username}")

        # Send initial comprehensive game status
        await self.send_comprehensive_game_status()

        # Start periodic updates
        self.update_task = asyncio.create_task(self.periodic_updates())
    
    async def disconnect(self, close_code):
        logger.info(f"Admin WebSocket disconnected: {getattr(self, 'admin_username', 'Unknown')}, code={close_code}")

        # Cancel periodic updates
        if hasattr(self, 'update_task'):
            self.update_task.cancel()
            try:
                await self.update_task
            except asyncio.CancelledError:
                pass

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages with enhanced security validation"""
        try:
            import time

            # Validate message size to prevent DoS attacks
            if len(text_data) > 10240:  # 10KB limit
                logger.warning(f"Oversized WebSocket message from admin {self.admin_username}: {len(text_data)} bytes")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Message too large'
                }))
                return

            # Parse JSON with enhanced error handling
            try:
                data = json.loads(text_data)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error from admin {self.admin_username}: {e}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Invalid JSON format'
                }))
                return

            # Validate message structure
            if not isinstance(data, dict):
                logger.warning(f"Non-dict message from admin {self.admin_username}")
                return

            message_type = data.get('type')
            if not message_type or not isinstance(message_type, str):
                logger.warning(f"Missing or invalid message type from admin {self.admin_username}")
                return

            # Rate limiting check (simple implementation)
            current_time = time.time()
            if not hasattr(self, 'last_message_time'):
                self.last_message_time = 0
                self.message_count = 0

            if current_time - self.last_message_time < 1:  # Less than 1 second
                self.message_count += 1
                if self.message_count > 10:  # Max 10 messages per second
                    logger.warning(f"Rate limit exceeded for admin {self.admin_username}")
                    return
            else:
                self.message_count = 0

            self.last_message_time = current_time

            # Route messages to appropriate handlers
            message_handlers = {
                'get_game_status': self.send_comprehensive_game_status,
                'get_live_stats': self.send_live_betting_stats,
                'get_timer_info': self.send_timer_info,
                'select_color': lambda: self.handle_color_selection(data),
                'ping': lambda: self.send(text_data=json.dumps({'type': 'pong'})),
                'force_refresh': self.handle_force_refresh,
                'sync_state': self.handle_sync_state
            }

            handler = message_handlers.get(message_type)
            if handler:
                await handler()
            else:
                logger.warning(f"Unknown message type from admin {self.admin_username}: {message_type}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': f'Unknown message type: {message_type}'
                }))

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from admin {self.admin_username}: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Unexpected error in admin WebSocket receive: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An unexpected error occurred'
            }))

    async def handle_force_refresh(self):
        """Handle force refresh request from admin"""
        await self.send_comprehensive_game_status()
        await self.send_live_betting_stats()
        await self.send_timer_info()

    async def handle_sync_state(self):
        """Handle state synchronization request"""
        await self.send_comprehensive_game_status()
        await self.send(text_data=json.dumps({
            'type': 'state_synced',
            'message': 'State synchronized successfully'
        }))
    
    async def handle_color_selection(self, data):
        """Handle admin color selection with enhanced security validation"""
        import re

        # Enhanced input validation
        round_id = data.get('round_id', '').strip()
        color = data.get('color', '').strip().lower()

        # Validate required fields
        if not round_id or not color:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Missing round_id or color'
            }))
            return

        # Validate round_id format to prevent injection
        if not re.match(r'^[a-zA-Z0-9-_]+$', str(round_id)):
            logger.warning(f"Invalid round_id format from admin {self.admin_username}: {round_id}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid round ID format'
            }))
            return

        # Validate color against whitelist
        valid_colors = ['red', 'green', 'violet', 'blue']
        if color not in valid_colors:
            logger.warning(f"Invalid color from admin {self.admin_username}: {color}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Invalid color. Must be one of: {", ".join(valid_colors)}'
            }))
            return

        # Validate timestamp if provided (prevent replay attacks)
        timestamp = data.get('timestamp')
        if timestamp:
            import time
            current_time = int(time.time() * 1000)
            if abs(current_time - timestamp) > 30000:  # 30 second window
                logger.warning(f"Stale timestamp from admin {self.admin_username}")
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Request timestamp is too old'
                }))
                return

        try:
            # Get the round and validate it's still active
            game_round = await database_sync_to_async(GameRound.objects.get)(
                id=round_id, ended=False
            )

            # Check if round is still in selection period
            time_elapsed = (timezone.now() - game_round.start_time).total_seconds()
            ROUND_DURATION = 50  # 50 seconds total
            if time_elapsed >= ROUND_DURATION:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Round has ended, cannot select color'
                }))
                return

            # Get admin from scope (authenticated admin)
            admin = self.scope.get('admin')
            if not admin:
                # Fallback to first admin if scope doesn't have admin
                admin = await database_sync_to_async(Admin.objects.first)()

            # Create or update admin selection with proper persistence
            @database_sync_to_async
            def save_admin_selection():
                selection, created = AdminColorSelection.objects.get_or_create(
                    round=game_round,
                    defaults={
                        'admin': admin,
                        'selected_color': color,
                        'is_auto_selected': False
                    }
                )

                if not created:
                    selection.admin = admin
                    selection.selected_color = color
                    selection.is_auto_selected = False
                    selection.save()

                return selection, created

            selection, created = await save_admin_selection()

            # Broadcast color selection to all admin clients with persistence flag
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'color_selected_event',
                    'round_id': str(round_id),
                    'color': color,
                    'admin_username': admin.username if admin else 'Unknown',
                    'selection_time': selection.selection_time.isoformat(),
                    'persist_until_round_end': True,
                    'time_remaining': int(ROUND_DURATION - time_elapsed)
                }
            )

            # Send confirmation to the selecting admin
            await self.send(text_data=json.dumps({
                'type': 'color_selection_confirmed',
                'round_id': str(round_id),
                'color': color,
                'message': f'Color {color} selected for round {game_round.period_id}',
                'persist_until_round_end': True
            }))

        except GameRound.DoesNotExist:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Round not found or has ended'
            }))
        except Exception as e:
            logger.error(f"Error in handle_color_selection: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error selecting color: {str(e)}'
            }))
    
    async def send_comprehensive_game_status(self):
        """Send comprehensive real-time game status to admin"""
        try:
            # Get active rounds and recently ended rounds
            @database_sync_to_async
            def get_rounds_data():
                from datetime import timedelta
                recent_time = timezone.now() - timedelta(minutes=10)

                # Get active rounds (not ended) - Only main room
                active_rounds = GameRound.objects.filter(
                    room='main',
                    ended=False
                ).filter(
                    Q(bet__isnull=False) | Q(start_time__gte=recent_time)
                ).distinct().order_by('-start_time')

                # Get recently ended rounds
                ended_rounds = GameRound.objects.filter(
                    room='main',
                    ended=True,
                    start_time__gte=recent_time
                ).filter(
                    Q(bet__isnull=False) | Q(start_time__gte=recent_time)
                ).distinct().order_by('-start_time')

                return list(active_rounds), list(ended_rounds)

            active_rounds, ended_rounds = await get_rounds_data()
            all_rounds = active_rounds + ended_rounds

            rounds_data = []
            total_players = 0
            total_amount = 0

            for round_obj in all_rounds:
                # Get detailed betting statistics
                @database_sync_to_async
                def get_round_stats(round_id):
                    bets = Bet.objects.filter(round_id=round_id, bet_type='color')

                    color_stats = {}
                    colors = ['red', 'green', 'violet', 'blue']
                    round_total_amount = 0
                    round_players = set()

                    for color in colors:
                        color_bets = bets.filter(color=color)
                        amount = sum(bet.amount for bet in color_bets)
                        count = color_bets.count()
                        users = color_bets.values('player__username').distinct().count()

                        color_stats[color] = {
                            'count': count,
                            'amount': amount,
                            'users': users
                        }

                        round_total_amount += amount
                        for bet in color_bets:
                            round_players.add(bet.player.username)

                    return color_stats, round_total_amount, len(round_players)

                color_stats, round_amount, round_players_count = await get_round_stats(round_obj.id)

                # Get admin selection
                @database_sync_to_async
                def get_admin_selection(round_id):
                    try:
                        return AdminColorSelection.objects.select_related('admin').filter(round_id=round_id).first()
                    except Exception:
                        return None

                admin_selection = await get_admin_selection(round_obj.id)

                # Calculate time remaining
                ROUND_DURATION = 50  # 50 seconds total
                time_elapsed = (timezone.now() - round_obj.start_time).total_seconds()
                time_remaining = max(0, ROUND_DURATION - time_elapsed)

                round_data = {
                    'round_id': round_obj.id,
                    'period_id': round_obj.period_id,
                    'room': round_obj.room,
                    'ended': round_obj.ended,
                    'start_time': round_obj.start_time.isoformat(),
                    'time_remaining': int(time_remaining),
                    'can_select': time_remaining > 0 and not round_obj.ended,
                    'color_stats': color_stats,
                    'total_bets': sum(stats['count'] for stats in color_stats.values()),
                    'total_amount': round_amount,
                    'total_players': round_players_count,
                    'admin_selected_color': admin_selection.selected_color if admin_selection else None,
                    'admin_selected_by': admin_selection.admin.username if admin_selection and admin_selection.admin else None,
                    'result_number': round_obj.result_number,
                    'result_color': round_obj.result_color,
                }

                rounds_data.append(round_data)
                total_amount += round_amount
                total_players += round_players_count

            await self.send(text_data=json.dumps({
                'type': 'comprehensive_game_status',
                'rounds': rounds_data,
                'summary': {
                    'total_rounds': len(active_rounds),
                    'total_players': total_players,
                    'total_amount': total_amount,
                },
                'timestamp': timezone.now().isoformat()
            }))

        except Exception as e:
            logger.error(f"Error getting comprehensive game status: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error getting game status: {str(e)}'
            }))
    
    async def send_live_betting_stats(self):
        """Send live betting statistics"""
        try:
            @database_sync_to_async
            def get_betting_stats():
                from django.db.models import Sum, Count

                # Get current active rounds from database
                active_rounds = GameRound.objects.filter(ended=False)

                # Initialize stats for all colors
                stats = {
                    'red': {'amount': 0, 'count': 0, 'users': 0},
                    'green': {'amount': 0, 'count': 0, 'users': 0},
                    'violet': {'amount': 0, 'count': 0, 'users': 0},
                    'blue': {'amount': 0, 'count': 0, 'users': 0}
                }

                # Get betting data from database for active rounds
                if active_rounds.exists():
                    for round_obj in active_rounds:
                        # Get bets for this round grouped by color
                        round_bets = Bet.objects.filter(round=round_obj, bet_type='color')

                        for color in stats.keys():
                            color_bets = round_bets.filter(color=color)
                            color_stats = color_bets.aggregate(
                                total_amount=Sum('amount'),
                                total_count=Count('id'),
                                unique_users=Count('player', distinct=True)
                            )

                            # Handle None values from Sum aggregation
                            stats[color]['amount'] += color_stats['total_amount'] or 0
                            stats[color]['count'] += color_stats['total_count'] or 0
                            stats[color]['users'] += color_stats['unique_users'] or 0

                return stats, active_rounds.count()

            stats, active_rounds_count = await get_betting_stats()

            await self.send(text_data=json.dumps({
                'type': 'live_betting_stats',
                'stats': stats,
                'active_rounds_count': active_rounds_count,
                'timestamp': timezone.now().isoformat()
            }))

        except Exception as e:
            logger.error(f"Error getting live betting stats: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error getting betting stats: {str(e)}'
            }))

    async def send_timer_info(self):
        """Send timer information for all active rounds"""
        try:
            @database_sync_to_async
            def get_timer_data():
                active_rounds = GameRound.objects.filter(ended=False).order_by('-start_time')
                timers = []

                for round_obj in active_rounds:
                    ROUND_DURATION = 50  # 50 seconds total
                    time_elapsed = (timezone.now() - round_obj.start_time).total_seconds()
                    time_remaining = max(0, ROUND_DURATION - time_elapsed)

                    timers.append({
                        'round_id': round_obj.id,
                        'period_id': round_obj.period_id,
                        'room': round_obj.room,
                        'time_remaining': int(time_remaining),
                        'phase': 'betting' if time_remaining > 10 else 'result' if time_remaining > 0 else 'ended',
                        'can_bet': time_remaining > 10,
                        'can_select': time_remaining > 0,
                    })

                return timers

            timers = await get_timer_data()

            await self.send(text_data=json.dumps({
                'type': 'timer_info',
                'success': True,
                'timers': timers,
                'timestamp': timezone.now().isoformat()
            }))

        except Exception as e:
            logger.error(f"Error getting timer info: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error getting timer info: {str(e)}'
            }))

    async def periodic_updates(self):
        """Send periodic updates to admin clients with optimized intervals"""
        last_round_states = {}  # Track round states to detect changes

        try:
            while True:
                # Optimized update interval - reduced from 1 second to 3 seconds
                # This reduces API calls while maintaining good user experience
                await asyncio.sleep(3)

                # Get current round states
                current_round_states = await self.get_current_round_states()

                # Check for round state changes and broadcast events
                await self.check_and_broadcast_state_changes(last_round_states, current_round_states)

                # Update last known states
                last_round_states = current_round_states.copy()

                # Send comprehensive status every 2 seconds
                if hasattr(self, '_update_counter'):
                    self._update_counter += 1
                else:
                    self._update_counter = 1

                if self._update_counter % 2 == 0:  # Every 6 seconds (3*2)
                    await self.send_comprehensive_game_status()

                if self._update_counter % 4 == 0:  # Every 12 seconds (3*4)
                    await self.send_live_betting_stats()

                # Send timer info less frequently since we get real-time sync from user consumer
                if self._update_counter % 2 == 0:  # Every 6 seconds (3*2)
                    await self.send_timer_info()

        except asyncio.CancelledError:
            logger.info(f"Periodic updates cancelled for admin {self.admin_username}")
        except Exception as e:
            logger.error(f"Error in periodic updates: {e}")

    async def get_current_round_states(self):
        """Get current state of all rounds"""
        @database_sync_to_async
        def get_states():
            rounds = GameRound.objects.filter(ended=False).order_by('-start_time')
            states = {}

            for round_obj in rounds:
                time_elapsed = (timezone.now() - round_obj.start_time).total_seconds()
                ROUND_DURATION = 50
                time_remaining = max(0, ROUND_DURATION - time_elapsed)

                states[round_obj.id] = {
                    'round_id': round_obj.id,
                    'period_id': round_obj.period_id,
                    'ended': round_obj.ended,
                    'time_remaining': int(time_remaining),
                    'phase': 'betting' if time_remaining > 10 else 'result' if time_remaining > 0 else 'ended'
                }

            return states

        return await get_states()

    async def check_and_broadcast_state_changes(self, last_states, current_states):
        """Check for state changes and broadcast appropriate events"""
        # Check for rounds that just ended
        for round_id, current_state in current_states.items():
            last_state = last_states.get(round_id)

            if last_state and last_state['phase'] != 'ended' and current_state['phase'] == 'ended':
                # Round just ended
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'round_ended_event',
                        'round_id': str(round_id),
                        'period_id': current_state['period_id']
                    }
                )

        # Check for new rounds (rounds in current_states but not in last_states)
        for round_id, current_state in current_states.items():
            if round_id not in last_states:
                # New round started
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'new_round_started_event',
                        'round_id': str(round_id),
                        'period_id': current_state['period_id']
                    }
                )

    # WebSocket event handlers
    async def color_selected(self, event):
        """Handle color selection broadcast (legacy)"""
        await self.send(text_data=json.dumps(event))

    async def color_selected_event(self, event):
        """Handle enhanced color selection broadcast with persistence"""
        await self.send(text_data=json.dumps({
            'type': 'color_selected',
            'round_id': event['round_id'],
            'color': event['color'],
            'admin_username': event['admin_username'],
            'selection_time': event['selection_time'],
            'persist_until_round_end': event['persist_until_round_end'],
            'time_remaining': event['time_remaining']
        }))

    async def round_ended(self, event):
        """Handle round ended broadcast (legacy)"""
        await self.send(text_data=json.dumps(event))
        # Send updated game status after round ends
        await self.send_comprehensive_game_status()

    async def new_round_started(self, event):
        """Handle new round started broadcast (legacy)"""
        await self.send(text_data=json.dumps(event))
        # Send updated game status after new round starts
        await self.send_comprehensive_game_status()

    async def round_ended_event(self, event):
        """Handle enhanced round ended broadcast with immediate UI updates"""
        await self.send(text_data=json.dumps({
            'type': 'round_ended',
            'round_id': event['round_id'],
            'period_id': event['period_id'],
            'trigger_card_update': True
        }))
        # Send updated game status immediately
        await self.send_comprehensive_game_status()

    async def new_round_started_event(self, event):
        """Handle enhanced new round started broadcast with immediate UI updates"""
        await self.send(text_data=json.dumps({
            'type': 'new_round_started',
            'round_id': event['round_id'],
            'period_id': event['period_id'],
            'trigger_card_refresh': True
        }))
        # Send updated game status immediately
        await self.send_comprehensive_game_status()

    async def game_status_update(self, event):
        """Handle game status update broadcast"""
        await self.send(text_data=json.dumps(event))

    async def timer_sync_update(self, event):
        """Handle timer synchronization update from user game consumer"""
        await self.send(text_data=json.dumps({
            'type': 'timer_sync',
            'round_id': event['round_id'],
            'time_remaining': event['time_remaining'],
            'phase': event['phase'],
            'room': event['room'],
            'timestamp': event['timestamp']
        }))

    async def bet_placed_admin_update(self, event):
        """Handle bet placed notification for admin real-time updates"""
        await self.send(text_data=json.dumps({
            'type': 'bet_placed_update',
            'round_id': event['round_id'],
            'username': event['username'],
            'bet_type': event['bet_type'],
            'color': event['color'],
            'number': event['number'],
            'amount': event['amount'],
            'room': event['room'],
            'timestamp': event['timestamp']
        }))

        # Trigger immediate betting stats refresh
        await self.send_live_betting_stats()

    async def timer_update(self, event):
        """Handle timer update from user game consumer for perfect synchronization"""
        await self.send(text_data=json.dumps({
            'type': 'timer_update',
            'time_remaining': event['time_remaining'],
            'phase': event['phase'],
            'round_id': event['round_id'],
            'timestamp': event['timestamp'],
            'server_timestamp': event['server_timestamp'],
            'round_start_time': event['round_start_time']
        }))


class AdminDashboardConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time admin dashboard updates"""

    async def connect(self):
        self.room_group_name = 'admin_dashboard'

        # Join dashboard group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave dashboard group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'get_dashboard_data':
                await self.send_dashboard_data()

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def send_dashboard_data(self):
        """Send comprehensive dashboard data"""
        try:
            # Get statistics
            stats = await self.get_dashboard_statistics()

            # Get betting activity data
            betting_activity = await self.get_betting_activity()

            # Get game distribution
            game_distribution = await self.get_game_distribution()

            # Get recent activity
            recent_activity = await self.get_recent_activity()

            # Get system alerts
            alerts = await self.get_system_alerts()

            await self.send(text_data=json.dumps({
                'type': 'dashboard_data',
                'stats': stats,
                'betting_activity': betting_activity,
                'game_distribution': game_distribution,
                'recent_activity': recent_activity,
                'alerts': alerts
            }))

        except Exception as e:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Error getting dashboard data: {str(e)}'
            }))

    async def get_dashboard_statistics(self):
        """Get real-time dashboard statistics"""
        @database_sync_to_async
        def get_stats():
            today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

            # Total players
            total_players = Player.objects.count()

            # Active players (last 24 hours)
            active_players = Player.objects.filter(
                bet__created_at__gte=timezone.now() - timedelta(hours=24)
            ).distinct().count()

            # Bets today
            total_bets = Bet.objects.filter(created_at__gte=today).count()

            # Betting volume today
            betting_volume = Bet.objects.filter(
                created_at__gte=today
            ).aggregate(total=Sum('amount'))['total'] or 0

            return {
                'total_players': total_players,
                'active_players': active_players,
                'total_bets': total_bets,
                'betting_volume': betting_volume
            }

        return await get_stats()

    async def get_betting_activity(self):
        """Get hourly betting activity for the last 24 hours"""
        @database_sync_to_async
        def get_activity():
            now = timezone.now()
            hours = []
            values = []

            for i in range(24):
                hour_start = now - timedelta(hours=i+1)
                hour_end = now - timedelta(hours=i)

                bets_count = Bet.objects.filter(
                    created_at__gte=hour_start,
                    created_at__lt=hour_end
                ).count()

                hours.append(hour_start.strftime('%H:00'))
                values.append(bets_count)

            # Reverse to show chronological order
            hours.reverse()
            values.reverse()

            return {
                'labels': hours,
                'values': values
            }

        return await get_activity()

    async def get_game_distribution(self):
        """Get game type distribution"""
        @database_sync_to_async
        def get_distribution():
            today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

            game_types = ['parity', 'sapre', 'bcone', 'noki']
            values = []

            for game_type in game_types:
                count = Bet.objects.filter(
                    round__game_type=game_type,
                    created_at__gte=today
                ).count()
                values.append(count)

            return {
                'labels': [gt.title() for gt in game_types],
                'values': values
            }

        return await get_distribution()

    async def get_recent_activity(self):
        """Get recent admin activity"""
        @database_sync_to_async
        def get_activity():
            logs = AdminLog.objects.select_related('admin').order_by('-created_at')[:10]

            activities = []
            for log in logs:
                activities.append({
                    'action': f"{log.admin.username if log.admin else 'System'}: {log.description}",
                    'time': log.created_at.strftime('%H:%M:%S')
                })

            return activities

        return await get_activity()

    async def get_system_alerts(self):
        """Get system alerts and warnings"""
        @database_sync_to_async
        def get_alerts():
            alerts = []

            # Check for inactive games
            inactive_games = GameRound.objects.filter(
                ended=False,
                start_time__lt=timezone.now() - timedelta(minutes=10)
            ).count()

            if inactive_games > 0:
                alerts.append({
                    'type': 'warning',
                    'message': f'{inactive_games} game rounds have been running for more than 10 minutes'
                })

            # Check for high betting volume
            today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_volume = Bet.objects.filter(
                created_at__gte=today
            ).aggregate(total=Sum('amount'))['total'] or 0

            if today_volume > 100000:  # Alert if volume exceeds 100k
                alerts.append({
                    'type': 'info',
                    'message': f'High betting volume today: ₹{today_volume}'
                })

            return alerts

        return await get_alerts()

    # WebSocket event handlers
    async def dashboard_update(self, event):
        """Handle dashboard update broadcast"""
        await self.send_dashboard_data()


class AdminUserManagementConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time user management updates"""

    async def connect(self):
        self.room_group_name = 'admin_user_management'

        # Check admin authentication
        if not self.scope.get('authenticated') or not self.scope.get('admin'):
            logger.warning("Unauthenticated admin WebSocket connection attempt")
            await self.close(code=4001)  # Unauthorized
            return

        admin = self.scope.get('admin')
        self.admin_id = admin.id
        self.admin_username = admin.username

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        logger.info(f"Admin User Management WebSocket connected: {self.admin_username}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"Admin User Management WebSocket disconnected: {getattr(self, 'admin_username', 'Unknown')}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'request_user_stats':
                await self.send_user_stats()
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def send_user_stats(self):
        """Send user statistics"""
        try:
            stats = await self.get_user_statistics()
            await self.send(text_data=json.dumps({
                'type': 'user_stats_update',
                'stats': stats
            }))
        except Exception as e:
            logger.error(f"Error sending user stats: {e}")

    @database_sync_to_async
    def get_user_statistics(self):
        """Get user statistics"""
        from django.db.models import Count, Sum

        total_users = Player.objects.count()
        active_users = Player.objects.filter(is_active=True).count()

        today = timezone.now().date()
        new_today = Player.objects.filter(created_at__date=today).count()

        # High value users (with balance > 1000)
        high_value = Player.objects.filter(wallet_balance__gt=1000).count()

        return {
            'total_users': total_users,
            'active_users': active_users,
            'new_today': new_today,
            'high_value': high_value
        }


class AdminFinancialConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time financial management updates"""

    async def connect(self):
        self.room_group_name = 'admin_financial'

        # Check admin authentication
        if not self.scope.get('authenticated') or not self.scope.get('admin'):
            logger.warning("Unauthenticated admin WebSocket connection attempt")
            await self.close(code=4001)  # Unauthorized
            return

        admin = self.scope.get('admin')
        self.admin_id = admin.id
        self.admin_username = admin.username

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

        logger.info(f"Admin Financial WebSocket connected: {self.admin_username}")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        logger.info(f"Admin Financial WebSocket disconnected: {getattr(self, 'admin_username', 'Unknown')}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'request_financial_update':
                await self.send_financial_stats()
            elif message_type == 'request_chart_data':
                period = data.get('period', '7d')
                await self.send_chart_data(period)
            elif message_type == 'ping':
                await self.send(text_data=json.dumps({'type': 'pong'}))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))

    async def send_financial_stats(self):
        """Send financial statistics"""
        try:
            stats = await self.get_financial_statistics()
            await self.send(text_data=json.dumps({
                'type': 'financial_stats_update',
                'stats': stats
            }))
        except Exception as e:
            logger.error(f"Error sending financial stats: {e}")

    async def send_chart_data(self, period):
        """Send chart data for specified period"""
        try:
            chart_data = await self.get_chart_data(period)
            await self.send(text_data=json.dumps({
                'type': 'chart_data_update',
                'period': period,
                'data': chart_data
            }))
        except Exception as e:
            logger.error(f"Error sending chart data: {e}")

    @database_sync_to_async
    def get_financial_statistics(self):
        """Get financial statistics"""
        from django.db.models import Sum, Count
        from polling.models import WalletTransaction

        # Calculate total revenue (all bet amounts)
        total_revenue = Bet.objects.aggregate(
            total=Sum('amount')
        )['total'] or 0

        # Calculate deposits and withdrawals
        deposits = WalletTransaction.objects.filter(
            transaction_type='deposit',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        withdrawals = WalletTransaction.objects.filter(
            transaction_type='withdrawal',
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # Calculate profit margin
        profit_margin = ((total_revenue - withdrawals) / max(total_revenue, 1)) * 100

        return {
            'total_revenue': total_revenue,
            'total_deposits': deposits,
            'total_withdrawals': withdrawals,
            'profit_margin': round(profit_margin, 2)
        }

    @database_sync_to_async
    def get_chart_data(self, period):
        """Get chart data for specified period"""
        from django.db.models import Sum, Count
        from datetime import timedelta

        # Calculate date range based on period
        end_date = timezone.now().date()
        if period == '7d':
            start_date = end_date - timedelta(days=7)
        elif period == '30d':
            start_date = end_date - timedelta(days=30)
        elif period == '90d':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)

        # Get daily betting data
        daily_data = []
        current_date = start_date

        while current_date <= end_date:
            daily_bets = Bet.objects.filter(
                created_at__date=current_date
            ).aggregate(
                total_amount=Sum('amount'),
                total_count=Count('id')
            )

            daily_data.append({
                'date': current_date.isoformat(),
                'amount': daily_bets['total_amount'] or 0,
                'count': daily_bets['total_count'] or 0
            })

            current_date += timedelta(days=1)

        return daily_data


# Background task to periodically update admin clients
async def admin_status_updater():
    """Background task to send periodic updates to admin clients"""
    from channels.layers import get_channel_layer

    channel_layer = get_channel_layer()

    while True:
        try:
            # Get current game status with proper async wrapper
            @database_sync_to_async
            def get_active_rounds():
                return list(GameRound.objects.filter(ended=False))

            active_rounds = await get_active_rounds()

            if active_rounds:
                # Send update to all admin clients
                await channel_layer.group_send(
                    "admin_game_control",
                    {
                        'type': 'status_update',
                        'message': 'Periodic status update',
                        'active_rounds_count': len(active_rounds)
                    }
                )

            # Wait 10 seconds before next update (optimized from 5 seconds)
            await asyncio.sleep(10)

        except Exception as e:
            print(f"Error in admin status updater: {e}")
            await asyncio.sleep(10)  # Wait longer on error
