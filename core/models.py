import json
import logging
import os
import re

import requests
import telebot
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, transaction
from django.db.transaction import atomic
from django.utils.timezone import now
from geopy.distance import geodesic
from urllib3 import request

from app.settings import env
from users.models import TelegramUser

logger = logging.getLogger(__name__)

# Constants
MAX_PANORAMA_MOVES = 5
DISTANCE_ERROR_LIMIT = 2000
RATING_UPDATING_THRESHOLD = 15

def get_coordinates(street_view_url: str) -> tuple or None:
    """
    Extracts latitude and longitude coordinates from a Google Street View URL.
    """
    # Attempt to follow redirects to get the final URL
    try:
        response = requests.head(street_view_url, allow_redirects=True)
        final_url = response.url
        match = re.search(r'@(-?\d+\.\d+),(-?\d+\.\d+)', final_url)

        if match:
            lat, lng = match.groups()
            return float(lat), float(lng)

        return None

    except requests.exceptions.MissingSchema:
        logger.error('Error extracting coordinates from URL', exc_info=True)
        return None

def get_country(lat: float, lng: float) -> str:
    """
    Retrieves the country name for given geographical coordinates using Google Maps Geocoding API.
    """

    # Construct the API URL with coordinates and API key
    url = f'https://maps.googleapis.com/maps/api/geocode/json?latlng={lat},{lng}&key={env("GOOGLE_MAP_API")}'
    data = json.loads(request(method='GET', url=url).data)

    for result in data['results']:
        # Iterate through address components to find the country
        for component in result['address_components']:
            if 'country' in component['types']:
                country = component['long_name']
                return country

    logger.warning(f'Country not found for coordinates: lat={lat}, lng={lng}')
    raise ValueError('Country not found')


class Location(models.Model):
    """
    A model representing a geographical location with Street View data and statistics.

    Attributes:
        id (AutoField): Primary key for the location.
        created_at (DateTimeField): Timestamp when the location was created.
        street_view_url (URLField): URL to the Google Street View location.
        lat (FloatField): Latitude coordinate of the location.
        lng (FloatField): Longitude coordinate of the location.
        country (CharField): Name of the country where the location is situated.
        complexity (CharField): Difficulty level of the location ('easy', 'normal', 'hard').
        total_guesses (PositiveIntegerField): Total number of guesses made for this location.
        total_errors (FloatField): Sum of all distance errors for this location.
        total_time (PositiveIntegerField): Total time spent by users guessing this location.
        total_moves (PositiveIntegerField): Total number of panorama moves made at this location.
        total_score (PositiveIntegerField): Sum of all scores achieved at this location.
        avg_error (FloatField): Average distance error for all guesses.
        avg_time (PositiveIntegerField): Average time spent per guess.
        avg_moves (PositiveIntegerField): Average number of moves per guess.
        avg_score (FloatField): Average score achieved at this location.
    """

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

    # STATISTICS
    total_guesses = models.PositiveIntegerField(default=0)
    total_errors = models.FloatField(default=0.0)
    total_time = models.PositiveIntegerField(default=0)
    total_moves = models.PositiveIntegerField(default=0)
    total_score = models.FloatField(default=0)
    avg_error = models.FloatField(default=0.0)
    avg_time = models.PositiveIntegerField(default=0)
    avg_moves = models.PositiveIntegerField(default=0)
    avg_score = models.FloatField(default=0.0)

    class Meta:
        ordering = ['-id']
        verbose_name_plural = 'Locations'

    def __str__(self):
        return f'{self.id}'

    def save(self, *args, **kwargs):
        # If coordinates are not set, try to extract them from the URL
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

    def recalculate_location_stats(self, duration: int, error: float, score: float, moves: int) -> None:
        if not isinstance(duration, int) or not isinstance(error, float) or not isinstance(score, float) or not isinstance(moves, int):
            raise ValueError('Data types are not as expected')
        if duration <= 0 or error <= 0.0 or score <= 0 or moves < 0:
            raise ValueError('Some of the values are not positive or zero')

        self.total_guesses += 1
        self.total_time += duration
        self.total_errors += error
        self.total_moves += moves
        self.total_score += score

        self.avg_error = self.total_errors / self.total_guesses
        self.avg_time = self.total_time / self.total_guesses
        self.avg_moves = self.total_moves / self.total_guesses
        self.avg_score = self.total_guesses / self.total_score if self.total_score > 0 else 0.0

        logger.info(f'Location statistics were recalculated. Location: {self.id}')


