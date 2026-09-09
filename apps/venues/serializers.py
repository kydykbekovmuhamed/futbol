from django.utils import timezone
from rest_framework import serializers

from .models import Venue


class VenueSerializer(serializers.ModelSerializer):
    surface_type_display = serializers.CharField(source="get_surface_type_display", read_only=True)
    occupied_until = serializers.SerializerMethodField()

    class Meta:
        model = Venue
        fields = [
            "id",
            "name",
            "district",
            "address",
            "latitude",
            "longitude",
            "surface_type",
            "surface_type_display",
            "field_size",
            "price_per_hour",
            "description",
            "occupied_until",
        ]

    def get_occupied_until(self, venue):
        """
        Таймер до освобождения (roadmap 2.1: "освободится через 23 мин")
        для карточки площадки в общем списке "сейчас". Ожидает, что вьюха
        предзагрузила venue.occupying_bookings (см. VenueListView) —
        без этого атрибута просто вернёт None, лишнего запроса не будет.
        """
        bookings = getattr(venue, "occupying_bookings", None)
        if not bookings:
            return None
        now = timezone.now()
        current = next((b for b in bookings if b.start_time <= now < b.end_time), None)
        return current.end_time if current else None


class VenueAvailabilitySerializer(VenueSerializer):
    class Meta(VenueSerializer.Meta):
        fields = [f for f in VenueSerializer.Meta.fields if f != "occupied_until"]
