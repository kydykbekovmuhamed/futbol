from rest_framework import serializers

from apps.teams.models import Team

from .models import ActivityEvent, Challenge, NewsItem, TeamSubscription


class ActivityEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source="get_event_type_display", read_only=True)

    class Meta:
        model = ActivityEvent
        fields = ["id", "event_type", "event_type_display", "title", "body", "is_read", "created_at"]
        read_only_fields = fields


class ChallengeSerializer(serializers.ModelSerializer):
    challenger_team_name = serializers.CharField(source="challenger_team.name", read_only=True)
    opponent_team_name = serializers.CharField(source="opponent_team.name", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = Challenge
        fields = [
            "id",
            "challenger_team",
            "challenger_team_name",
            "opponent_team",
            "opponent_team_name",
            "message",
            "proposed_time",
            "status",
            "status_display",
            "created_at",
            "responded_at",
        ]
        read_only_fields = ["status", "created_at", "responded_at"]


class ChallengeCreateSerializer(serializers.Serializer):
    challenger_team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    opponent_team = serializers.PrimaryKeyRelatedField(queryset=Team.objects.all())
    message = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    proposed_time = serializers.DateTimeField(required=False, allow_null=True, default=None)


class NewsItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = NewsItem
        fields = ["id", "title", "source_name", "source_url", "published_at"]
        read_only_fields = fields


class TeamSubscriptionSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = TeamSubscription
        fields = ["team", "is_active", "expires_at"]
        read_only_fields = fields


class LocalScheduleRowSerializer(serializers.Serializer):
    """roadmap, Этап 3: "Расписание/результаты местных турниров" — тонкая обёртка над TournamentMatch."""

    tournament_match_id = serializers.IntegerField()
    tournament_name = serializers.CharField()
    round_number = serializers.IntegerField()
    home_team_name = serializers.CharField()
    away_team_name = serializers.CharField()
    match_status = serializers.CharField()
    home_score = serializers.IntegerField(allow_null=True)
    away_score = serializers.IntegerField(allow_null=True)
    venue_name = serializers.CharField(allow_null=True)
    scheduled_at = serializers.DateTimeField(allow_null=True)


class ExtendedStatsSerializer(serializers.Serializer):
    team_id = serializers.IntegerField()
    team_name = serializers.CharField()
    rank_title = serializers.CharField()
    points_to_next_rank = serializers.IntegerField(allow_null=True)
    games_played = serializers.IntegerField()
    win_rate_percent = serializers.FloatField()
    monthly_breakdown = serializers.ListField(child=serializers.DictField())
    longest_win_streak = serializers.IntegerField()
