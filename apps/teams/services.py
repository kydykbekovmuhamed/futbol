from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Match, MatchStatus, Team, TeamMembership, TeamRole

# Очковая система за результат матча (roadmap Этап 2: "рейтинг команд",
# без уточнения формулы — выбрана привычная футбольная схема 3/1/0).
POINTS_FOR_WIN = 3
POINTS_FOR_DRAW = 1
POINTS_FOR_LOSS = 0


class AlreadyTeamMember(Exception):
    """Пользователь уже состоит в этой команде."""


class NotTeamMember(Exception):
    """Пользователь не состоит в команде — действие недоступно."""


class TeamNameTaken(Exception):
    """Команда с таким именем уже существует."""


class MatchAlreadyReported(Exception):
    """Результат этого матча уже зафиксирован."""


class NotMatchParticipant(Exception):
    """Результат может внести только участник одной из двух команд матча."""


def create_team(*, name: str, creator, district: str = "", description: str = "") -> Team:
    try:
        with transaction.atomic():
            team = Team.objects.create(name=name, district=district, description=description)
            TeamMembership.objects.create(team=team, user=creator, role=TeamRole.CAPTAIN)
    except IntegrityError as exc:
        raise TeamNameTaken(f"Команда с именем «{name}» уже существует.") from exc
    return team


def join_team(*, team: Team, user) -> TeamMembership:
    try:
        return TeamMembership.objects.create(team=team, user=user, role=TeamRole.MEMBER)
    except IntegrityError as exc:
        raise AlreadyTeamMember("Вы уже состоите в этой команде.") from exc


def leave_team(*, team: Team, user) -> None:
    deleted, _ = TeamMembership.objects.filter(team=team, user=user).delete()
    if not deleted:
        raise NotTeamMember("Вы не состоите в этой команде.")


def _is_member(user, team_id: int) -> bool:
    return TeamMembership.objects.filter(team_id=team_id, user=user).exists()


def schedule_match(*, home_team: Team, away_team: Team, organizer, booking=None) -> Match:
    if not (_is_member(organizer, home_team.id) or _is_member(organizer, away_team.id)):
        raise NotTeamMember("Матч может создать только участник одной из двух команд.")
    return Match.objects.create(home_team=home_team, away_team=away_team, booking=booking)


def report_match_result(*, match_id: int, reporter, home_score: int, away_score: int) -> Match:
    with transaction.atomic():
        match = Match.objects.select_for_update().get(pk=match_id)
        if match.status == MatchStatus.PLAYED:
            raise MatchAlreadyReported("Результат этого матча уже внесён.")
        if not (_is_member(reporter, match.home_team_id) or _is_member(reporter, match.away_team_id)):
            raise NotMatchParticipant("Результат может внести только участник одной из команд.")

        match.home_score = home_score
        match.away_score = away_score
        match.status = MatchStatus.PLAYED
        match.reported_by = reporter
        match.played_at = timezone.now()
        match.save(update_fields=["home_score", "away_score", "status", "reported_by", "played_at"])

        home_team = Team.objects.select_for_update().get(pk=match.home_team_id)
        away_team = Team.objects.select_for_update().get(pk=match.away_team_id)
        home_old_points, home_old_rank = home_team.rating_points, home_team.rank_title
        away_old_points, away_old_rank = away_team.rating_points, away_team.rank_title

        _apply_result(home_team, away_team, home_score, away_score)
        home_team.save(update_fields=["wins", "draws", "losses", "rating_points"])
        away_team.save(update_fields=["wins", "draws", "losses", "rating_points"])

        # Лента активности/push на основе поведения (roadmap, Этап 3) —
        # после коммита, чтобы падение уведомления не откатило сам результат.
        transaction.on_commit(
            lambda: _notify_rating_changes(
                home_team, home_team.rating_points - home_old_points, home_old_rank,
                away_team, away_team.rating_points - away_old_points, away_old_rank,
            )
        )

    return match


def _notify_rating_changes(home_team, home_delta, home_old_rank, away_team, away_delta, away_old_rank) -> None:
    from apps.community.services import notify_rating_change

    notify_rating_change(team=home_team, points_delta=home_delta, old_rank_title=home_old_rank)
    notify_rating_change(team=away_team, points_delta=away_delta, old_rank_title=away_old_rank)


def _apply_result(home_team: Team, away_team: Team, home_score: int, away_score: int) -> None:
    if home_score > away_score:
        home_team.wins += 1
        home_team.rating_points += POINTS_FOR_WIN
        away_team.losses += 1
        away_team.rating_points += POINTS_FOR_LOSS
    elif home_score < away_score:
        away_team.wins += 1
        away_team.rating_points += POINTS_FOR_WIN
        home_team.losses += 1
        home_team.rating_points += POINTS_FOR_LOSS
    else:
        home_team.draws += 1
        away_team.draws += 1
        home_team.rating_points += POINTS_FOR_DRAW
        away_team.rating_points += POINTS_FOR_DRAW
