from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Game, PlayerCard


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email")


class PlayerCardSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = PlayerCard
        fields = ("id", "user", "card_numbers", "selected_numbers", "is_winner")


class GameSerializer(serializers.ModelSerializer):
    winner = UserSerializer(read_only=True)
    player_cards = PlayerCardSerializer(
        many=True, read_only=True, source="playercard_set"
    )

    class Meta:
        model = Game
        fields = (
            "id",
            "status",
            "created_at",
            "winner",
            "drawn_numbers",
            "current_number",
            "player_cards",
        )
