from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import OpponentRequest, OpponentRequestStatus, PlayerApplication, PlayerRequest, PlayerRequestStatus
from .serializers import (
    MatchOpponentSerializer,
    OpponentRequestCreateSerializer,
    OpponentRequestSerializer,
    PlayerApplicationSerializer,
    PlayerRequestCreateSerializer,
    PlayerRequestSerializer,
)
from .services import (
    AlreadyApplied,
    AlreadyTeamMember,
    BookingNotConfirmed,
    CannotRespondToOwnRequest,
    NotBookingOwner,
    NotTeamMember,
    RequestAlreadyResolved,
    accept_application,
    apply_to_player_request,
    cancel_opponent_request,
    create_opponent_request,
    create_player_request,
    decline_application,
    match_opponent_request,
)


class OpponentRequestListCreateView(generics.ListAPIView):
    serializer_class = OpponentRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = OpponentRequest.objects.select_related("team", "matched_team", "booking__venue")
        status_param = self.request.query_params.get("status", OpponentRequestStatus.OPEN)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def post(self, request, *args, **kwargs):
        serializer = OpponentRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            obj = create_opponent_request(creator=request.user, **serializer.validated_data)
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        except (NotBookingOwner, BookingNotConfirmed) as exc:
            raise ValidationError({"booking": [str(exc)]})
        return Response(OpponentRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class OpponentRequestMatchView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        serializer = MatchOpponentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            obj = match_opponent_request(
                request_id=pk, responder=request.user, **serializer.validated_data
            )
        except OpponentRequest.DoesNotExist:
            raise NotFound("Заявка не найдена.")
        except (NotTeamMember, CannotRespondToOwnRequest) as exc:
            raise PermissionDenied(str(exc))
        except RequestAlreadyResolved as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(OpponentRequestSerializer(obj).data)


class OpponentRequestCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            obj = cancel_opponent_request(request_id=pk, user=request.user)
        except OpponentRequest.DoesNotExist:
            raise NotFound("Заявка не найдена.")
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        except RequestAlreadyResolved as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(OpponentRequestSerializer(obj).data)


class PlayerRequestListCreateView(generics.ListAPIView):
    serializer_class = PlayerRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = PlayerRequest.objects.select_related("team", "booking__venue")
        status_param = self.request.query_params.get("status", PlayerRequestStatus.OPEN)
        if status_param:
            qs = qs.filter(status=status_param)
        return qs

    def post(self, request, *args, **kwargs):
        serializer = PlayerRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            obj = create_player_request(creator=request.user, **serializer.validated_data)
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        return Response(PlayerRequestSerializer(obj).data, status=status.HTTP_201_CREATED)


class PlayerRequestApplyView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            application = apply_to_player_request(request_id=pk, applicant=request.user)
        except PlayerRequest.DoesNotExist:
            raise NotFound("Заявка не найдена.")
        except AlreadyTeamMember as exc:
            raise ValidationError({"detail": str(exc)})
        except (RequestAlreadyResolved, AlreadyApplied) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(PlayerApplicationSerializer(application).data, status=status.HTTP_201_CREATED)


class PlayerRequestApplicationsView(generics.ListAPIView):
    serializer_class = PlayerApplicationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return PlayerApplication.objects.filter(request_id=self.kwargs["pk"]).select_related("applicant")


class _ApplicationDecisionView(APIView):
    permission_classes = [IsAuthenticated]
    action = None

    def post(self, request, pk, *args, **kwargs):
        try:
            application = self.action(application_id=pk, decider=request.user)
        except PlayerApplication.DoesNotExist:
            raise NotFound("Заявка игрока не найдена.")
        except NotTeamMember as exc:
            raise PermissionDenied(str(exc))
        except RequestAlreadyResolved as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        return Response(PlayerApplicationSerializer(application).data)


class PlayerApplicationAcceptView(_ApplicationDecisionView):
    action = staticmethod(accept_application)


class PlayerApplicationDeclineView(_ApplicationDecisionView):
    action = staticmethod(decline_application)
