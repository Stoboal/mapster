import requests
import re
import logging
import json

from django.db import models, transaction
from django.db.transaction import atomic
from django.utils.timezone import now
from geopy.distance import geodesic
from urllib3 import request

from app.settings import env
from users.models import TelegramUser


logger = logging.getLogger(__name__)


def get_coordinates(street_view_url: str) -> tuple or None:
    try:
        response = requests.head(street_view_url, allow_redirects=True)
        final_url = response.url

        match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)
        if match:
            lat, lng = match.groups()
            return float(lat), float(lng)

        return None
    except Exception as e:
        print("Error: ", e)
        return None

def get_country(lat: float, lng: float) -> str:
    url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={env("GOOGLE_MAP_API")}'
    data = json.loads(request(method='GET', url=url).data)
    for result in data['results']:
        for component in result['address_components']:
            if 'country' in component['types']:
                country = component['long_name']
                return country


class Location(models.Model):
    COMPLEXITY = (
        ('easy', 'easy'),
        ('normal', 'normal'),
        ('hard', 'hard'),
    )
    id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)
    street_view_url = models.URLField(max_length=255, blank=True, null=True)

    lat = models.FloatField(null=True, blank=True)
    lng = models.FloatField(null=True, blank=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    complexity = models.CharField(max_length=10, choices=COMPLEXITY, default='normal')

    total_guesses = models.PositiveIntegerField(default=0)
    total_errors = models.FloatField(default=0.0)
    total_time = models.PositiveIntegerField(default=0)
    avg_error = models.FloatField(default=0.0)
    avg_time = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['-id']
        verbose_name_plural = 'Locations'

    def __str__(self):
        return f'{self.id}'

    def save(self, *args, **kwargs):
        if not self.lat and not self.lng:
            coordinates = get_coordinates(self.street_view_url)
            if coordinates:
                self.lat, self.lng = coordinates
                self.country = get_country(*coordinates)
            else:
                self.lat, self.lng = None, None

        is_new = self.pk is None
        super().save(*args, **kwargs)

        if is_new:
            logger.info(f'New object: Location, lat={self.lat}, lng={self.lng}')
        else:
            logger.info(f'Object was changed: Location, id={self.pk}: lat={self.lat}, lng={self.lng}.')


class Guess(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='guesses')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='guesses')
    guessed_at = models.DateTimeField(auto_now_add=True)

    guessed_lat = models.FloatField(null=True, blank=True)
    guessed_lng = models.FloatField(null=True, blank=True)
    distance_error = models.FloatField(null=True, blank=True)
    duration = models.PositiveIntegerField()
    score = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Guesses'

    def calculate_score(self) -> int:
        error = self.distance_error
        time = self.duration

        if error < 2000:
            if self.duration <= 60:
                score = ((60 - time) * 5  + (2000 - error)) / 10
            else:
                score = (2000 - error) / 10
        else:
            score = 0

        return score

    @atomic
    def save(self, *args, **kwargs):
        self.distance_error = self.calculate_distance_error()
        self.score = self.calculate_score()

        self.user.recalculate_player_stats(self.duration, self.distance_error, self.score)

        self.location.total_guesses += 1
        self.location.total_errors += self.distance_error
        self.location.total_time += self.duration
        self.location.avg_error = self.location.total_errors / self.location.total_guesses
        self.location.avg_time = self.location.total_time / self.location.total_guesses

        self.user.save()
        self.location.save()

        super().save(*args, **kwargs)
        logger.info(
            f'New object: Guess, user={self.user.id}, location={self.location}'
        )

    @atomic
    def delete(self, *args, **kwargs):
        self.user.games -= 1
        self.location.total_guesses -= 1

        if self.user.games > 1:
            self.user.total_errors -= self.distance_error
            self.user.total_time -= self.duration
            self.user.avg_error = self.user.total_errors / self.user.games
            self.user.avg_time = self.user.total_time / self.user.games
        else:
            self.user.games = 0
            self.user.total_errors = 0.0
            self.user.total_time = 0
            self.user.avg_error = 0.0
            self.user.avg_time = 0

        self.user.save()

        if self.location.total_guesses > 1:
            self.location.total_errors -= self.distance_error
            self.location.total_time -= self.duration
            self.location.avg_error = self.location.total_errors / self.location.total_guesses
            self.location.avg_time = self.location.total_time / self.location.total_guesses
        else:
            self.location.total_guesses = 0
            self.location.total_errors = 0.0
            self.location.total_time = 0
            self.location.avg_error = 0.0
            self.location.avg_time = 0

        self.location.save()

        super().delete(*args, **kwargs)
        logger.info(
            f'Object was deleted: Guess, id={self.pk}, user={self.user.id}, location={self.location}'
        )

    def calculate_distance_error(self):
        return geodesic((self.guessed_lat, self.guessed_lng), (self.location.lat, self.location.lng)).kilometers


class Rating(models.Model):
    id = models.AutoField(primary_key=True)
    data = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f'rating_data:{self.updated_at}'

    def update_rating(self):
        current_time = now()

        if self.updated_at is not None and (current_time - self.updated_at).total_seconds() < 15:
            return

        users = TelegramUser.objects.filter(games__gte=5).order_by('-total_score')
        rating_data = [
            {
                "username": user.username,
                "games": user.games,
                "score": user.total_score,
                "score_for_game": user.total_score / user.games if user.games > 0 else 0,
            }
            for user in users
        ]
        if self.data != rating_data:
            with transaction.atomic():
                self.data = rating_data
                self.updated_at = current_time
                self.save()
        logger.info(f'Rating data was updated')
