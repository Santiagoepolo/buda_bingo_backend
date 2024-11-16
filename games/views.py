from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.utils import timezone
from games.models import Game, PlayerCard
from games.serializers import GameSerializer
import random

from games.view_utils import cancel_old_games


class GameViewSet(viewsets.ModelViewSet):
    queryset = Game.objects.all()
    serializer_class = GameSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def join_game(self, request):
        with transaction.atomic():
            # Cancel any previous games that has been waiting for too long
            cancel_old_games()

            # Find an available game or create a new one
            game = Game.objects.filter(status="waiting").first()
            if not game:
                game = Game.objects.create(created_at=timezone.now())

            if not PlayerCard.objects.filter(user=request.user, game=game).exists():
                card_numbers = self.generate_bingo_card()

                PlayerCard.objects.create(
                    user=request.user, game=game, card_numbers=card_numbers
                )

            serializer = self.get_serializer(game)
            response_data = serializer.data
            response_data["created_at"] = game.created_at.timestamp()

            return Response(response_data)

    def generate_bingo_card(self):
        card = []
        used_numbers = set()

        ranges = [(1, 15), (16, 30), (31, 45), (46, 60), (61, 75)]

        for col_idx, (start, end) in enumerate(ranges):
            column = []
            numbers_needed = (
                5 if col_idx != 2 else 4
            )  # La columna del medio necesita solo 4 números

            while len(column) < numbers_needed:
                num = random.randint(start, end)
                if num not in used_numbers:
                    used_numbers.add(num)
                    column.append(num)

            # Mezclar los números en la columna
            random.shuffle(column)

            # Si es la columna del medio (N), insertar el comodín en el centro
            if col_idx == 2:
                column.insert(2, 0)  # Usamos 0 como marcador del comodín

            card.append(column)

        # Transponer la matriz para obtener filas en lugar de columnas
        return [list(row) for row in zip(*card)]
