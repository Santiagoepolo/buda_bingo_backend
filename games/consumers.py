import json
import random
import asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Game, PlayerCard
from rest_framework_simplejwt.tokens import AccessToken
from django.core.exceptions import ObjectDoesNotExist
import logging

logger = logging.getLogger(__name__)


class BingoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
            self.game_group_name = f"game_{self.game_id}"
            self.number_generator_task = None

            query_string = self.scope["query_string"].decode()
            params = dict(x.split("=") for x in query_string.split("&") if "=" in x)
            token = params.get("token", "")

            if not token:
                logger.error("No token provided")
                await self.close()
                return

            try:
                access_token = AccessToken(token)
                user_id = access_token["user_id"]
                self.user = await self.get_user(user_id)

                if not self.user:
                    logger.error(f"User not found for ID: {user_id}")
                    await self.close()
                    return

                game_state = await self.get_game_state()
                if game_state:
                    await self.channel_layer.group_add(
                        self.game_group_name, self.channel_name
                    )

                    await self.accept()

                    await self.send(
                        text_data=json.dumps(
                            {
                                "type": "game_state",
                                "state": game_state["state"],
                                "player_card": game_state["player_card"],
                            }
                        )
                    )

                    game = await self.get_game(self.game_id)
                    if game.status == "waiting":
                        time_elapsed = (
                            timezone.now() - game.created_at
                        ).total_seconds()
                        if time_elapsed > 60:
                            player_count = await self.get_player_count(self.game_id)
                            if player_count >= 3:
                                await self.start_game()

                    await self.channel_layer.group_send(
                        self.game_group_name,
                        {"type": "player_joined", "player": self.user.username},
                    )
                else:
                    logger.error("Could not get game state")
                    await self.close()

            except Exception as e:
                logger.error(f"Token validation error: {str(e)}")
                await self.close()

        except Exception as e:
            logger.error(f"Connection error: {str(e)}")
            await self.close()

    @database_sync_to_async
    def get_player_count(self, game_id):
        return (
            PlayerCard.objects.filter(game_id=game_id).values("user").distinct().count()
        )

    async def start_game(self):
        game = await self.get_game(self.game_id)
        if game.status == "waiting":
            await self.update_game_status("playing")
            # Start number generator
            self.number_generator_task = asyncio.create_task(self.generate_numbers())
            # Notify all players that the game is starting
            await self.channel_layer.group_send(
                self.game_group_name,
                {"type": "game_starting", "message": "El juego está comenzando"},
            )

    @database_sync_to_async
    def update_game_status(self, status):
        game = Game.objects.get(id=self.game_id)
        game.status = status
        game.save()

    async def game_starting(self, event):
        await self.send(
            text_data=json.dumps({"type": "game_starting", "message": event["message"]})
        )

    async def disconnect(self, close_code):
        try:
            if hasattr(self, "number_generator_task") and self.number_generator_task:
                self.number_generator_task.cancel()
            if hasattr(self, "game_group_name"):
                await self.channel_layer.group_discard(
                    self.game_group_name, self.channel_name
                )
        except Exception as e:
            logger.error(f"Disconnect error: {str(e)}")

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @database_sync_to_async
    def get_game(self, game_id):
        try:
            return Game.objects.get(id=game_id)
        except Game.DoesNotExist:
            return None

    @database_sync_to_async
    def get_game_state(self):
        try:
            game = Game.objects.get(id=self.game_id)
            player_card = PlayerCard.objects.get(user=self.user, game=game)

            return {
                "state": {
                    "status": game.status,
                    "currentNumber": game.current_number,
                    "drawnNumbers": game.drawn_numbers,
                    "winner": game.winner.username if game.winner else None,
                    "players": [
                        {
                            "username": pc.user.username,
                            "is_disqualified": pc.is_disqualified,
                        }
                        for pc in PlayerCard.objects.filter(game=game)
                    ],
                },
                "player_card": {
                    "id": player_card.id,
                    "card_numbers": player_card.card_numbers,
                    "selected_numbers": player_card.selected_numbers,
                    "is_winner": player_card.is_winner,
                },
            }
        except (Game.DoesNotExist, PlayerCard.DoesNotExist):
            return None

    async def generate_numbers(self):
        try:
            game = await self.get_game(self.game_id)
            available_numbers = set(range(1, 76)) - set(game.drawn_numbers)

            while game.status == "playing" and available_numbers:
                await asyncio.sleep(5)

                number = random.choice(list(available_numbers))
                available_numbers.remove(number)

                game.drawn_numbers.append(number)
                game.current_number = number
                await self.update_game(game)

                await self.channel_layer.group_send(
                    self.game_group_name, {"type": "number_drawn", "number": number}
                )

                game = await self.get_game(self.game_id)
                if game.status != "playing":
                    break

        except Exception as e:
            logger.error(f"Error generating numbers: {str(e)}")

    @database_sync_to_async
    def update_game(self, game):
        game.save()

    async def disconnect(self, close_code):
        try:
            if self.number_generator_task:
                self.number_generator_task.cancel()
            await self.channel_layer.group_discard(
                self.game_group_name, self.channel_name
            )
        except:
            pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            action = data.get("action")

            if action == "select_number":
                success = await self.select_number(data.get("number"))
                await self.send(
                    text_data=json.dumps(
                        {
                            "type": "number_selected",
                            "success": success,
                            "number": data.get("number"),
                        }
                    )
                )
            elif action == "claim_bingo":
                is_winner = await self.verify_bingo()
                if is_winner:
                    await self.channel_layer.group_send(
                        self.game_group_name,
                        {
                            "type": "bingo_claimed",
                            "success": True,
                            "player": self.user.username,
                        },
                    )
                else:
                    await self.disqualify_player()
                    await self.channel_layer.group_send(
                        self.game_group_name,
                        {
                            "type": "bingo_claimed",
                            "success": False,
                            "player": self.user.username,
                        },
                    )
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")

    @database_sync_to_async
    def select_number(self, number):
        try:
            game = Game.objects.get(id=self.game_id)
            player_card = PlayerCard.objects.get(user=self.user, game=game)

            if (
                number in game.drawn_numbers
                and number not in player_card.selected_numbers
            ):
                player_card.selected_numbers.append(number)
                player_card.save()
                return True
            return False
        except (Game.DoesNotExist, PlayerCard.DoesNotExist):
            return False

    @database_sync_to_async
    def verify_bingo(self):
        try:
            game = Game.objects.get(id=self.game_id)
            player_card = PlayerCard.objects.get(user=self.user, game=game)

            if self.check_win_condition(
                player_card.card_numbers, player_card.selected_numbers
            ):
                game.status = "finished"
                game.winner = self.user
                game.save()

                player_card.is_winner = True
                player_card.save()
                return True
            return False
        except (Game.DoesNotExist, PlayerCard.DoesNotExist):
            return False

    def check_win_condition(self, card_numbers, selected_numbers):
        selected_set = set(selected_numbers)
        selected_set.add(0)  # Añadir el comodín al conjunto de números seleccionados

        # Verificar filas
        for row in card_numbers:
            if all(num in selected_set for num in row):
                return True

        # Verificar columnas
        for col in range(5):
            if all(card_numbers[row][col] in selected_set for row in range(5)):
                return True

        # Verificar diagonales
        if all(card_numbers[i][i] in selected_set for i in range(5)):
            return True
        if all(card_numbers[i][4 - i] in selected_set for i in range(5)):
            return True

        # Verificar las cuatro esquinas
        corners = [
            card_numbers[0][0],  # Esquina superior izquierda
            card_numbers[0][4],  # Esquina superior derecha
            card_numbers[4][0],  # Esquina inferior izquierda
            card_numbers[4][4],  # Esquina inferior derecha
        ]
        if all(corner in selected_set for corner in corners):
            return True

        return False

    @database_sync_to_async
    def disqualify_player(self):
        try:
            player_card = PlayerCard.objects.get(user=self.user, game_id=self.game_id)
            player_card.is_disqualified = True
            player_card.save()
        except PlayerCard.DoesNotExist:
            pass

    async def number_drawn(self, event):
        await self.send(text_data=json.dumps(event))

    async def bingo_claimed(self, event):
        await self.send(text_data=json.dumps(event))

    async def player_joined(self, event):
        await self.send(text_data=json.dumps(event))

    async def game_starting(self, event):
        await self.send(text_data=json.dumps(event))
