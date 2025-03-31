from django.contrib import admin
from .models import *

@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):

    list_display = [
        'id', 'username', 'total_score', 'telegram_id', 'games', 'avg_error', 'avg_time', 'total_time', 'total_errors'
    ]