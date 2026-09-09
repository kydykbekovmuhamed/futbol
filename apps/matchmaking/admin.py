from django.contrib import admin

from .models import OpponentRequest, PlayerApplication, PlayerRequest


@admin.register(OpponentRequest)
class OpponentRequestAdmin(admin.ModelAdmin):
    list_display = ("team", "booking", "status", "matched_team", "created_at")
    list_filter = ("status",)
    autocomplete_fields = ("team", "booking", "matched_team")


class PlayerApplicationInline(admin.TabularInline):
    model = PlayerApplication
    extra = 0


@admin.register(PlayerRequest)
class PlayerRequestAdmin(admin.ModelAdmin):
    list_display = ("team", "booking", "spots_needed", "status", "created_at")
    list_filter = ("status",)
    autocomplete_fields = ("team", "booking")
    inlines = [PlayerApplicationInline]
