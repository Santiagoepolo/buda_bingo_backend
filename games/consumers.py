import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from ..games.models import Game, PlayerCard
from django.contrib.auth.models import User


class BingoConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.game_id = self.scope["url_route"]["kwargs"]["game_id"]
        self.game_group_name = f"game_{self.game_id}"

        await self.channel_layer.group_add(self.game_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.game_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        action = data.get("action")

        if action == "select_number":
            await self.select_number(data)
        elif action == "claim_bingo":
            await self.claim_bingo(data)

    @database_sync_to_async
    def select_number(self, data):
        game = Game.objects.get(id=self.game_id)
        player_card = PlayerCard.objects.get(
            user_id=data["user_id"], game_id=self.game_id
        )
        number = data["number"]

        if number in game.drawn_numbers and number not in player_card.selected_numbers:
            player_card.selected_numbers.append(number)
            player_card.save()

    @database_sync_to_async
    def claim_bingo(self, data):
        game = Game.objects.get(id=self.game_id)
        player_card = PlayerCard.objects.get(
            user_id=data["user_id"], game_id=self.game_id
        )

        # Verify win condition
        if self.verify_win(player_card, game):
            game.status = "finished"
            game.winner = player_card.user
            game.save()

            player_card.is_winner = True
            player_card.save()

            return True
        return False

    def verify_win(self, player_card, game):
        # Implement win verification logic here
        # Check rows, columns, and diagonals
        return True  # Placeholder
