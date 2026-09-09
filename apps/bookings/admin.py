from django.contrib import admin

from .models import Booking


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("venue", "client", "start_time", "end_time", "status", "confirmation_deadline")
    list_filter = ("status", "venue")
    search_fields = ("venue__name", "client__phone")
    autocomplete_fields = ("venue", "client", "extended_from")
    date_hierarchy = "start_time"
