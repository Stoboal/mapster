from rest_framework import serializers

from users.models import TelegramUser

from .models import Feedback, GameResult, Location, Rating


class TelegramUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramUser
        fields = [
            'id', 'username', 'date_joined', 'telegram_id', 'games', 'avg_time', 'avg_error', 'total_time',
            'total_errors', 'total_score', 'daily_moves_remaining', 'last_move_date'
        ]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = [
            'id', 'lat', 'lng', 'complexity', 'country', 'created_at', 'street_view_url', 'total_guesses', 'total_errors', 'total_time',
            'avg_error', 'avg_time', 'total_moves', 'avg_moves'
        ]
        read_only_fields = [
            'id', 'created_at', 'total_guesses', 'total_errors', 'total_time', 'avg_time', 'avg_error', 'total_moves', 'avg_moves'
        ]


class GameResultSerializer(serializers.ModelSerializer):
    location_id = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), source='location')
    user_id = serializers.PrimaryKeyRelatedField(queryset=TelegramUser.objects.all(), source='user')

    class Meta:
        model = GameResult
        fields = [
            'user_id', 'location_id', 'guessed_lat', 'guessed_lng', 'duration', 'score', 'moves_used'
        ]
        read_only_fields = ['user_id', 'score']


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = ['data', 'updated_at']
        read_only_fields = ['data', 'updated_at']


class FeedbackSerializer(serializers.ModelSerializer):
    user_id = serializers.PrimaryKeyRelatedField(queryset=TelegramUser.objects.all(), source='user')
    class Meta:
        model = Feedback
        fields = [
            'id', 'user_id','feedback_text', 'created_at', 'updated_at', 'answered', 'answer', 'answered_at', 'sent_at'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'answered', 'answer', 'answered_at', 'sent_at'
        ]
