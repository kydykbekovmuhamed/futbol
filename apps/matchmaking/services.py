from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.bookings.models import BookingStatus
from apps.teams.models import TeamMembership

from .models import (
    ApplicationStatus,
    OpponentRequest,
    OpponentRequestStatus,
    PlayerApplication,
    PlayerRequest,
    PlayerRequestStatus,
)


class NotTeamMember(Exception):
    """Действие доступно только участнику команды."""


class NotBookingOwner(Exception):
    """Заявку на бронь может создать только тот, кто её оформил."""


class BookingNotConfirmed(Exception):
    """Искать соперника/игрока имеет смысл только на подтверждённый слот."""


class RequestAlreadyResolved(Exception):
    """Заявка уже закрыта/отменена/на неё уже откликнулись."""


class CannotRespondToOwnRequest(Exception):
    """Команда не может стать соперником самой себе."""


class AlreadyApplied(Exception):
    """Игрок уже откликался на эту заявку."""


class AlreadyTeamMember(Exception):
    """Не имеет смысла проситься в состав команды, в которой уже состоишь."""


def _ensure_team_member(user, team_id: int) -> None:
    if not TeamMembership.objects.filter(team_id=team_id, user=user).exists():
        raise NotTeamMember("Действие доступно только участнику этой команды.")


def create_opponent_request(*, team, booking, creator, message: str = "") -> OpponentRequest:
    _ensure_team_member(creator, team.id)
    if booking.client_id != creator.id:
        raise NotBookingOwner("Заявку на поиск соперника может создать только тот, кто оформил бронь.")
    if booking.status != BookingStatus.CONFIRMED:
        raise BookingNotConfirmed("Слот ещё не подтверждён администратором площадки.")

    return OpponentRequest.objects.create(team=team, booking=booking, message=message, created_by=creator)


def match_opponent_request(*, request_id: int, responder_team, responder) -> OpponentRequest:
    with transaction.atomic():
        req = OpponentRequest.objects.select_for_update().get(pk=request_id)
        if req.status != OpponentRequestStatus.OPEN:
            raise RequestAlreadyResolved(f"Заявка уже в статусе «{req.get_status_display()}».")
        _ensure_team_member(responder, responder_team.id)
        if responder_team.id == req.team_id:
            raise CannotRespondToOwnRequest("Нельзя откликнуться на собственную заявку.")

        req.status = OpponentRequestStatus.MATCHED
        req.matched_team = responder_team
        req.matched_at = timezone.now()
        req.save(update_fields=["status", "matched_team", "matched_at"])
    return req


def cancel_opponent_request(*, request_id: int, user) -> OpponentRequest:
    with transaction.atomic():
        req = OpponentRequest.objects.select_for_update().get(pk=request_id)
        _ensure_team_member(user, req.team_id)
        if req.status != OpponentRequestStatus.OPEN:
            raise RequestAlreadyResolved(f"Заявка уже в статусе «{req.get_status_display()}».")
        req.status = OpponentRequestStatus.CANCELLED
        req.save(update_fields=["status"])
    return req


def create_player_request(*, team, booking, creator, spots_needed: int = 1, message: str = "") -> PlayerRequest:
    _ensure_team_member(creator, team.id)
    return PlayerRequest.objects.create(
        team=team, booking=booking, spots_needed=spots_needed, message=message, created_by=creator
    )


def apply_to_player_request(*, request_id: int, applicant) -> PlayerApplication:
    with transaction.atomic():
        req = PlayerRequest.objects.select_for_update().get(pk=request_id)
        if req.status != PlayerRequestStatus.OPEN:
            raise RequestAlreadyResolved(f"Заявка уже в статусе «{req.get_status_display()}».")
        if TeamMembership.objects.filter(team_id=req.team_id, user=applicant).exists():
            raise AlreadyTeamMember("Вы уже состоите в этой команде.")

        try:
            return PlayerApplication.objects.create(request=req, applicant=applicant)
        except IntegrityError as exc:
            raise AlreadyApplied("Вы уже откликнулись на эту заявку.") from exc


def accept_application(*, application_id: int, decider) -> PlayerApplication:
    with transaction.atomic():
        application = (
            PlayerApplication.objects.select_for_update().select_related("request").get(pk=application_id)
        )
        request_obj = application.request
        _ensure_team_member(decider, request_obj.team_id)
        if application.status != ApplicationStatus.PENDING:
            raise RequestAlreadyResolved(f"Заявка игрока уже в статусе «{application.get_status_display()}».")

        now = timezone.now()
        application.status = ApplicationStatus.ACCEPTED
        application.decided_at = now
        application.save(update_fields=["status", "decided_at"])

        accepted_count = PlayerApplication.objects.filter(
            request_id=request_obj.id, status=ApplicationStatus.ACCEPTED
        ).count()
        if accepted_count >= request_obj.spots_needed and request_obj.status != PlayerRequestStatus.CLOSED:
            request_obj.status = PlayerRequestStatus.CLOSED
            request_obj.save(update_fields=["status"])

    return application


def decline_application(*, application_id: int, decider) -> PlayerApplication:
    with transaction.atomic():
        application = (
            PlayerApplication.objects.select_for_update().select_related("request").get(pk=application_id)
        )
        _ensure_team_member(decider, application.request.team_id)
        if application.status != ApplicationStatus.PENDING:
            raise RequestAlreadyResolved(f"Заявка игрока уже в статусе «{application.get_status_display()}».")

        application.status = ApplicationStatus.DECLINED
        application.decided_at = timezone.now()
        application.save(update_fields=["status", "decided_at"])
    return application
