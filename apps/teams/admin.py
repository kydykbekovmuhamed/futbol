from django.contrib import admin

from .models import Match, Team, TeamMembership


class TeamMembershipInline(admin.TabularInline):
    model = TeamMembership
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("name", "district", "rating_points", "wins", "draws", "losses")
    search_fields = ("name", "district")
    inlines = [TeamMembershipInline]


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("home_team", "away_team", "status", "home_score", "away_score", "played_at")
    list_filter = ("status",)
    autocomplete_fields = ("home_team", "away_team", "booking")
