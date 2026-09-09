from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Match, Team, TeamMembership
from .serializers import (
    MatchCreateSerializer,
    MatchResultSerializer,
    MatchSerializer,
    TeamCreateSerializer,
    TeamMembershipSerializer,
    TeamSerializer,
)
from .services import (
    AlreadyTeamMember,
    MatchAlreadyReported,
    NotMatchParticipant,
    NotTeamMember,
    TeamNameTaken,
    create_team,
    join_team,
    leave_team,
    report_match_result,
    schedule_match,
)


class TeamListCreateView(generics.ListAPIView):
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Team.objects.annotate(members_count=Count("memberships"))
        search = self.request.query_params.get("search")
        if search:
            qs = qs.filter(name__icontains=search)
        if self.request.query_params.get("mine") == "true":
            qs = qs.filter(memberships__user=self.request.user)
        return qs

    def post(self, request, *args, **kwargs):
        serializer = TeamCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            team = create_team(creator=request.user, **serializer.validated_data)
        except TeamNameTaken as exc:
            raise ValidationError({"name": [str(exc)]})
        return Response(TeamSerializer(team).data, status=status.HTTP_201_CREATED)


class TeamDetailView(generics.RetrieveAPIView):
    queryset = Team.objects.annotate(members_count=Count("memberships"))
    serializer_class = TeamSerializer
    permission_classes = [IsAuthenticated]


class TeamMembersView(generics.ListAPIView):
    serializer_class = TeamMembershipSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TeamMembership.objects.filter(team_id=self.kwargs["pk"]).select_related("user")


class TeamJoinView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            raise NotFound("Команда не найдена.")
        try:
            join_team(team=team, user=request.user)
        except AlreadyTeamMember as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(TeamSerializer(team).data)


class TeamLeaveView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            raise NotFound("Команда не найдена.")
        try:
            leave_team(team=team, user=request.user)
        except NotTeamMember as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MatchListCreateView(generics.ListAPIView):
    serializer_class = MatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = Match.objects.select_related("home_team", "away_team")
        team_id = self.request.query_params.get("team")
        if team_id:
            try:
                team_id = int(team_id)
            except ValueError:
                return qs.none()
            qs = qs.filter(Q(home_team_id=team_id) | Q(away_team_id=team_id))
        return qs

    def post(self, request, *args, **kwargs):
        serializer = MatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            match = schedule_match(organizer=request.user, **serializer.validated_data)
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        return Response(MatchSerializer(match).data, status=status.HTTP_201_CREATED)


class MatchReportResultView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        serializer = MatchResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            match = report_match_result(match_id=pk, reporter=request.user, **serializer.validated_data)
        except Match.DoesNotExist:
            raise NotFound("Матч не найден.")
        except NotMatchParticipant as exc:
            raise PermissionDenied(str(exc))
        except MatchAlreadyReported as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(MatchSerializer(match).data)
