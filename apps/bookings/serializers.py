from rest_framework import serializers

from apps.venues.models import Venue

from .models import Booking


class BookingSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    venue_name = serializers.CharField(source="venue.name", read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "venue",
            "venue_name",
            "start_time",
            "end_time",
            "status",
            "status_display",
            "price",
            "deposit_amount",
            "confirmation_deadline",
            "extended_from",
            "created_at",
        ]
        read_only_fields = [
            "status",
            "price",
            "deposit_amount",
            "confirmation_deadline",
            "extended_from",
            "created_at",
        ]


class BookingCreateSerializer(serializers.Serializer):
    venue = serializers.PrimaryKeyRelatedField(queryset=Venue.objects.filter(is_active=True))
    start_time = serializers.DateTimeField()
    end_time = serializers.DateTimeField()
