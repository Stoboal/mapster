import logging

from django.db.models import Subquery
from django.db.models.functions import Random
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .mixins import AuthenticatedMixin
from .models import Location, Guess, Rating
from .serializers import TelegramUserSerializer, GuessSerializer, LocationSerializer, RatingSerializer


logger = logging.getLogger(__name__)

class GetUserAPIView(AuthenticatedMixin, APIView):
    def get(self, request):
        user = self.get_user(request)
        serializer = TelegramUserSerializer(user)
        logger.info(f'User {user} requested profile data')
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetRatingAPIView(AuthenticatedMixin, APIView):
    def get(self, request):
        user = self.get_user(request)
        rating = Rating.objects.first()
        if not rating:
            try:
                logger.info(f'Rating data was created by user {user}')
                rating = Rating.objects.create(data=[])
            except Exception as e:
                logger.error(f'Error in rating data creation by user {user}: {e}')
                return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            rating.update_rating()
            logger.info(f'Rating data was updated successfully by user {user}')

        except Exception as e:
            logger.error(f'Error in rating data update by user {user}: {e}')
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        serializer = RatingSerializer(rating)
        return Response(serializer.data, status=status.HTTP_200_OK)


class GetLocationAPIView(AuthenticatedMixin, APIView):
    def get(self, request):
        user = self.get_user(request)

        guessed_location_ids = Guess.objects.filter(user=user).values_list('location_id', flat=True)
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
    def post(self, request):
        # Ensure the user is authenticated before processing the request
        self.get_user(request)

        data = request.data.copy()
        data['user_id'] = request.user.id

        serializer = GuessSerializer(data=data)
        if serializer.is_valid():
            guess = serializer.save()
            logger.info(f'Guess {guess} was submitted by user {guess.user}')
            return Response(
                {
                    "message": "Guess submitted successfully",
                    "distance_error": f"{guess.distance_error} kilometers",
                    "duration": f"{guess.duration} seconds",
                    "score": guess.score,
                },
                status=status.HTTP_201_CREATED
            )

        logger.warning(f'Error in guess submission by user {request.user}: {serializer.errors}')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
