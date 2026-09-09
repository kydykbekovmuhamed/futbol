from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.notifications.providers import get_notification_provider
from apps.payments.models import Payment, PaymentStatus
from apps.payments.providers import default_provider_name, get_payment_provider
from apps.teams.models import MatchStatus, TeamMembership

from .models import ActivityEvent, ActivityEventType, Challenge, ChallengeStatus, TeamSubscription


class SubscriptionRequired(Exception):
    """Расширенная статистика доступна только по активной подписке команды."""


class NotTeamMember(Exception):
    """Действие доступно только участнику команды."""


class ChallengeAlreadyResolved(Exception):
    """Вызов уже принят/отклонён/отменён — повторное действие не применяется."""


class CannotChallengeOwnTeam(Exception):
    """Команда не может бросить вызов сама себе."""


class SubscriptionPaymentFailed(Exception):
    """Не удалось провести оплату подписки."""


def _team_member_ids(team_id: int):
    return TeamMembership.objects.filter(team_id=team_id).values_list("user_id", flat=True)


def _push_all(user_ids, title: str, body: str) -> None:
    from apps.accounts.models import User

    provider = get_notification_provider()
    for phone in User.objects.filter(id__in=user_ids).values_list("phone", flat=True):
        provider.send_push(phone=phone, title=title, body=body)


def _create_events_for_team(team_id, event_type, title, body) -> None:
    user_ids = list(_team_member_ids(team_id))
    ActivityEvent.objects.bulk_create(
        [ActivityEvent(user_id=uid, event_type=event_type, title=title, body=body) for uid in user_ids]
    )
    _push_all(user_ids, title, body)


def notify_rating_change(*, team, points_delta: int, old_rank_title: str) -> None:
    """
    Вызывается apps.teams.services.report_match_result после начисления
    очков (roadmap, Этап 3: "твоя команда поднялась в рейтинге" + push на
    основе поведения). Не в транзакции с самим начислением очков —
    уведомление не должно откатывать сохранённый результат матча, если
    вдруг упадёт push.
    """
    sign = "+" if points_delta >= 0 else ""
    _create_events_for_team(
        team.id,
        ActivityEventType.RATING_CHANGED,
        "Рейтинг команды изменился",
        f"«{team.name}»: {sign}{points_delta} очков, теперь {team.rating_points}.",
    )

    if team.rank_title != old_rank_title:
        to_next = team.points_to_next_rank
        progress = f" До следующего звания: {to_next} очков." if to_next is not None else " Это высшее звание!"
        _create_events_for_team(
            team.id,
            ActivityEventType.RANK_UP,
            f"Новое звание: {team.rank_title}",
            f"«{team.name}» теперь «{team.rank_title}».{progress}",
        )


def create_challenge(*, challenger_team, opponent_team, creator, message: str = "", proposed_time=None) -> Challenge:
    if not TeamMembership.objects.filter(team_id=challenger_team.id, user=creator).exists():
        raise NotTeamMember("Бросить вызов от имени команды может только её участник.")
    if challenger_team.id == opponent_team.id:
        raise CannotChallengeOwnTeam("Нельзя бросить вызов самим себе.")

    challenge = Challenge.objects.create(
        challenger_team=challenger_team,
        opponent_team=opponent_team,
        message=message,
        proposed_time=proposed_time,
        created_by=creator,
    )

    when = f" на {proposed_time:%d.%m %H:%M}" if proposed_time else ""
    _create_events_for_team(
        opponent_team.id,
        ActivityEventType.CHALLENGE_RECEIVED,
        f"Вам бросили вызов: «{challenger_team.name}»",
        f"«{challenger_team.name}» зовёт сыграть{when}." + (f" {message}" if message else ""),
    )
    return challenge


def _respond(*, challenge_id: int, responder, new_status: str, event_type, event_title: str) -> Challenge:
    with transaction.atomic():
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)
        if not TeamMembership.objects.filter(team_id=challenge.opponent_team_id, user=responder).exists():
            raise NotTeamMember("Ответить на вызов может только участник команды-адресата.")
        if challenge.status != ChallengeStatus.PENDING:
            raise ChallengeAlreadyResolved(f"Вызов уже в статусе «{challenge.get_status_display()}».")

        challenge.status = new_status
        challenge.responded_at = timezone.now()
        challenge.save(update_fields=["status", "responded_at"])

    _create_events_for_team(
        challenge.challenger_team_id,
        event_type,
        event_title,
        f"«{challenge.opponent_team.name}» ответила на ваш вызов.",
    )
    return challenge


def accept_challenge(*, challenge_id: int, responder) -> Challenge:
    return _respond(
        challenge_id=challenge_id,
        responder=responder,
        new_status=ChallengeStatus.ACCEPTED,
        event_type=ActivityEventType.CHALLENGE_ACCEPTED,
        event_title="Вызов принят",
    )


def decline_challenge(*, challenge_id: int, responder) -> Challenge:
    return _respond(
        challenge_id=challenge_id,
        responder=responder,
        new_status=ChallengeStatus.DECLINED,
        event_type=ActivityEventType.CHALLENGE_DECLINED,
        event_title="Вызов отклонён",
    )


def cancel_challenge(*, challenge_id: int, canceller) -> Challenge:
    with transaction.atomic():
        challenge = Challenge.objects.select_for_update().get(pk=challenge_id)
        if not TeamMembership.objects.filter(team_id=challenge.challenger_team_id, user=canceller).exists():
            raise NotTeamMember("Отменить вызов может только команда, которая его бросила.")
        if challenge.status != ChallengeStatus.PENDING:
            raise ChallengeAlreadyResolved(f"Вызов уже в статусе «{challenge.get_status_display()}».")

        challenge.status = ChallengeStatus.CANCELLED
        challenge.responded_at = timezone.now()
        challenge.save(update_fields=["status", "responded_at"])
    return challenge