class GameResult(models.Model):
    """
    Represents a single game attempt by a user to guess a location.

    Attributes:
        id (AutoField): Primary key for the game result.
        user (ForeignKey): Reference to the TelegramUser who made the guess.
        location (ForeignKey): Reference to the Location that was being guessed.
        guessed_at (DateTimeField): Timestamp when the guess was made.
        moves_used (PositiveIntegerField): Number of panorama moves used during the guess.
        guessed_lat (FloatField): Latitude coordinate guessed by the user.
        guessed_lng (FloatField): Longitude coordinate guessed by the user.
        distance_error (FloatField): Distance in kilometers between guessed and actual location.
        duration (PositiveIntegerField): Time taken to make the guess in seconds.
        score (FloatField): Calculated score for the guess based on accuracy and time.
    """

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='guesses')
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='guesses')
    guessed_at = models.DateTimeField(auto_now_add=True)
    moves_used = models.PositiveIntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(MAX_PANORAMA_MOVES)])
    guessed_lat = models.FloatField(null=True, blank=True)
    guessed_lng = models.FloatField(null=True, blank=True)
    distance_error = models.FloatField(null=True, blank=True)
    duration = models.PositiveIntegerField()
    score = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name_plural = 'Games'

    def calculate_score(self) -> float:
        """
        Calculate score based on error, moves, and time
        """
        error = self.distance_error
        time = self.duration
        score = 0

        if error < DISTANCE_ERROR_LIMIT:
            if self.moves_used < MAX_PANORAMA_MOVES:
                if self.moves_used == 0:
                    score += 100
                elif self.moves_used == 1:
                    score += 50
                else:
                    score += self.moves_used * 10
            if self.duration <= 60:
                score += ((60 - time) * 5  + (DISTANCE_ERROR_LIMIT - error)) / 10
            else:
                score += (DISTANCE_ERROR_LIMIT - error) / 10
        else:
            score = 0

        return score

    @atomic
    def save(self, *args, **kwargs):
        self.distance_error = self.calculate_distance_error()
        self.score = self.calculate_score()

        # Recalculate stats for user and location
        self.user.recalculate_player_stats(self.duration, self.distance_error, self.score, self.moves_used)
        self.location.recalculate_location_stats(self.duration, self.distance_error, self.score, self.moves_used)

        self.user.save()
        self.location.save()

        super().save(*args, **kwargs)
        logger.info(f'New object: Guess, user={self.user.id}, location={self.location}')

    @atomic
    def delete(self, *args, **kwargs):
        self.user.games -= 1
        self.location.total_guesses -= 1

        # Recalculating player stats
        if self.user.games > 1:
            self.user.total_errors -= self.distance_error
            self.user.total_time -= self.duration
            self.user.avg_error = self.user.total_errors / self.user.games
            self.user.avg_time = self.user.total_time / self.user.games
            self.user.avg_moves_per_game = self.user.total_moves / self.user.games
            self.user.avg_score = self.user.total_score / self.user.games
            self.user.daily_moves_remaining += self.moves_used
        else:
            self.user.games = 0
            self.user.total_errors = 0.0
            self.user.total_time = 0
            self.user.total_moves = 0
            self.user.total_score = 0.0
            self.user.avg_error = 0.0
            self.user.avg_time = 0
            self.user.avg_moves_per_game = 0
            self.user.avg_score = 0.0
            self.user.daily_moves_remaining += self.moves_used
        self.user.save()

        # Recalculating location stats
        if self.location.total_guesses > 1:
            self.location.total_errors -= self.distance_error
            self.location.total_time -= self.duration
            self.location.total_guesses -= 1
            self.location.total_moves -= self.moves_used
            self.location.total_score -= self.score
            self.location.avg_error = self.location.total_errors / self.location.total_guesses
            self.location.avg_time = self.location.total_time / self.location.total_guesses
            self.location.avg_moves = self.location.total_moves / self.location.total_guesses
            self.location.avg_score = self.location.total_score / self.location.total_guesses
        else:
            self.location.total_guesses = 0
            self.location.total_errors = 0.0
            self.location.total_time = 0
            self.location.total_moves = 0
            self.location.total_score = 0.0
            self.location.avg_error = 0.0
            self.location.avg_time = 0
            self.location.avg_moves = 0
            self.location.avg_score = 0.0
        self.location.save()

        # Delete the guess
        super().delete(*args, **kwargs)
        logger.info(
            f'Object was deleted: Guess, id={self.pk}, user={self.user.id}, location={self.location}'
        )

    def calculate_distance_error(self) -> float:
        return geodesic((self.guessed_lat, self.guessed_lng), (self.location.lat, self.location.lng)).kilometers


