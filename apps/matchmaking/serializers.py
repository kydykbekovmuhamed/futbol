from rest_framework import serializers

from apps.bookings.models import Booking
from apps.teams.models import Team

from .models import OpponentRequest, PlayerApplication, PlayerRequest


class OpponentRequestSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    matched_team_name = serializers.CharField(source="matched_team.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    venue_name = serializers.CharField(source="booking.venue.name", read_only=True)
    start_time = serializers.DateTimeField(source="booking.start_time", read_only=True)
    end_time = serializers.DateTimeField(source="booking.end_time", read_only=True)

    class Meta:
        model = OpponentRequest
        fields = [
            "id",
            "team",
            "team_name",
            "booking",
            "venue_name",
            "start_time",
            "end_time",
            "message",
            "status",
            "status_display",
            "matched_team",
            "matched_team_name",
            "created_at",
        ]
        read_only_fields = ["status", "matched_team", "created_at"]


class OpponentRequestCreateSerializer(serializers.Serializer):
    team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())
    message = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class MatchOpponentSerializer(serializers.Serializer):
    responder_team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())


class PlayerRequestSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    venue_name = serializers.CharField(source="booking.venue.name", read_only=True)
    start_time = serializers.DateTimeField(source="booking.start_time", read_only=True)
    accepted_count = serializers.SerializerMethodField()

    class Meta:
        model = PlayerRequest
        fields = [
            "id",
            "team",
            "team_name",
            "booking",
            "venue_name",
            "start_time",
            "spots_needed",
            "accepted_count",
            "message",
            "status",
            "status_display",
            "created_at",
        ]
        read_only_fields = ["status", "created_at"]

    def get_accepted_count(self, obj):
        return obj.applications.filter(status="accepted").count()


class PlayerRequestCreateSerializer(serializers.Serializer):
    team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all())
    spots_needed = serializers.IntegerField(min_value=1, default=1)
    message = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class PlayerApplicationSerializer(serializers.ModelSerializer):
    applicant_phone = serializers.CharField(source="applicant.phone", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = PlayerApplication
        fields = ["id", "request", "applicant", "applicant_phone", "status", "status_display", "created_at"]
        read_only_fields = fields
