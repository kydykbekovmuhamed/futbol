from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.teams.models import Team, TeamMembership

from .models import ActivityEvent, Challenge, NewsItem
from .serializers import (
    ActivityEventSerializer,
    ChallengeCreateSerializer,
    ChallengeSerializer,
    ExtendedStatsSerializer,
    LocalScheduleRowSerializer,
    NewsItemSerializer,
    TeamSubscriptionSerializer,
)
from .services import (
    CannotChallengeOwnTeam,
    ChallengeAlreadyResolved,
    NotTeamMember,
    SubscriptionPaymentFailed,
    SubscriptionRequired,
    accept_challenge,
    cancel_challenge,
    create_challenge,
    decline_challenge,
    get_extended_stats,
    get_local_schedule,
    subscribe_team,
)


class ActivityFeedView(generics.ListAPIView):
    serializer_class = ActivityEventSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ActivityEvent.objects.filter(user=self.request.user)


class ActivityEventMarkReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        updated = ActivityEvent.objects.filter(pk=pk, user=request.user).update(is_read=True)
        if not updated:
            raise NotFound("Событие не найдено.")
        return Response(status=status.HTTP_204_NO_CONTENT)


class ChallengeListCreateView(generics.ListAPIView):
    serializer_class = ChallengeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        team_ids = TeamMembership.objects.filter(user=self.request.user).values_list("team_id", flat=True)
        return Challenge.objects.filter(
            Q(challenger_team_id__in=team_ids) | Q(opponent_team_id__in=team_ids)
        ).select_related("challenger_team", "opponent_team")

    def post(self, request, *args, **kwargs):
        serializer = ChallengeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            challenge = create_challenge(creator=request.user, **serializer.validated_data)
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        except CannotChallengeOwnTeam as exc:
            raise ValidationError({"opponent_team": [str(exc)]})
        return Response(ChallengeSerializer(challenge).data, status=status.HTTP_201_CREATED)


class _ChallengeDecisionView(APIView):
    permission_classes = [IsAuthenticated]
    action = None
    actor_kwarg = "responder"

    def post(self, request, pk, *args, **kwargs):
        try:
            challenge = self.action(challenge_id=pk, **{self.actor_kwarg: request.user})
        except Challenge.DoesNotExist:
            raise NotFound("Вызов не найден.")
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        except ChallengeAlreadyResolved as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(ChallengeSerializer(challenge).data)


class ChallengeAcceptView(_ChallengeDecisionView):
    action = staticmethod(accept_challenge)


class ChallengeDeclineView(_ChallengeDecisionView):
    action = staticmethod(decline_challenge)


class ChallengeCancelView(_ChallengeDecisionView):
    action = staticmethod(cancel_challenge)
    actor_kwarg = "canceller"


class LocalScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        rows = get_local_schedule()
        return Response(LocalScheduleRowSerializer(rows, many=True).data)


class NewsListView(generics.ListAPIView):
    queryset = NewsItem.objects.all()
    serializer_class = NewsItemSerializer
    permission_classes = [IsAuthenticated]


class TeamSubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            raise NotFound("Команда не найдена.")
        try:
            result = subscribe_team(team=team, activator=request.user)
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        except SubscriptionPaymentFailed as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)

        data = TeamSubscriptionSerializer(result.subscription).data
        if result.payment_redirect_url:
            # Провайдер с редиректом (FreedomPay) — клиента нужно отправить
            # туда завершить оплату, подписка продлится позже по вебхуку
            # (см. apps.community.services.activate_subscription_after_payment_success).
            data["payment_redirect_url"] = result.payment_redirect_url
        return Response(data, status=status.HTTP_201_CREATED)


class TeamExtendedStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            team = Team.objects.get(pk=pk)
        except Team.DoesNotExist:
            raise NotFound("Команда не найдена.")
        try:
            stats = get_extended_stats(team=team)
        except SubscriptionRequired as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_402_PAYMENT_REQUIRED)
        return Response(ExtendedStatsSerializer(stats).data)
