from django.utils import timezone
from games.models import Game


def cancel_old_games():
    return Game.objects.filter(
        status="waiting", created_at__lt=timezone.now() - timezone.timedelta(minutes=1)
    ).update(status="cancelled")
