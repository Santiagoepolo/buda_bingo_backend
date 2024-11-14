from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from games.models import Game, PlayerCard
from games.serializers import GameSerializer, PlayerCardSerializer
import random


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def join_game(self, request):
        with transaction.atomic():
            # Find or create a waiting game
            game = Game.objects.filter(status="waiting").first()
            if not game:
                game = Game.objects.create(status="waiting")

            # Generate unique bingo card
            card_numbers = self.generate_bingo_card()

            # Create player card
            PlayerCard.objects.create(
                user=request.user, game=game, card_numbers=card_numbers
            )

            # Check if game should start
            if PlayerCard.objects.filter(game=game).count() >= 2:
                game.status = "playing"
                game.save()

            return Response(self.get_serializer(game).data)

    def generate_bingo_card(self):
        card = []
        used_numbers = set()

        for col in range(5):
            start = col * 15 + 1
            end = start + 14
            column = []

            while len(column) < 5:
                num = random.randint(start, end)
                if num not in used_numbers:
                    used_numbers.add(num)
                    column.append(num)

            card.append(sorted(column))

        # Transpose the card to get rows instead of columns
        return list(map(list, zip(*card)))
