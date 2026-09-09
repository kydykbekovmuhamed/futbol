from django.db.models import Count, Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.teams.services import MatchAlreadyReported, NotMatchParticipant

from .models import RegistrationStatus, Tournament, TournamentMatch, TournamentRegistration
from .serializers import (
    StandingsRowSerializer,
    TournamentCreateSerializer,
    TournamentMatchCreateSerializer,
    TournamentMatchResultSerializer,
    TournamentMatchSerializer,
    TournamentRegisterSerializer,
    TournamentRegistrationSerializer,
    TournamentSerializer,
)
from .services import (
    AlreadyRegistered,
    NotTeamMember,
    NotTournamentOrganizer,
    RegistrationAlreadyResolved,
    RegistrationDeadlinePassed,
    RegistrationNotEligible,
    TournamentFull,
    TournamentNotOpen,
    cancel_registration,
    create_tournament,
    disqualify_registration,
    get_standings,
    register_team,
    report_tournament_match_result,
    schedule_tournament_match,
)


class TournamentListCreateView(generics.ListAPIView):
    serializer_class = TournamentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Tournament.objects.annotate(
            registered_teams_count=Count(
                "registrations", filter=Q(registrations__status=RegistrationStatus.REGISTERED)
            )
        )

    def post(self, request, *args, **kwargs):
        serializer = TournamentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tournament = create_tournament(organizer=request.user, **serializer.validated_data)
        except RegistrationDeadlinePassed as exc:
            raise ValidationError({"registration_deadline": [str(exc)]})
        return Response(TournamentSerializer(tournament).data, status=status.HTTP_201_CREATED)


class TournamentDetailView(generics.RetrieveAPIView):
    queryset = Tournament.objects.annotate(
        registered_teams_count=Count(
            "registrations", filter=Q(registrations__status=RegistrationStatus.REGISTERED)
        )
    )
    serializer_class = TournamentSerializer
    permission_classes = [IsAuthenticated]


class TournamentRegistrationsView(generics.ListAPIView):
    serializer_class = TournamentRegistrationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TournamentRegistration.objects.filter(tournament_id=self.kwargs["pk"]).select_related("team")

    def post(self, request, pk, *args, **kwargs):
        serializer = TournamentRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tournament = Tournament.objects.get(pk=pk)
        except Tournament.DoesNotExist:
            raise NotFound("Турнир не найден.")
        try:
            registration = register_team(tournament=tournament, registrant=request.user, **serializer.validated_data)
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        except (TournamentNotOpen, RegistrationDeadlinePassed, TournamentFull) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except AlreadyRegistered as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(TournamentRegistrationSerializer(registration).data, status=status.HTTP_201_CREATED)


class TournamentRegistrationCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            registration = cancel_registration(registration_id=pk, user=request.user)
        except TournamentRegistration.DoesNotExist:
            raise NotFound("Регистрация не найдена.")
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        except (RegistrationAlreadyResolved, TournamentNotOpen) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(TournamentRegistrationSerializer(registration).data)


class TournamentRegistrationDisqualifyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            registration = disqualify_registration(registration_id=pk, organizer=request.user)
        except TournamentRegistration.DoesNotExist:
            raise NotFound("Регистрация не найдена.")
        except NotTournamentOrganizer as exc:
            raise PermissionDenied(str(exc))
        except RegistrationAlreadyResolved as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(TournamentRegistrationSerializer(registration).data)


class TournamentStandingsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        rows = get_standings(pk)
        return Response(StandingsRowSerializer(rows, many=True).data)


class TournamentMatchListCreateView(generics.ListAPIView):
    serializer_class = TournamentMatchSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return TournamentMatch.objects.filter(tournament_id=self.kwargs["pk"]).select_related(
            "match", "home_registration__team", "away_registration__team"
        )

    def post(self, request, pk, *args, **kwargs):
        serializer = TournamentMatchCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            tournament = Tournament.objects.get(pk=pk)
        except Tournament.DoesNotExist:
            raise NotFound("Турнир не найден.")
        try:
            tournament_match = schedule_tournament_match(
                tournament=tournament, organizer=request.user, **serializer.validated_data
            )
        except NotTournamentOrganizer as exc:
            raise PermissionDenied(str(exc))
        except RegistrationNotEligible as exc:
            raise ValidationError({"detail": [str(exc)]})
        return Response(TournamentMatchSerializer(tournament_match).data, status=status.HTTP_201_CREATED)


class TournamentMatchReportResultView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        serializer = TournamentMatchResultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            report_tournament_match_result(tournament_match_id=pk, reporter=request.user, **serializer.validated_data)
        except TournamentMatch.DoesNotExist:
            raise NotFound("Матч не найден.")
        except NotMatchParticipant as exc:
            raise PermissionDenied(str(exc))
        except MatchAlreadyReported as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        tournament_match = TournamentMatch.objects.select_related(
            "match", "home_registration__team", "away_registration__team"
        ).get(pk=pk)
        return Response(TournamentMatchSerializer(tournament_match).data)
