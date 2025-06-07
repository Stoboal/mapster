import logging

from django.db.models import Subquery
from django.db.models.functions import Random
from drf_spectacular.utils import extend_schema, OpenApiResponse, inline_serializer
from rest_framework import status, serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .mixins import AuthenticatedMixin
from .models import GameResult, Location, Rating
from .serializers import (
    FeedbackSerializer,
    GameResultSerializer,
    LocationSerializer,
    RatingSerializer,
    TelegramUserSerializer,
)

logger = logging.getLogger(__name__)

class GetUserAPIView(AuthenticatedMixin, APIView):
    """
    Provides information about the authenticated user's profile.
    """
    @extend_schema(
        summary="Get user profile",
        description="Retrieves and returns the authenticated user's data.",
        responses={
            200: TelegramUserSerializer,
            401: OpenApiResponse(description="Error: unauthorized or expired token")
        }
    )
    def get(self, request):
        user = self.get_user(request)
        serializer = TelegramUserSerializer(user)
        logger.info(f'User {user} requested profile data')
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetRatingAPIView(AuthenticatedMixin, APIView):
    """
    Provides access to the leaderboard (rating).
    """
    @extend_schema(
        summary="Get rating",
        description="Retrieves and returns the rating data.",
        responses={
            200: RatingSerializer,
            400: OpenApiResponse(description="Error: rating data update failed"),
            401: OpenApiResponse(description="Error: unauthorized or expired token"),
        }
    )
    def get(self, request):
        user = self.get_user(request)
        rating = Rating.objects.first()

        if not rating:
            # Creating an empty rating object if it doesn't exist
            try:
                logger.info(f'Rating data was created by user {user}')
                rating = Rating.objects.create(data=[])
                rating.data = rating.create_rating_data()
                rating.save()
            except Exception as e:
                logger.error(f'Error in rating data creation by user {user}: {e}')
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Updating existing rating data
            rating.update_rating()
            logger.info(f'Rating data was updated successfully by user {user}')

        except Exception as e:
            logger.error(f'Error in rating data update by user {user}: {e}')
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RatingSerializer(rating)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetLocationAPIView(AuthenticatedMixin, APIView):
    """
    Provides a random location for the user to guess.
    """
    @extend_schema(
        summary="Get random location",
        description="Retrieves and returns a random location for the user to guess.",
        responses={
            200: LocationSerializer,
            401: OpenApiResponse(description="Error: unauthorized or expired token"),
            404: OpenApiResponse(description="Error: no available locations found")
        }
    )
    def get(self, request):
        user = self.get_user(request)

        guessed_location_ids = GameResult.objects.filter(user=user).values_list('location_id', flat=True)
        location_queryset = Location.objects.exclude(id__in=Subquery(guessed_location_ids))
        if user.games <= 5:
            location_queryset = location_queryset.filter(complexity='easy')
        location = location_queryset.order_by(Random()).first()

        if not location:
            logger.warning(f'No available locations found for user {user}')
            return Response(
                {"error": "No available locations found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = LocationSerializer(location)
        logger.info(f'Location {location} was returned to user {user}')
        return Response(serializer.data, status=status.HTTP_200_OK)


class SubmitGuessAPIView(AuthenticatedMixin, APIView):
    """
    Accepts and processes a user's attempt to guess a location.
    """
    @extend_schema(
        summary="Submit guess",
        description="Accepts and processes a user's attempt to guess a location.",
        request=GameResultSerializer,
        responses={
            201: GameResultSerializer,
            401: OpenApiResponse(description="Error: unauthorized or expired token"),
            400: OpenApiResponse(description="Error: invalid guess data"),
        }
    )
    def post(self, request):
        # Ensure the user is authenticated before processing the request
        user = self.get_user(request)
        data = request.data.copy()
        data['user_id'] = request.user.id
        serializer = GameResultSerializer(data=data)

        if serializer.is_valid():
            guess = serializer.save()
            logger.info(f'Guess {guess} was submitted by user {guess.user}')

            user.refresh_from_db()
            user_serializer = TelegramUserSerializer(user)
            response_data = {
                "message": "Guess submitted successfully",
                "distance_error": f"{guess.distance_error} kilometers",
                "duration": f"{guess.duration} seconds",
                "score": guess.score,
                "moves used": f"{guess.moves_used} moves",
                "updated_user_stats": user_serializer.data
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        logger.warning(f'Error in guess submission by user {request.user}: {serializer.errors}')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class SendFeedbackAPIView(AuthenticatedMixin, APIView):
    """
    Accepts and processes a user's feedback.
    """
    @extend_schema(
        summary="Send feedback",
        description="Accepts and processes a user's feedback.",
        request=FeedbackSerializer,
        responses={
            201: OpenApiResponse(
                description="Feedback submitted successfully",
                response=inline_serializer(
                    name="FeedbackResponse",
                    fields={
                        'message': serializers.CharField(),
                        'distance_error': serializers.CharField(),
                        'duration': serializers.CharField(),
                        'score': serializers.IntegerField(),
                        'moves_used': serializers.CharField()
                    }
                )
            ),
            401: OpenApiResponse(description="Error: unauthorized or expired token"),
            400: OpenApiResponse(description="Error: invalid feedback data"),
        }
    )
    def post(self, request):
        self.get_user(request)
        data = request.data.copy()
        data['user_id'] = request.user.id
        serializer = FeedbackSerializer(data=data)

        if serializer.is_valid():
            feedback = serializer.save()
            logger.info(f'Feedback {feedback} was submitted by user {feedback.user}')
            return Response(
                {"message": "Feedback submitted successfully"},
                status=status.HTTP_201_CREATED
            )

        logger.warning(f'Error in feedback submission by user {request.user}: {serializer.errors}')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
