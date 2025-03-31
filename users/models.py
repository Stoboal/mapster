from django.contrib.auth.models import AbstractUser
from django.db import models

class TelegramUser(AbstractUser):
    telegram_id = models.CharField(max_length=255, unique=True)
    username = models.CharField(max_length=255, unique=False)

    games = models.PositiveIntegerField(default=0)
    avg_error = models.PositiveIntegerField(default=0)
    avg_time = models.PositiveIntegerField(default=0)
    total_time = models.PositiveIntegerField(default=0)
    total_errors = models.PositiveIntegerField(default=0)
    total_score = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = 'telegram_id'

    def __str__(self):
        return f'id: {self.telegram_id}, username: {self.username}'

    def recalculate_player_stats(self, duration: int, error: float, score: int) -> None:
        self.games += 1
        self.total_time += duration
        self.avg_time = self.total_time / self.games
        self.total_errors += error
        self.avg_error = self.total_errors / self.games
        self.total_score += score
