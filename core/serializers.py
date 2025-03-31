from rest_framework import serializers

from users.models import TelegramUser
from .models import Location, Guess, Rating

class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUser
        fields = ['id', 'username', 'date_joined', 'telegram_id', 'games', 'avg_time', 'avg_error', 'total_time',
        'total_errors', 'total_score']

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            'id', 'lat', 'lng', 'created_at', 'street_view_url', 'total_guesses', 'total_errors', 'total_time',
            'avg_error', 'avg_time'
        ]
        read_only_fields = ['id', 'created_at', 'total_guesses', 'total_errors', 'total_time', 'avg_time', 'avg_error']


class GuessSerializer(serializers.ModelSerializer):
    location_id = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), source='location')
    user_id = serializers.PrimaryKeyRelatedField(queryset=TelegramUser.objects.all(), source='user')

    class Meta:
        model = Guess
        fields = ['user_id', 'location_id', 'guessed_lat', 'guessed_lng', 'duration', 'score']


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['data', 'updated_at']
        read_only_fields = ['data', 'updated_at']
