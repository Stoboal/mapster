from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

DAILY_MOVES_LIMIT = 15

class TelegramUser(AbstractUser):
    telegram_id = models.CharField(max_length=255, unique=True)
    chat_id = models.BigIntegerField(unique=True, null=True, blank=True)
    username = models.CharField(max_length=255, unique=False)

    # STATISTICS
    games = models.PositiveIntegerField(default=0)
    daily_moves_remaining = models.PositiveIntegerField(default=DAILY_MOVES_LIMIT)
    last_move_date = models.DateField(null=True, blank=True, auto_now=True)

    avg_moves_per_game = models.PositiveIntegerField(default=0)
    avg_error = models.PositiveIntegerField(default=0)
    avg_time = models.PositiveIntegerField(default=0)
    total_moves = models.PositiveIntegerField(default=0)
    total_time = models.PositiveIntegerField(default=0)
    total_errors = models.PositiveIntegerField(default=0)
    total_score = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = 'telegram_id'

    def __str__(self):
        return f'id: {self.telegram_id}, username: {self.username}'

    def recalculate_player_stats(self, duration: int, error: float, score: int, moves: int) -> None:
        self.games += 1
        self.total_time += duration
        self.total_errors += error
        self.total_moves += moves
        self.total_score += score
        self.avg_time = self.total_time / self.games
        self.avg_error = self.total_errors / self.games
        self.avg_moves_per_game = self.total_moves / self.games

        self.daily_moves_remaining -= moves
        self.last_move_date = timezone.now().date()
