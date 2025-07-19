# consumers.py
import json
import secrets
import asyncio
import logging
import hashlib
import time
from .models import Player, GameRound, Bet, AdminColorSelection
from .wallet_utils import place_bet_with_wallet, process_bet_result_with_master_wallet, validate_bet_amount
from .notification_service import notify_game_result, notify_wallet_transaction
from .secure_random import secure_random
from .websocket_reliability import reliable_ws_manager
from .timer_sync import server_timer
from .responsible_gambling import responsible_gambling
from .monitoring import monitoring
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from django.db import transaction

logger = logging.getLogger(__name__)

# Global game state management
game_rooms = {}  # {room_name: {'round': GameRound, 'timer_task': Task, 'players': set(), 'bets': {}, 'lock': asyncio.Lock()}}
game_rooms_lock = asyncio.Lock()  # Global lock for game_rooms access
ROUND_DURATION = 50  # 50 seconds total as per requirements
BETTING_DURATION = 40  # 40 seconds for betting, 10 seconds for results/admin selection
HEARTBEAT_INTERVAL = 2  # Send heartbeat every 2 seconds

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"game_{self.room_name}"

        # Get user information from session
        session = self.scope.get('session', {})

        # Check if user is authenticated
        if not session.get('is_authenticated'):
            logger.warning(f"Unauthenticated WebSocket connection attempt to room {self.room_name}")
            await self.close(code=4001)  # Unauthorized
            return

        # Get authenticated user information
        self.user_id = session.get('user_id')
        self.username = session.get('username')

        if not self.user_id or not self.username:
            logger.warning(f"Missing user credentials in session for room {self.room_name}")
            await self.close(code=4001)  # Unauthorized
            return

        # Verify user exists and is active
        try:
            player = await database_sync_to_async(Player.objects.get)(
                id=self.user_id,
                username=self.username,
                is_active=True
            )
        except Player.DoesNotExist:
            logger.warning(f"User {self.username} (ID: {self.user_id}) not found or inactive")
            await self.close(code=4001)  # User not found or inactive
            return

        # Initialize room if it doesn't exist with proper locking
        async with game_rooms_lock:
            if self.room_name not in game_rooms:
                await self.initialize_room()

            # Add player to room
            game_rooms[self.room_name]['players'].add(self.username)

        # Join room group
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()
        logger.info(f"WebSocket connected: user={self.username}, room={self.room_name}")

        # Record WebSocket connection for monitoring
        monitoring.record_websocket_event('connect')

        # Send current game state to the new player
        await self.send_game_state()

        # Notify other players
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'player_joined',
                'username': self.username,
                'player_count': len(game_rooms[self.room_name]['players'])
            }
        )

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected: user={getattr(self, 'username', 'Unknown')}, room={self.room_name}, code={close_code}")

        # Record WebSocket disconnection for monitoring
        monitoring.record_websocket_event('disconnect')

        # Remove player from room with proper locking
        async with game_rooms_lock:
            if self.room_name in game_rooms and hasattr(self, 'username'):
                game_rooms[self.room_name]['players'].discard(self.username)

                # Clean up empty game rooms to prevent memory leaks
                if len(game_rooms[self.room_name]['players']) == 0:
                    # Get room data before cleanup
                    room_data = game_rooms[self.room_name]
                    game_round = room_data['round']

                    # Check if round has expired and needs to be ended
                    time_elapsed = (timezone.now() - game_round.start_time).total_seconds()
                    if time_elapsed >= ROUND_DURATION and not game_round.ended:
                        logger.info(f"Round {game_round.period_id} has expired ({time_elapsed:.1f}s), ending it before cleanup")
                        # Cancel timer task if exists
                        if room_data.get('timer_task'):
                            room_data['timer_task'].cancel()
                        # End the round properly
                        try:
                            await self.end_round()
                        except Exception as e:
                            logger.error(f"Error ending expired round during disconnect: {e}")
                            # Fallback: mark round as ended in database
                            try:
                                await database_sync_to_async(
                                    GameRound.objects.filter(id=game_round.id).update
                                )(ended=True)
                                logger.info(f"Fallback: marked round {game_round.period_id} as ended")
                            except Exception as fallback_error:
                                logger.error(f"Fallback round ending failed: {fallback_error}")
                    else:
                        # Cancel timer task if exists (for active rounds)
                        if room_data.get('timer_task'):
                            room_data['timer_task'].cancel()

                    # Remove empty room
                    del game_rooms[self.room_name]
                    logger.info(f"Cleaned up empty game room: {self.room_name}")
                else:
                    # Notify other players
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'player_left',
                            'username': self.username,
                            'player_count': len(game_rooms[self.room_name]['players'])
                        }
                    )

        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            if message_type == 'place_bet':
                await self.handle_bet(data)
            elif message_type == 'get_game_state':
                await self.send_game_state()
            elif message_type == 'message_ack':
                # Handle message acknowledgment
                message_id = data.get('message_id')
                if message_id:
                    await reliable_ws_manager.acknowledge_message(message_id, self.channel_name)
            elif message_type == 'ping':
                # Respond to ping for connection health check
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': time.time()
                }))

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error from user {self.username}: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid JSON format'
            }))
        except Exception as e:
            logger.error(f"Unexpected error in receive from user {self.username}: {e}")
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'An unexpected error occurred'
            }))

    async def handle_bet(self, data):
        bet_type = data.get('bet_type', 'color')
        color = data.get('color')
        number = data.get('number')
        amount = data.get('amount', 10)

        # Validate amount first
        try:
            amount = int(amount)
        except (ValueError, TypeError):
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid bet amount format'
            }))
            return

        if amount <= 0 or amount > 10000:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Bet amount must be between 1 and 10000'
            }))
            return

        # Validate bet type and values
        if bet_type == 'color':
            if not color or color not in ['red', 'green', 'violet', 'blue']:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Invalid color selection'
                }))
                return
        elif bet_type == 'number':
            try:
                number = int(number)
            except (ValueError, TypeError):
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Invalid number format'
                }))
                return

            if not (0 <= number <= 9):
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Number must be between 0 and 9'
                }))
                return
        else:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid bet type'
            }))
            return

        # Server-authoritative timing validation
        client_timestamp = data.get('timestamp')
        is_valid, reason = server_timer.validate_bet_timing(self.room_name, client_timestamp)

        if not is_valid:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Bet rejected: {reason}'
            }))
            return

        # Responsible gambling validation
        player = await self.get_or_create_player(self.username)
        if not player:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Player authentication failed'
            }))
            return

        rg_valid, rg_reason = await responsible_gambling.validate_bet(str(player.id), amount)
        if not rg_valid:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': f'Responsible gambling limit: {rg_reason}',
                'type_detail': 'responsible_gambling'
            }))
            return

        # Check if betting is still allowed and get room data
        room_data = game_rooms.get(self.room_name)
        if not room_data or not room_data.get('round') or room_data['round'].ended:
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Betting is closed for this round'
            }))
            return

        # Use room-specific lock to prevent race conditions in bet processing
        async with room_data['lock']:
            # Get authenticated player (refresh from database)
            player = await self.get_or_create_player(self.username)

            if not player:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'Player authentication failed'
                }))
                return

            # Check if player already has a bet for this round
            @database_sync_to_async
            def check_existing_bet():
                return Bet.objects.filter(player=player, round=room_data['round']).exists()

            has_existing_bet = await check_existing_bet()

            if has_existing_bet:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'You can only place one bet per round. Wait for the next round to place another bet.'
                }))
                return

            # Validate bet amount and place bet with wallet transaction
            @database_sync_to_async
            def place_bet():
                return place_bet_with_wallet(player, room_data['round'], bet_type, color, number, amount)

            success, bet, error_message = await place_bet()

            if not success:
                # Record bet processing error for monitoring
                monitoring.record_error('bet_processing')

                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': error_message or 'Failed to place bet. Please try again.'
                }))
                return

            # Store bet in room data
            bet_key = f"{self.username}_{bet_type}_{color or number}"
            room_data['bets'][bet_key] = {
                'username': self.username,
                'bet_type': bet_type,
                'color': color,
                'number': number,
                'amount': amount,
                'bet_id': bet.id
            }

            # Notify all players about the bet
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'bet_placed',
                    'username': self.username,
                    'bet_type': bet_type,
                    'color': color,
                    'number': number,
                    'amount': amount,
                    'player_balance': player.balance
                }
            )

            # Notify admin panel about the new bet for real-time statistics
            await self.channel_layer.group_send(
                "admin_game_control",
                {
                    'type': 'bet_placed_admin_update',
                    'round_id': room_data['round'].id,
                    'username': self.username,
                    'bet_type': bet_type,
                    'color': color,
                    'number': number,
                    'amount': amount,
                    'room': self.room_name,
                    'timestamp': timezone.now().timestamp()
                }
            )

    # Helper methods
    async def initialize_room(self):
        """Initialize a new game room with a fresh round - Only allow main room"""
        # Only allow main room to run
        if self.room_name != 'main':
            logger.warning(f"Attempted to initialize non-main room: {self.room_name}")
            return

        # If room already exists in memory, just add player and update time
        if self.room_name in game_rooms:
            room_data = game_rooms[self.room_name]
            room_data['players'].add(self.username)

            # Update time remaining based on actual elapsed time
            game_round = room_data['round']
            time_elapsed = (timezone.now() - game_round.start_time).total_seconds()
            accurate_time_remaining = max(0, ROUND_DURATION - time_elapsed)
            room_data['time_remaining'] = int(accurate_time_remaining)

            logger.info(f"Player {self.username} joined existing room {self.room_name}, time remaining: {accurate_time_remaining:.1f}s")
            return

        # Check if there's already an active round in any room
        existing_active_round = await database_sync_to_async(
            GameRound.objects.filter(ended=False).first
        )()

        if existing_active_round:
            # Check if the existing round has expired
            time_elapsed = (timezone.now() - existing_active_round.start_time).total_seconds()
            time_remaining = max(0, ROUND_DURATION - time_elapsed)

            if time_elapsed >= ROUND_DURATION:
                # Round has expired, end it and create a new one
                logger.info(f"Existing round {existing_active_round.period_id} has expired ({time_elapsed:.1f}s), ending it")
                await database_sync_to_async(
                    GameRound.objects.filter(id=existing_active_round.id).update
                )(ended=True)

                # Create new game round
                game_round = await database_sync_to_async(GameRound.objects.create)(
                    room='main',  # Force main room
                    start_time=timezone.now()
                )
                time_remaining = ROUND_DURATION  # New round starts with full duration
                logger.info(f"Created new round after expiring old one: {game_round.period_id}")
            else:
                # Use existing active round
                game_round = existing_active_round
                logger.info(f"Using existing active round: {game_round.period_id}, elapsed: {time_elapsed:.1f}s, remaining: {time_remaining:.1f}s")
        else:
            # Create new game round only for main room
            game_round = await database_sync_to_async(GameRound.objects.create)(
                room='main',  # Force main room
                start_time=timezone.now()
            )
            time_remaining = ROUND_DURATION  # New round starts with full duration
            logger.info(f"Created new round for main room: {game_round.period_id}")

        game_rooms[self.room_name] = {
            'round': game_round,
            'timer_task': None,
            'players': {self.username},  # Add current player to the set
            'bets': {},
            'time_remaining': int(time_remaining),  # Use calculated time remaining
            'lock': asyncio.Lock()  # Room-specific lock for bet processing
        }

        # Only start a new timer if there isn't already one running for this round
        existing_timer = game_rooms[self.room_name].get('timer_task')

        if existing_timer and not existing_timer.done():
            # Timer is already running for this round, don't start a new one
            logger.info(f"Timer already running for round {game_round.period_id}, not starting new timer")
        else:
            # Cancel any existing timer task before starting new one
            if existing_timer:
                existing_timer.cancel()
                try:
                    await existing_timer
                except asyncio.CancelledError:
                    pass

            # Start the server-authoritative timer
            if time_remaining > 0:
                # Register callbacks for timer events
                server_timer.register_phase_change_callback(
                    self.room_name,
                    self.handle_phase_change
                )
                server_timer.register_timer_update_callback(
                    self.room_name,
                    self.handle_timer_update
                )

                # Start the server-authoritative timer
                timer_started = await server_timer.start_round_timer(self.room_name, game_round)

                if timer_started:
                    logger.info(f"Started server-authoritative timer for round {game_round.period_id}")
                else:
                    logger.error(f"Failed to start server-authoritative timer for round {game_round.period_id}")
            else:
                logger.info(f"Round {game_round.period_id} has already ended, not starting timer")

    async def get_or_create_player(self, username):
        """Get authenticated player with better error handling"""
        try:
            # First try with both ID and username
            if hasattr(self, 'user_id') and self.user_id:
                player = await database_sync_to_async(Player.objects.get)(
                    id=self.user_id,
                    username=username,
                    is_active=True
                )
            else:
                # Fallback to username only if no user_id
                player = await database_sync_to_async(Player.objects.get)(
                    username=username,
                    is_active=True
                )
                # Update user_id for future use
                self.user_id = player.id

            # Refresh player data to ensure latest state
            await database_sync_to_async(player.refresh_from_db)()
            return player

        except Player.DoesNotExist:
            logger.error(f"Player {username} (ID: {getattr(self, 'user_id', 'unknown')}) not found during bet placement")

            # Try to find player by username only as last resort
            try:
                player = await database_sync_to_async(Player.objects.get)(
                    username=username,
                    is_active=True
                )
                self.user_id = player.id
                logger.info(f"Found player {username} by username, updated user_id to {player.id}")
                return player
            except Player.DoesNotExist:
                logger.error(f"Player {username} not found in database at all")
                return None

        except Exception as e:
            logger.error(f"Error retrieving player {username}: {e}")
            return None



    async def send_game_state(self):
        """Send current game state to the player"""
        room_data = game_rooms.get(self.room_name)
        if not room_data:
            return

        player = await self.get_or_create_player(self.username)
        if not player:
            logger.error(f"Failed to get player {self.username} for game state")
            return

        # Get server-authoritative timing
        game_round = room_data['round']
        accurate_time_remaining, current_phase = server_timer.get_accurate_time_remaining(self.room_name)

        # Update room data with server-authoritative time
        room_data['time_remaining'] = int(accurate_time_remaining)

        # Check if player has already placed a bet in this round
        @database_sync_to_async
        def get_player_bet():
            try:
                return Bet.objects.filter(player=player, round=game_round).first()
            except Exception:
                return None

        existing_bet = await get_player_bet()

        # Get all bets for this round to show existing bets
        @database_sync_to_async
        def get_round_bets():
            try:
                return list(Bet.objects.filter(round=game_round).select_related('player'))
            except Exception:
                return []

        round_bets = await get_round_bets()

        # Prepare existing bets data for frontend
        existing_bets = []
        for bet in round_bets:
            existing_bets.append({
                'username': bet.player.username,
                'color': bet.color,
                'amount': bet.amount,
                'bet_type': bet.bet_type,
                'number': bet.number
            })

        # Get server synchronization data
        sync_data = server_timer.get_sync_data(self.room_name)

        # Prepare game state data with server synchronization
        game_state_data = {
            'type': 'game_state',
            'time_remaining': int(accurate_time_remaining),
            'player_balance': player.balance,
            'players_count': len(room_data['players']),
            'round_id': room_data['round'].id,
            'betting_closed': not server_timer.is_betting_allowed(self.room_name),
            'phase': current_phase,
            'existing_bets': existing_bets,
            'sync_data': sync_data  # Include server synchronization data
        }

        # Add existing bet information if player has already bet
        if existing_bet:
            game_state_data['existing_bet'] = {
                'color': existing_bet.color,
                'amount': existing_bet.amount,
                'bet_type': existing_bet.bet_type,
                'number': existing_bet.number
            }
            logger.info(f"Player {self.username} has existing bet: {existing_bet.color} ${existing_bet.amount}")

        await self.send(text_data=json.dumps(game_state_data))

        logger.info(f"Sent game state to {self.username}: time_remaining={int(accurate_time_remaining)}, phase={'betting' if accurate_time_remaining > 0 else 'result'}, has_bet={existing_bet is not None}")

    async def round_timer(self):
        """Handle the round timer and game progression with improved timing"""
        room_data = game_rooms.get(self.room_name)
        if not room_data:
            logger.error(f"Room data not found for {self.room_name}")
            return

        try:
            start_time = asyncio.get_event_loop().time()
            last_heartbeat = 0
            game_round = room_data['round']  # Get game round from room data

            # Calculate the correct starting point based on actual elapsed time
            time_elapsed = (timezone.now() - game_round.start_time).total_seconds()
            current_time_remaining = max(0, ROUND_DURATION - time_elapsed)

            # If round has already ended, skip timer
            if current_time_remaining <= 0:
                logger.info(f"Round {game_round.period_id} has already ended, skipping timer")
                await self.end_round()
                return

            # Start timer from the correct remaining time, not from full duration
            betting_time_remaining = min(current_time_remaining, BETTING_DURATION)
            start_from = int(betting_time_remaining)

            logger.info(f"Starting timer for round {game_round.period_id} from {start_from} seconds (elapsed: {time_elapsed:.1f}s)")

            # Betting phase - start from correct remaining time
            for remaining in range(start_from, 0, -1):
                logger.debug(f"Timer tick: {remaining} seconds remaining for round {game_round.period_id}")
                # Check if task was cancelled
                if asyncio.current_task().cancelled():
                    logger.info(f"Timer task cancelled for room {self.room_name}")
                    return

                room_data['time_remaining'] = remaining

                # Send timer update with enhanced sync data to users
                timer_data = {
                    'type': 'timer_update',
                    'time_remaining': remaining,
                    'phase': 'betting',
                    'timestamp': asyncio.get_event_loop().time(),
                    'server_timestamp': timezone.now().timestamp(),
                    'round_id': game_round.id,
                    'round_start_time': game_round.start_time.timestamp()
                }

                # Send timer update with reliable delivery (critical for game timing)
                await reliable_ws_manager.send_reliable_message(
                    self.room_group_name,
                    timer_data,
                    critical=True,
                    timeout=5.0
                )

                # Also send the same timer update to admin panel for perfect synchronization
                await reliable_ws_manager.send_reliable_message(
                    "admin_game_control",
                    timer_data,
                    critical=True,
                    timeout=5.0
                )

                # Send timer update to admin panel for synchronization (every second for perfect sync)
                await self.channel_layer.group_send(
                    "admin_game_control",
                    {
                        'type': 'timer_sync_update',
                        'round_id': game_round.id,
                        'time_remaining': remaining,
                        'phase': 'betting',
                        'room': self.room_name,
                        'timestamp': timezone.now().timestamp()
                    }
                )

                # Send heartbeat more frequently for better sync (every 2 seconds)
                if remaining % HEARTBEAT_INTERVAL == 0 and remaining != last_heartbeat:
                    await self.channel_layer.group_send(
                        self.room_group_name,
                        {
                            'type': 'heartbeat',
                            'time_remaining': remaining,
                            'phase': 'betting',
                            'server_time': asyncio.get_event_loop().time(),
                            'server_timestamp': timezone.now().timestamp(),
                            'round_id': game_round.id
                        }
                    )
                    last_heartbeat = remaining

                # More precise timing - calculate exact sleep duration
                elapsed = asyncio.get_event_loop().time() - start_time
                expected_elapsed = (BETTING_DURATION - remaining + 1)
                sleep_duration = max(0.1, expected_elapsed - elapsed)

                await asyncio.sleep(sleep_duration)

            # Ensure betting is properly closed
            room_data['time_remaining'] = 0

            # Close betting with explicit state update (critical message)
            await reliable_ws_manager.send_reliable_message(
                self.room_group_name,
                {
                    'type': 'betting_closed',
                    'message': 'Betting is now closed!'
                },
                critical=True,
                timeout=10.0
            )

            # Immediate transition to result phase (critical message)
            await reliable_ws_manager.send_reliable_message(
                self.room_group_name,
                {
                    'type': 'timer_update',
                    'time_remaining': 0,
                    'phase': 'result'
                },
                critical=True,
                timeout=10.0
            )

            # Small delay to ensure UI updates, then calculate results
            await asyncio.sleep(0.5)

            # End round and calculate results
            logger.info(f"Timer completed for round {game_round.period_id}, calling end_round")
            await self.end_round()

        except asyncio.CancelledError:
            logger.info(f"Timer task cancelled for room {self.room_name}")
            raise
        except Exception as e:
            logger.error(f"Error in round timer for room {self.room_name}: {e}")
            # Try to recover by ending the round
            try:
                await self.end_round()
            except:
                pass

    async def end_round(self):
        """End the current round and calculate results"""
        logger.info(f"Starting end_round for room {self.room_name}")

        try:
            room_data = game_rooms.get(self.room_name)
            if not room_data:
                logger.error(f"No room data found for {self.room_name}")
                return

            game_round = room_data['round']
            logger.info(f"Processing end_round for round {game_round.period_id}")

            # Check if admin has selected a color for this round
            admin_selection = await database_sync_to_async(
                AdminColorSelection.objects.filter(round=game_round).first
            )()

            verification_hash = None

            if admin_selection and admin_selection.selected_color:
                # Use admin selected color with secure number generation
                result_color = admin_selection.selected_color
                result_number, verification_hash = await self.get_number_for_color(result_color, game_round.period_id)
                selection_type = "Admin Selected"
                logger.info(f"Using admin selected color: {result_color}, number: {result_number}, hash: {verification_hash[:16]}...")
            else:
                # Use auto-selection logic: choose color with minimum bets using secure method
                bet_stats = await self.get_bet_statistics(game_round)
                result_color, result_number, verification_hash = secure_random.select_minimum_bet_color(
                    game_round.period_id, bet_stats
                )
                selection_type = "Auto Selected (Minimum Bets)"
                logger.info(f"Using auto-selected color: {result_color}, number: {result_number}, hash: {verification_hash[:16]}...")

                # Create auto-selection record
                await database_sync_to_async(AdminColorSelection.objects.create)(
                    round=game_round,
                    selected_color=result_color,
                    is_auto_selected=True,
                    verification_hash=verification_hash
                )

            # Process all operations atomically to prevent inconsistent state
            @database_sync_to_async
            def atomic_round_completion():
                with transaction.atomic():
                    # Update game round with verification hash
                    game_round.result_color = result_color
                    game_round.result_number = result_number
                    game_round.ended = True
                    if verification_hash:
                        # Store verification hash in a custom field or log it
                        logger.info(f"Round {game_round.period_id} verification hash: {verification_hash}")
                    game_round.save()

                    # Process all bets in the same transaction
                    results = []
                    bet_ids = [bet_data['bet_id'] for bet_data in room_data['bets'].values()]

                    if bet_ids:
                        # Get all bets in one query with select_for_update to prevent race conditions
                        bets = list(Bet.objects.select_for_update().filter(id__in=bet_ids))

                        for bet in bets:
                            try:
                                # Process bet result with master wallet transaction
                                won, payout = process_bet_result_with_master_wallet(bet, result_number, result_color)

                                # Update player stats atomically
                                player = bet.player
                                player.total_bets += 1
                                if won:
                                    player.total_wins += 1
                                    player.score += 10
                                player.save()

                                results.append({
                                    'username': player.username,
                                    'bet_type': bet.bet_type,
                                    'color': bet.color,
                                    'number': bet.number,
                                    'amount': bet.amount,
                                    'won': won,
                                    'payout': payout,
                                    'new_balance': player.balance,
                                    'player_id': player.id  # Add for responsible gambling tracking
                                })

                            except Exception as e:
                                logger.error(f"Error processing bet {bet.id}: {e}")
                                # Continue processing other bets but log the error
                                continue

                    return results

            # Execute atomic operation
            results = await atomic_round_completion()
            logger.info(f"Atomically processed {len(results)} bets for round {game_round.period_id}")

            # Record bet outcomes for responsible gambling tracking
            for result in results:
                try:
                    await responsible_gambling.record_bet(
                        str(result['player_id']),
                        result['amount'],
                        result['won'],
                        result['payout']
                    )
                except Exception as e:
                    logger.error(f"Error recording responsible gambling data for {result['username']}: {e}")

            # Send notifications for game results (outside the transaction for performance)
            for result in results:
                try:
                    player = await self.get_or_create_player(result['username'])
                    if player:
                        @database_sync_to_async
                        def send_game_notification():
                            try:
                                bet_result = 'win' if result['won'] else 'loss'
                                amount = result['payout'] if result['won'] else result['amount']
                                notify_game_result(player, game_round, bet_result, amount)
                            except Exception as e:
                                logger.error(f"Error sending game notification to {player.username}: {e}")

                        await send_game_notification()
                except Exception as e:
                    logger.error(f"Error sending notification for {result['username']}: {e}")

            # Send results to all players with reliable delivery (critical message)
            logger.info(f"Sending round_ended event for round {game_round.period_id}: color={result_color}, number={result_number}, results_count={len(results)}")

            round_ended_message = {
                'type': 'round_ended',
                'result_color': result_color,
                'result_number': result_number,
                'selection_type': selection_type,
                'results': results,
                'verification_hash': verification_hash[:16] if verification_hash else None
            }

            await reliable_ws_manager.send_reliable_message(
                self.room_group_name,
                round_ended_message,
                critical=True,
                timeout=15.0,
                max_retries=5
            )

            logger.info(f"Round ended event sent successfully for round {game_round.period_id}")

            # Wait 3 seconds then start new round
            await asyncio.sleep(3)
            await self.start_new_round()

        except Exception as e:
            logger.error(f"Error in end_round for room {self.room_name}: {e}")
            logger.exception("Full traceback:")

            # Try to send a basic round ended event even if there was an error
            try:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'round_ended',
                        'result_color': 'red',  # Default fallback
                        'result_number': 2,     # Default fallback
                        'selection_type': 'Error Fallback',
                        'results': []
                    }
                )
                logger.info("Sent fallback round_ended event due to error")
            except Exception as fallback_error:
                logger.error(f"Failed to send fallback round_ended event: {fallback_error}")

            # Still try to start new round
            try:
                await asyncio.sleep(3)
                await self.start_new_round()
            except Exception as new_round_error:
                logger.error(f"Failed to start new round after error: {new_round_error}")

    async def start_new_round(self):
        """Start a new round - Only for main room"""
        # Only allow main room to create new rounds
        if self.room_name != 'main':
            logger.warning(f"Attempted to start new round in non-main room: {self.room_name}")
            return

        # End any existing active rounds before creating new one
        await database_sync_to_async(
            GameRound.objects.filter(ended=False).update
        )(ended=True)

        # Create new game round only for main room
        game_round = await database_sync_to_async(GameRound.objects.create)(
            room='main',  # Force main room
            start_time=timezone.now()
        )

        logger.info(f"Started new round for main room: {game_round.period_id}")

        # Reset room data
        game_rooms[self.room_name].update({
            'round': game_round,
            'bets': {},
            'time_remaining': ROUND_DURATION
        })

        # Notify players of new round
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'new_round_started',
                'round_id': game_round.id
            }
        )

        # Cancel any existing timer task before starting new one
        if game_rooms[self.room_name]['timer_task']:
            game_rooms[self.room_name]['timer_task'].cancel()
            try:
                await game_rooms[self.room_name]['timer_task']
            except asyncio.CancelledError:
                pass

        # Start new timer
        game_rooms[self.room_name]['timer_task'] = asyncio.create_task(
            self.round_timer()
        )

    # WebSocket event handlers
    async def player_joined(self, event):
        await self.send(text_data=json.dumps(event))

    async def player_left(self, event):
        await self.send(text_data=json.dumps(event))

    async def admin_color_selected(self, event):
        """Handle admin color selection broadcast to users"""
        await self.send(text_data=json.dumps({
            'type': 'admin_color_selected',
            'round_id': event['round_id'],
            'color': event['color'],
            'time_remaining': event['time_remaining'],
            'admin_selection': event['admin_selection']
        }))

    async def bet_placed(self, event):
        """Handle bet placed event"""
        await self.send(text_data=json.dumps(event))

    async def betting_closed(self, event):
        """Handle betting closed event"""
        await self.send(text_data=json.dumps(event))

    async def round_ended(self, event):
        """Handle round ended event"""
        await self.send(text_data=json.dumps(event))

    async def new_round_started(self, event):
        """Handle new round started event"""
        await self.send(text_data=json.dumps(event))

    async def timer_update(self, event):
        """Handle timer update event"""
        await self.send(text_data=json.dumps(event))

    async def game_state(self, event):
        """Handle game state update event"""
        await self.send(text_data=json.dumps(event))

    async def admin_force_round_end(self, event):
        """Handle admin forced round end"""
        logger.info(f"Received admin force round end for round {event['round_id']}")

        # Cancel current timer if running
        room_data = game_rooms.get(self.room_name)
        if room_data and room_data.get('timer_task'):
            timer_task = room_data['timer_task']
            if not timer_task.done():
                timer_task.cancel()
                logger.info(f"Cancelled timer for round {event['round_id']} due to admin selection")

        # Immediately end the round
        await self.end_round()

    async def bet_placed(self, event):
        await self.send(text_data=json.dumps(event))

    async def timer_update(self, event):
        await self.send(text_data=json.dumps(event))

    async def betting_closed(self, event):
        await self.send(text_data=json.dumps(event))

    async def round_ended(self, event):
        await self.send(text_data=json.dumps(event))

    async def new_round_started(self, event):
        await self.send(text_data=json.dumps(event))

    async def heartbeat(self, event):
        await self.send(text_data=json.dumps(event))

    async def get_minimum_selected_color(self, game_round):
        """Get the color with minimum bets for auto-selection"""
        # Get all color bets for this round
        bets = await database_sync_to_async(list)(
            Bet.objects.filter(round=game_round, bet_type='color')
        )

        # Count bets for each color
        color_counts = {'green': 0, 'red': 0, 'violet': 0, 'blue': 0}
        for bet in bets:
            if bet.color in color_counts:
                color_counts[bet.color] += 1

        # Return the color with minimum bets
        min_color = min(color_counts.items(), key=lambda x: x[1])[0]
        return min_color

    async def get_number_for_color(self, color, round_id):
        """Get a cryptographically secure random number for the given color"""
        number, verification_hash = secure_random.generate_number_for_color(round_id, color)
        return number, verification_hash

    def get_color_for_number(self, number):
        """Get the color that corresponds to a given number"""
        return secure_random.get_color_for_number(number)

    async def get_bet_statistics(self, game_round):
        """Get betting statistics for the current round"""
        @database_sync_to_async
        def calculate_stats():
            from django.db.models import Sum, Count

            # Get all bets for this round grouped by color
            color_stats = {}
            colors = ['red', 'green', 'violet', 'blue']

            for color in colors:
                bets = Bet.objects.filter(round=game_round, color=color)
                total_amount = bets.aggregate(Sum('amount'))['amount__sum'] or 0
                total_count = bets.count()

                color_stats[color] = {
                    'total_amount': total_amount,
                    'total_count': total_count
                }

            return color_stats

        return await calculate_stats()

    async def handle_phase_change(self, new_phase: str, time_remaining: float):
        """Handle phase changes from server-authoritative timer"""
        try:
            logger.info(f"Phase change in room {self.room_name}: {new_phase}, time remaining: {time_remaining:.1f}s")

            if new_phase == 'result':
                # Betting phase ended, close betting
                await reliable_ws_manager.send_reliable_message(
                    self.room_group_name,
                    {
                        'type': 'betting_closed',
                        'message': 'Betting is now closed!'
                    },
                    critical=True,
                    timeout=10.0
                )
            elif new_phase == 'ended':
                # Round ended, calculate results
                await self.end_round()

        except Exception as e:
            logger.error(f"Error handling phase change in room {self.room_name}: {e}")

    async def handle_timer_update(self, time_remaining: float, phase: str):
        """Handle timer updates from server-authoritative timer"""
        try:
            # Update room data
            room_data = game_rooms.get(self.room_name)
            if room_data:
                room_data['time_remaining'] = int(time_remaining)

            # Send synchronized timer update to all clients
            timer_data = {
                'type': 'timer_update',
                'time_remaining': int(time_remaining),
                'phase': phase,
                'server_timestamp': time.time(),
                'sync_data': server_timer.get_sync_data(self.room_name)
            }

            # Send to game room
            await reliable_ws_manager.send_reliable_message(
                self.room_group_name,
                timer_data,
                critical=True,
                timeout=5.0
            )

            # Send to admin panel
            await reliable_ws_manager.send_reliable_message(
                "admin_game_control",
                timer_data,
                critical=True,
                timeout=5.0
            )

        except Exception as e:
            logger.error(f"Error handling timer update in room {self.room_name}: {e}")