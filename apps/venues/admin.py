from django.contrib import admin

from .models import Venue, VenueMembership


class VenueMembershipInline(admin.TabularInline):
    model = VenueMembership
    extra = 0


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "district",
        "surface_type",
        "field_size",
        "price_per_hour",
        "commission_percent",
        "subscription_tier",
        "is_active",
    )
    list_filter = ("surface_type", "field_size", "subscription_tier", "is_active", "district")
    search_fields = ("name", "address", "district")
    inlines = [VenueMembershipInline]


@admin.register(VenueMembership)
class VenueMembershipAdmin(admin.ModelAdmin):
    list_display = ("venue", "user", "role", "is_active", "created_at")
    list_filter = ("role", "is_active")
    search_fields = ("venue__name", "user__phone")