def subscribe_team(*, team, activator) -> TeamSubscription:
    """
    Разовая оплата на TEAM_SUBSCRIPTION_DURATION_DAYS дней (см. docstring
    TeamSubscription) — списывается сразу (hold+immediate capture), в
    отличие от задатка за площадку здесь не нужен разрыв во времени между
    резервированием и подтверждением. Продление — повторный вызов этой же
    функции: срок считается от текущего expires_at, если подписка ещё
    активна (не сгорает оставшееся время при досрочном продлении), иначе
    от текущего момента. Каждый вызов — отдельная строка Payment (см.
    Payment.team_subscription — обычный FK, не OneToOne).
    """
    if not TeamMembership.objects.filter(team_id=team.id, user=activator).exists():
        raise NotTeamMember("Оформить подписку может только участник команды.")

    subscription, _created = TeamSubscription.objects.get_or_create(team=team)

    price = settings.TEAM_SUBSCRIPTION_PRICE
    provider = get_payment_provider()
    hold_result = provider.hold(reference=f"team-subscription-{subscription.id}", amount=price)
    if not hold_result.success:
        raise SubscriptionPaymentFailed(f"Не удалось провести оплату: {hold_result.error}")

    payment = Payment.objects.create(
        team_subscription=subscription,
        provider=default_provider_name(),
        strategy=provider.strategy,
        amount=price,
        status=PaymentStatus.HELD,
        external_id=hold_result.external_id,
    )
    capture_result = provider.capture(payment=payment)

    # Отдельная атомарная секция только на "успех списания -> продлить
    # подписку" — если capture провалился, FAILED-статус на payment всё
    # равно должен сохраниться (аудит), поэтому raise ниже — уже вне atomic.
    with transaction.atomic():
        payment.status = PaymentStatus.CAPTURED if capture_result.success else PaymentStatus.FAILED
        if capture_result.external_id:
            payment.external_id = capture_result.external_id
        payment.settled_at = timezone.now()
        payment.save(update_fields=["status", "external_id", "settled_at"])

        if capture_result.success:
            now = timezone.now()
            base = subscription.expires_at if subscription.expires_at and subscription.expires_at > now else now
            subscription.expires_at = base + timezone.timedelta(days=settings.TEAM_SUBSCRIPTION_DURATION_DAYS)
            subscription.save(update_fields=["expires_at"])

    if not capture_result.success:
        raise SubscriptionPaymentFailed(f"Не удалось списать оплату: {capture_result.error}")

    return subscription


def get_local_schedule(*, limit: int = 50) -> list[dict]:
    """
    roadmap, Этап 3: "Расписание/результаты местных турниров" — тонкая
    агрегация уже существующих данных Этапа 2 (apps.tournaments), без новой
    модели: собственные данные платформы, свободный контент (roadmap, раздел 5).
    """
    from apps.tournaments.models import TournamentMatch

    rows = TournamentMatch.objects.select_related(
        "tournament", "match", "match__booking__venue", "home_registration__team", "away_registration__team"
    ).order_by("-created_at")[:limit]

    result = []
    for tm in rows:
        booking = tm.match.booking
        result.append(
            {
                "tournament_match_id": tm.id,
                "tournament_name": tm.tournament.name,
                "round_number": tm.round_number,
                "home_team_name": tm.home_registration.team.name,
                "away_team_name": tm.away_registration.team.name,
                "match_status": tm.match.status,
                "home_score": tm.match.home_score,
                "away_score": tm.match.away_score,
                "venue_name": booking.venue.name if booking else None,
                "scheduled_at": booking.start_time if booking else None,
            }
        )
    return result


def get_extended_stats(*, team) -> dict:
    """
    Расширенная статистика (roadmap, раздел 3: "Подписка игроков/команд") —
    доступна только по активной подписке команды. За основу берём те же
    сыгранные матчи, что формируют базовый Team.rating_points/wins/etc —
    отдельного хранилища для "расширенной" версии не заводим, считаем на лету.
    """
    from apps.teams.models import Match

    subscription = getattr(team, "subscription", None)
    if subscription is None or not subscription.is_active:
        raise SubscriptionRequired("Расширенная статистика доступна только по активной подписке команды.")

    matches = list(
        Match.objects.filter(
            Q(home_team_id=team.id) | Q(away_team_id=team.id), status=MatchStatus.PLAYED
        ).order_by("played_at")
    )

    monthly: dict[str, dict] = {}
    longest_streak = 0
    current_streak = 0
    total_wins = 0

    for match in matches:
        is_home = match.home_team_id == team.id
        team_score = match.home_score if is_home else match.away_score
        opponent_score = match.away_score if is_home else match.home_score

        if team_score > opponent_score:
            outcome = "win"
            total_wins += 1
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0
            outcome = "draw" if team_score == opponent_score else "loss"

        month_key = match.played_at.strftime("%Y-%m") if match.played_at else "unknown"
        bucket = monthly.setdefault(month_key, {"month": month_key, "wins": 0, "draws": 0, "losses": 0})
        bucket[{"win": "wins", "draw": "draws", "loss": "losses"}[outcome]] += 1

    games_played = len(matches)
    win_rate = round(100 * total_wins / games_played, 1) if games_played else 0.0

    return {
        "team_id": team.id,
        "team_name": team.name,
        "rank_title": team.rank_title,
        "points_to_next_rank": team.points_to_next_rank,
        "games_played": games_played,
        "win_rate_percent": win_rate,
        "monthly_breakdown": sorted(monthly.values(), key=lambda row: row["month"]),
        "longest_win_streak": longest_streak,
    }
