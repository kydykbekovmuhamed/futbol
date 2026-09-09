from django.contrib import admin

from .models import Tournament, TournamentMatch, TournamentRegistration


class TournamentRegistrationInline(admin.TabularInline):
    model = TournamentRegistration
    extra = 0


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organizer",
        "entry_fee",
        "organizer_commission_percent",
        "min_teams",
        "max_teams",
        "registration_deadline",
        "status",
    )
    list_filter = ("status",)
    search_fields = ("name",)
    inlines = [TournamentRegistrationInline]


@admin.register(TournamentMatch)
class TournamentMatchAdmin(admin.ModelAdmin):
    list_display = ("tournament", "round_number", "home_registration", "away_registration")
    list_filter = ("tournament", "round_number")
