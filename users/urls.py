from django.urls import path

from . import views

urlpatterns = [
    path("auth/telegram/", views.telegram_auth, name="telegram_auth"),
]
