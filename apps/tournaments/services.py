from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.payments.models import Payment, PaymentStatus, PaymentStrategy
from apps.payments.providers import default_provider_name, get_payment_provider
from apps.teams.models import Match, MatchStatus, TeamMembership
from apps.teams.services import report_match_result as _report_match_result

from .models import RegistrationStatus, Tournament, TournamentMatch, TournamentRegistration, TournamentStatus


class NotTeamMember(Exception):
    """Зарегистрировать команду может только её участник."""


class TournamentNotOpen(Exception):
    """Регистрация на турнир закрыта/отменена/завершена."""


class RegistrationDeadlinePassed(Exception):
    """Дедлайн регистрации уже прошёл."""


class AlreadyRegistered(Exception):
    """Команда уже зарегистрирована на этот турнир."""


class TournamentFull(Exception):
    """Достигнут лимит команд (max_teams)."""


class RegistrationAlreadyResolved(Exception):
    """Регистрация уже отменена/дисквалифицирована — повторное действие не применяется."""


class NotTournamentOrganizer(Exception):
    """Действие доступно только организатору турнира."""


class RegistrationNotEligible(Exception):
    """Эта регистрация не может участвовать в матче (отменена/дисквалифицирована/не из этого турнира)."""


def create_tournament(
    *,
    name: str,
    organizer,
    entry_fee,
    registration_deadline,
    min_teams: int = 4,
    max_teams: int | None = None,
    description: str = "",
    sponsor_name: str = "",
) -> Tournament:
    if registration_deadline <= timezone.now():
        raise RegistrationDeadlinePassed("Дедлайн регистрации должен быть в будущем.")

    with transaction.atomic():
        tournament = Tournament.objects.create(
            name=name,
            description=description,
            sponsor_name=sponsor_name,
            organizer=organizer,
            entry_fee=entry_fee,
            min_teams=min_teams,
            max_teams=max_teams,
            registration_deadline=registration_deadline,
        )
        transaction.on_commit(lambda: _schedule_registration_close(tournament.id))
    return tournament


def _schedule_registration_close(tournament_id: int) -> None:
    from .tasks import close_tournament_registration

    tournament = Tournament.objects.get(pk=tournament_id)
    delay = max((tournament.registration_deadline - timezone.now()).total_seconds(), 0)
    close_tournament_registration.apply_async(args=[tournament_id], countdown=delay)


def register_team(*, tournament: Tournament, team, registrant) -> TournamentRegistration:
    if not TeamMembership.objects.filter(team_id=team.id, user=registrant).exists():
        raise NotTeamMember("Зарегистрировать команду может только её участник.")
    if tournament.status != TournamentStatus.REGISTRATION_OPEN:
        raise TournamentNotOpen(f"Турнир в статусе «{tournament.get_status_display()}», регистрация недоступна.")
    if timezone.now() >= tournament.registration_deadline:
        raise RegistrationDeadlinePassed("Дедлайн регистрации на этот турнир уже прошёл.")
    if tournament.max_teams is not None:
        registered_count = tournament.registrations.filter(status=RegistrationStatus.REGISTERED).count()
        if registered_count >= tournament.max_teams:
            raise TournamentFull(f"Достигнут лимит команд ({tournament.max_teams}).")

    try:
        with transaction.atomic():
            registration = TournamentRegistration.objects.create(
                tournament=tournament, team=team, registered_by=registrant
            )
            provider = get_payment_provider()
            result = provider.hold(reference=f"tournament-entry-{registration.pk}", amount=tournament.entry_fee)
            if not result.success:
                raise TournamentNotOpen(f"Не удалось зарезервировать взнос: {result.error}")
            Payment.objects.create(
                tournament_registration=registration,
                provider=default_provider_name(),
                strategy=provider.strategy,
                amount=tournament.entry_fee,
                status=PaymentStatus.HELD,
                external_id=result.external_id,
            )
    except IntegrityError as exc:
        raise AlreadyRegistered("Команда уже зарегистрирована на этот турнир.") from exc

    return registration


def cancel_registration(*, registration_id: int, user) -> TournamentRegistration:
    with transaction.atomic():
        registration = TournamentRegistration.objects.select_for_update().select_related("tournament").get(
            pk=registration_id
        )
        if not TeamMembership.objects.filter(team_id=registration.team_id, user=user).exists():
            raise NotTeamMember("Отменить регистрацию может только участник команды.")
        if registration.status != RegistrationStatus.REGISTERED:
            raise RegistrationAlreadyResolved(f"Регистрация уже в статусе «{registration.get_status_display()}».")
        if registration.tournament.status != TournamentStatus.REGISTRATION_OPEN:
            raise TournamentNotOpen("Регистрация на турнир уже закрыта — отменить нельзя.")

        registration.status = RegistrationStatus.CANCELLED
        registration.save(update_fields=["status"])

        payment = Payment.objects.select_for_update().get(tournament_registration_id=registration.id)
        _settle_entry_payment(payment, action="release")

    return registration


