from rest_framework import serializers

from apps.bookings.models import Booking

from .models import Match, Team, TeamMembership


class TeamSerializer(serializers.ModelSerializer):
    games_played = serializers.IntegerField(read_only=True)
    members_count = serializers.IntegerField(source="memberships.count", read_only=True)
    rank_title = serializers.CharField(read_only=True)
    points_to_next_rank = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Team
        fields = [
            "id",
            "name",
            "district",
            "description",
            "rating_points",
            "wins",
            "draws",
            "losses",
            "games_played",
            "members_count",
            "rank_title",
            "points_to_next_rank",
            "created_at",
        ]
        read_only_fields = ["rating_points", "wins", "draws", "losses", "created_at"]


class TeamCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    district = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")
    description = serializers.CharField(required=False, allow_blank=True, default="")


class TeamMembershipSerializer(serializers.ModelSerializer):
    user_phone = serializers.CharField(source="user.phone", read_only=True)

    class Meta:
        model = TeamMembership
        fields = ["id", "user", "user_phone", "role", "joined_at"]
        read_only_fields = fields


class MatchSerializer(serializers.ModelSerializer):
    home_team_name = serializers.CharField(source="home_team.name", read_only=True)
    away_team_name = serializers.CharField(source="away_team.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Match
        fields = [
            "id",
            "booking",
            "home_team",
            "home_team_name",
            "away_team",
            "away_team_name",
            "status",
            "status_display",
            "home_score",
            "away_score",
            "played_at",
            "created_at",
        ]
        read_only_fields = ["status", "home_score", "away_score", "played_at", "created_at"]


class MatchCreateSerializer(serializers.Serializer):
    home_team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    away_team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    booking = serializers.PrimaryKeyRelatedField(queryset=Booking.objects.all(), required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["home_team"] == attrs["away_team"]:
            raise serializers.ValidationError({"away_team": "Команда не может играть сама с собой."})
        return attrs


class MatchResultSerializer(serializers.Serializer):
    home_score = serializers.IntegerField(min_value=0)
    away_score = serializers.IntegerField(min_value=0)
