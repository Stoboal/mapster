from django.urls import path

from .views import (
    GetLocationAPIView,
    GetRatingAPIView,
    GetUserAPIView,
    SendFeedbackAPIView,
    SubmitGuessAPIView,
)

urlpatterns = [
    path('location/random', GetLocationAPIView.as_view(), name='get_location'),
    path('location/guess', SubmitGuessAPIView.as_view(), name='submit_guess'),
    path('rating/', GetRatingAPIView.as_view(), name='get_location'),
    path('profile/', GetUserAPIView.as_view(), name='get_user'),
    path('feedback/send', SendFeedbackAPIView.as_view(), name='send_feedback'),
]