def cancel_registration_after_payment_failure(registration_id: int) -> TournamentRegistration | None:
    """
    Вызывается вебхуком провайдера (apps.payments.views.freedompay_result),
    когда взнос за участие не подтвердился асинхронно — тот же безопасный
    идемпотентный путь, что apps.bookings.services.expire_booking для
    задатка за площадку: не действует, если регистрация уже не в статусе
    REGISTERED (отменена/дисквалифицирована/турнир уже закрыл регистрацию —
    решать это заново не наше дело), иначе освобождает место под лимитом
    команд (TournamentFull) и возвращает взнос.
    """
    with transaction.atomic():
        try:
            registration = TournamentRegistration.objects.select_for_update().get(pk=registration_id)
        except TournamentRegistration.DoesNotExist:
            return None
        if registration.status != RegistrationStatus.REGISTERED:
            return registration

        registration.status = RegistrationStatus.CANCELLED
        registration.save(update_fields=["status"])

        payment = Payment.objects.select_for_update().get(tournament_registration_id=registration.id)
        _settle_entry_payment(payment, action="release")

    return registration


def _settle_entry_payment(payment: Payment, *, action: str) -> None:
    """
    Действует только на платёж в статусе HELD — тот же guard, что и в
    apps.bookings.services._settle_payment (см. его комментарий): если
    взнос уже FAILED (например вебхук FreedomPay асинхронно сообщил о
    неудаче раньше — apps.payments.views.freedompay_result), снимать
    резерв не с чего, provider.release() звать бессмысленно.
    """
    if payment.status != PaymentStatus.HELD:
        return

    provider = get_payment_provider(payment.strategy)
    if action == "capture":
        result = provider.capture(payment=payment)
        new_status = PaymentStatus.CAPTURED
    else:
        result = provider.release(payment=payment)
        new_status = (
            PaymentStatus.RELEASED if payment.strategy == PaymentStrategy.HOLD_CAPTURE else PaymentStatus.REFUNDED
        )

    payment.status = new_status if result.success else PaymentStatus.FAILED
    if result.external_id:
        payment.external_id = result.external_id
    if action == "capture" and result.success:
        # Комиссия организатора со взноса команды (roadmap 4.1) — только с
        # реально списанной суммы.
        payment.commission_amount = payment.tournament_registration.tournament.commission_on(payment.amount)
    payment.settled_at = timezone.now()
    payment.save(update_fields=["status", "external_id", "commission_amount", "settled_at"])


def close_registration(tournament_id: int) -> Tournament:
    """
    Вызывается по достижении registration_deadline (Celery, см. tasks.py).
    roadmap 4.1, "вопросы механики регистрации": если команд меньше min_teams
    — турнир отменяется, все взносы возвращаются; иначе взносы списываются
    и регистрация закрывается (турнир готов к формированию сетки).
    """
    with transaction.atomic():
        try:
            tournament = Tournament.objects.select_for_update().get(pk=tournament_id)
        except Tournament.DoesNotExist:
            return None
        if tournament.status != TournamentStatus.REGISTRATION_OPEN:
            return tournament  # уже обработано (повторный вызов таймера — no-op)

        registrations = list(
            TournamentRegistration.objects.select_for_update().filter(
                tournament=tournament, status=RegistrationStatus.REGISTERED
            )
        )

        if len(registrations) < tournament.min_teams:
            tournament.status = TournamentStatus.CANCELLED
            tournament.save(update_fields=["status"])
            for registration in registrations:
                registration.status = RegistrationStatus.CANCELLED
                registration.save(update_fields=["status"])
                payment = Payment.objects.select_for_update().get(tournament_registration_id=registration.id)
                _settle_entry_payment(payment, action="release")
        else:
            tournament.status = TournamentStatus.REGISTRATION_CLOSED
            tournament.save(update_fields=["status"])
            for registration in registrations:
                payment = Payment.objects.select_for_update().get(tournament_registration_id=registration.id)
                _settle_entry_payment(payment, action="capture")

    return tournament


