from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.fields import ArrayField


class Game(models.Model):
    STATUS_CHOICES = [
        ("waiting", "Waiting"),
        ("playing", "Playing"),
        ("finished", "Finished"),
        ("cancelled", "Cancelled"),
    ]

    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="waiting")
    created_at = models.DateTimeField(auto_now_add=True)
    winner = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name="won_games"
    )
    drawn_numbers = ArrayField(models.IntegerField(), default=list)
    current_number = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        db_table = "games"


class PlayerCard(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    card_numbers = ArrayField(ArrayField(models.IntegerField(), size=5), size=5)
    selected_numbers = ArrayField(models.IntegerField(), default=list)
    is_winner = models.BooleanField(default=False)
    is_disqualified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


    class Meta:
        unique_together = ["user", "game"]
        db_table = "player_cards"
