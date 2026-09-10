from django.contrib import admin
from django.utils.html import format_html

from .models import Booking, BookingStatus

_STATUS_PILL_VARIANT = {
    BookingStatus.PENDING_CONFIRMATION: "orange",
    BookingStatus.EXTENSION_PENDING: "orange",
    BookingStatus.CONFIRMED: "lime",
    BookingStatus.DECLINED: "red",
    BookingStatus.EXPIRED: "red",
    BookingStatus.CANCELLED: "muted",
    BookingStatus.COMPLETED: "muted",
}


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("venue", "client", "start_time", "end_time", "status_badge", "confirmation_deadline")
    list_filter = ("status", "venue")
    search_fields = ("venue__name", "client__phone")
    autocomplete_fields = ("venue", "client", "extended_from")
    date_hierarchy = "start_time"

    @admin.display(description="Статус", ordering="status")
    def status_badge(self, obj):
        variant = _STATUS_PILL_VARIANT.get(obj.status, "muted")
        return format_html(
            '<span class="status-pill status-pill--{}">{}</span>', variant, obj.get_status_display()
        )
