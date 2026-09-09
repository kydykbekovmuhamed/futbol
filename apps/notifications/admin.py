from django.contrib import admin

from .models import DeviceToken, NotificationLog


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ("booking", "recipient", "channel", "status", "sent_at", "responded_at")
    list_filter = ("channel", "status")
    search_fields = ("booking__venue__name", "recipient__phone")


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "platform", "is_active", "created_at", "last_seen_at")
    list_filter = ("platform", "is_active")
    search_fields = ("user__phone", "token")
