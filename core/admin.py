from django.contrib import admin

from .models import Feedback, GameResult, Location, Rating


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('id', 'location', 'country', 'street_view_url', 'created_at', 'total_guesses', 'avg_error')
    list_filter = ('id', 'created_at', 'country', 'total_guesses', 'avg_error')

    def location(self, obj):
        return f"({obj.lat}, {obj.lng})"

    location.short_description = 'Location'

    def get_fields(self, request, obj=None):
        if obj is None:
            return ['street_view_url', 'complexity']
        return super().get_fields(request, obj)


@admin.register(GameResult)
class GuessAdmin(admin.ModelAdmin):
    list_display = ('id', 'score', 'user_id', 'location', 'distance_error', 'duration', 'guessed_at')
    list_filter = ('id', 'score', 'user_id', 'location', 'distance_error', 'duration', 'guessed_at')

    def user_id(self, obj):
        return f"{obj.user.id}"
    user_id.short_description = 'User'

    def get_fields(self, request, obj=None):
        if obj is None:
            return ['user', 'location', 'duration']
        return super().get_fields(request, obj)

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.delete()


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ('data', 'updated_at')


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('user_id', 'feedback_text', 'created_at', 'answered', 'answer', 'answered_at')
    list_filter = ('user_id', 'feedback_text', 'created_at', 'answered', 'answer', 'answered_at')

    def user_id(self, obj):
        return f"{obj.user.id}"
    user_id.short_description = 'User'
