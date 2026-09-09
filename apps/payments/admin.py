from django.contrib import admin

from .models import Payment


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "__str__",
        "booking",
        "tournament_registration",
        "provider",
        "strategy",
        "amount",
        "commission_amount",
        "status",
        "created_at",
        "settled_at",
    )
    list_filter = ("provider", "strategy", "status")
    search_fields = (
        "booking__venue__name",
        "booking__client__phone",
        "tournament_registration__tournament__name",
        "external_id",
    )