def _ensure_organizer(user, tournament: Tournament) -> None:
    if tournament.organizer_id != user.id:
        raise NotTournamentOrganizer("Действие доступно только организатору турнира.")


def _ensure_registration_eligible(registration: TournamentRegistration, tournament: Tournament) -> None:
    if registration.tournament_id != tournament.id:
        raise RegistrationNotEligible("Эта регистрация относится к другому турниру.")
    if registration.status != RegistrationStatus.REGISTERED:
        raise RegistrationNotEligible(f"Команда в статусе «{registration.get_status_display()}», играть не может.")


def schedule_tournament_match(
    *, tournament: Tournament, round_number: int, home_registration, away_registration, organizer, booking=None
) -> TournamentMatch:
    """
    Сознательное упрощение MVP (см. docstring TournamentMatch): организатор
    сам сопоставляет пары по раундам, автогенерации сетки нет. Именно
    организатор турнира (а не участник команды) авторизует матч — это
    отличает создание турнирного матча от обычного schedule_match в apps.teams.
    """
    _ensure_organizer(organizer, tournament)
    if home_registration.id == away_registration.id:
        raise RegistrationNotEligible("Команда не может играть сама с собой.")
    _ensure_registration_eligible(home_registration, tournament)
    _ensure_registration_eligible(away_registration, tournament)

    match = Match.objects.create(
        home_team_id=home_registration.team_id,
        away_team_id=away_registration.team_id,
        booking=booking,
    )
    return TournamentMatch.objects.create(
        tournament=tournament,
        round_number=round_number,
        home_registration=home_registration,
        away_registration=away_registration,
        match=match,
    )


def report_tournament_match_result(*, tournament_match_id: int, reporter, home_score: int, away_score: int):
    """Результат вносит участник одной из играющих команд — делегируем в apps.teams (не дублируем логику)."""
    tournament_match = TournamentMatch.objects.select_related("match").get(pk=tournament_match_id)
    return _report_match_result(
        match_id=tournament_match.match_id, reporter=reporter, home_score=home_score, away_score=away_score
    )


def disqualify_registration(*, registration_id: int, organizer) -> TournamentRegistration:
    """
    roadmap 4.1: неявка команды на свой слот — техническое поражение с
    потерей взноса. Взнос уже списан к этому моменту (close_registration
    списывает при старте турнира) — здесь просто не возвращаем его.
    """
    with transaction.atomic():
        registration = TournamentRegistration.objects.select_for_update().select_related("tournament").get(
            pk=registration_id
        )
        _ensure_organizer(organizer, registration.tournament)
        if registration.status != RegistrationStatus.REGISTERED:
            raise RegistrationAlreadyResolved(f"Регистрация уже в статусе «{registration.get_status_display()}».")

        registration.status = RegistrationStatus.DISQUALIFIED
        registration.save(update_fields=["status"])
    return registration


def get_standings(tournament_id: int) -> list[dict]:
    """
    "Турнирная таблица" (roadmap, раздел 4) — считается на лету по матчам
    этого турнира (3/1/0 очка, как и общий рейтинг команд в apps.teams),
    а не хранится отдельным полем: единственный источник истины — счёт
    в apps.teams.Match.
    """
    registrations = TournamentRegistration.objects.filter(
        tournament_id=tournament_id, status=RegistrationStatus.REGISTERED
    ).select_related("team")

    table = {
        reg.id: {
            "registration_id": reg.id,
            "team_id": reg.team_id,
            "team_name": reg.team.name,
            "played": 0,
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "points": 0,
        }
        for reg in registrations
    }

    matches = TournamentMatch.objects.filter(
        tournament_id=tournament_id, match__status=MatchStatus.PLAYED
    ).select_related("match")

    for tm in matches:
        home_row = table.get(tm.home_registration_id)
        away_row = table.get(tm.away_registration_id)
        if home_row is None or away_row is None:
            continue  # одна из команд отменена/дисквалифицирована после игры — не считаем в таблице
        home_score, away_score = tm.match.home_score, tm.match.away_score
        home_row["played"] += 1
        away_row["played"] += 1
        if home_score > away_score:
            home_row["wins"] += 1
            home_row["points"] += 3
            away_row["losses"] += 1
        elif home_score < away_score:
            away_row["wins"] += 1
            away_row["points"] += 3
            home_row["losses"] += 1
        else:
            home_row["draws"] += 1
            away_row["draws"] += 1
            home_row["points"] += 1
            away_row["points"] += 1

    return sorted(table.values(), key=lambda row: (-row["points"], row["team_name"]))
