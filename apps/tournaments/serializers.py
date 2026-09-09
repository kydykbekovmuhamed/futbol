from rest_framework import serializers

from apps.bookings.models import Booking
from apps.teams.models import Team

from .models import Tournament, TournamentMatch, TournamentRegistration


class TournamentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    registered_teams_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Tournament
        fields = [
            "id",
            "name",
            "description",
            "sponsor_name",
            "organizer",
            "entry_fee",
            "min_teams",
            "max_teams",
            "registration_deadline",
            "status",
            "status_display",
            "registered_teams_count",
            "created_at",
        ]
        read_only_fields = ["organizer", "status", "created_at"]


class TournamentCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True, default="")
    sponsor_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    entry_fee = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    min_teams = serializers.IntegerField(min_value=2, default=4)
    max_teams = serializers.IntegerField(min_value=2, required=False, allow_null=True, default=None)
    registration_deadline = serializers.DateTimeField()


class TournamentRegistrationSerializer(serializers.ModelSerializer):
    team_name = serializers.CharField(source="team.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = TournamentRegistration
        fields = ["id", "tournament", "team", "team_name", "status", "status_display", "created_at"]
        read_only_fields = ["status", "created_at"]


class TournamentRegisterSerializer(serializers.Serializer):
    team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())


class TournamentMatchSerializer(serializers.ModelSerializer):
    home_team_name = serializers.CharField(source="home_registration.team.name", read_only=True)
    away_team_name = serializers.CharField(source="away_registration.team.name", read_only=True)
    home_score = serializers.IntegerField(source="match.home_score", read_only=True)
    away_score = serializers.IntegerField(source="match.away_score", read_only=True)
    match_status = serializers.CharField(source="match.status", read_only=True)

    class Meta:
        model = TournamentMatch
        fields = [
            "id",
            "tournament",
            "round_number",
            "home_registration",
            "home_team_name",
            "away_registration",
            "away_team_name",
            "match",
            "match_status",
            "home_score",
            "away_score",
            "created_at",
        ]
        read_only_fields = ["match", "created_at"]


class TournamentMatchCreateSerializer(serializers.Serializer):
    round_number = serializers.IntegerField(min_value=1, default=1)
    home_registration = serializers.PrimaryKeyRelatedField(queryset=TournamentRegistration.objects.all())
    away_registration = serializers.PrimaryKeyRelatedField(queryset=TournamentRegistration.objects.all())
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all(), required=False, allow_null=True)


class TournamentMatchResultSerializer(serializers.Serializer):
    home_score = serializers.IntegerField(min_value=0)
    away_score = serializers.IntegerField(min_value=0)


class StandingsRowSerializer(serializers.Serializer):
    registration_id = serializers.IntegerField()
    team_id = serializers.IntegerField()
    team_name = serializers.CharField()
    played = serializers.IntegerField()
    wins = serializers.IntegerField()
    draws = serializers.IntegerField()
    losses = serializers.IntegerField()
    points = serializers.IntegerField()