class Rating(models.Model):
    """
    A model representing user ratings and leaderboard data.

    Attributes:
        id (AutoField): Primary key for the rating entry.
        data (JSONField): JSON array containing user ranking data including username,
                         games played, total score, and average score per game.
        updated_at (DateTimeField): Timestamp of the last rating update.

    Methods:
        update_rating(): Updates the rating data if more than 15 seconds have passed
                        since the last update or if the data has changed.
    """

    id = models.AutoField(primary_key=True)
    data = models.JSONField(default=list)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    def __str__(self):
        return f'rating_data:{self.updated_at}'

    def update_rating(self) -> None:
        """
        Updates the rating data if more than 15 seconds have passed since the last update.
        """
        current_time = now()
        # Avoid frequent updates
        if self.updated_at is not None and (current_time - self.updated_at).total_seconds() <= RATING_UPDATING_THRESHOLD:
            return

        # Update data only if it has changed
        new_data = self.create_rating_data()
        if self.data != new_data:
            with transaction.atomic():
                self.data = new_data
                self.updated_at = current_time
                self.save()

        logger.info('Rating data was updated')

    @staticmethod
    def create_rating_data() -> list:
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
        return rating_data


class Feedback(models.Model):
    """
    A model representing user feedback and administrative responses.

    Attributes:
        id (AutoField): Primary key for the feedback entry.
        User (ForeignKey): Reference to the TelegramUser who submitted the feedback.
        Created_at (DateTimeField): Timestamp when the feedback was submitted.
        Updated_at (DateTimeField): Timestamp of the last update to the feedback.
        Answered_at (DateTimeField): Timestamp when admin answered the feedback.
        Answered (BooleanField): Indicates whether the feedback has been answered.
        Feedback_text (TextField): The actual feedback content submitted by the user.
        Answer (TextField): The administrative response to the feedback.
    """

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(TelegramUser, on_delete=models.CASCADE, related_name='feedback')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    answered_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    answered = models.BooleanField(default=False)

    feedback_text = models.TextField()
    answer = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-answered', '-created_at']

    def __str__(self):
        return f'Feedback id {self.id}, user {self.user}, message "{self.feedback_text}"'

    def save(self, *args, **kwargs):
        # Mark as answered and set timestamp if answer is provided
        if self.answer and not self.answered:
            self.answered = True
            self.answered_at = now()
        super().save(*args, **kwargs)

    # Method to send the answer to the user via Telegram
    def send_answer(self) -> None:
        if not self.answered or not self.answer or not self.user or not hasattr(self.user, 'chat_id'):
            logger.warning(
                f"Cannot send answer for Feedback id {self.id}: missing data")
            return

        user_chat_id = self.user.chat_id
        try:
            token = os.environ.get("TELEGRAM_TOKEN")
            if not token:
                logger.error("TELEGRAM_TOKEN environment variable not set.")
                return
            # Initialize Telegram bot and send message
            bot = telebot.TeleBot(token)
            message_text = f'Answer for your feedback:\n\n{self.answer}\n\nThank you for your opinion!'
            bot.send_message(chat_id=user_chat_id, text=message_text)
            logger.info(f'Answer for Feedback id {self.id} for user {self.user} was sent successfully.')
            self.sent_at = now()
            self.save(update_fields=['sent_at'])

        except Exception as e:
            logger.error(f"Error sending answer for Feedback id {self.id}: {e}")
