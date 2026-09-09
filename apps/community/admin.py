from django.contrib import admin

from .models import ActivityEvent, Challenge, NewsItem, TeamSubscription


@admin.register(ActivityEvent)
class ActivityEventAdmin(admin.ModelAdmin):
    list_display = ("user", "event_type", "title", "is_read", "created_at")
    list_filter = ("event_type", "is_read")
    search_fields = ("user__phone", "title")


@admin.register(Challenge)
class ChallengeAdmin(admin.ModelAdmin):
    list_display = ("challenger_team", "opponent_team", "status", "proposed_time", "created_at")
    list_filter = ("status",)
    autocomplete_fields = ("challenger_team", "opponent_team")


@admin.register(NewsItem)
class NewsItemAdmin(admin.ModelAdmin):
    list_display = ("title", "source_name", "published_at")
    search_fields = ("title", "source_name")


@admin.register(TeamSubscription)
class TeamSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("team", "is_active", "expires_at", "created_at")
    search_fields = ("team__name",)
