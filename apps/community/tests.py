from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.payments.models import Payment, PaymentStatus
from apps.teams.services import create_team, join_team, report_match_result, schedule_match

from .models import ActivityEvent, ActivityEventType, ChallengeStatus, NewsItem, TeamSubscription
from .services import (
    CannotChallengeOwnTeam,
    ChallengeAlreadyResolved,
    NotTeamMember,
    SubscriptionRequired,
    accept_challenge,
    cancel_challenge,
    create_challenge,
    decline_challenge,
    get_extended_stats,
    get_local_schedule,
    subscribe_team,
)


class CommunityFixturesMixin:
    def setUp(self):
        super().setUp()
        self.captain_a = User.objects.create_user(phone="+996700800001", password="x")
        self.player_a = User.objects.create_user(phone="+996700800002", password="x")
        self.captain_b = User.objects.create_user(phone="+996700800003", password="x")
        self.outsider = User.objects.create_user(phone="+996700800004", password="x")

        self.team_a = create_team(name="Барс Комьюнити", creator=self.captain_a)
        join_team(team=self.team_a, user=self.player_a)
        self.team_b = create_team(name="Тигр Комьюнити", creator=self.captain_b)


class RatingNotificationTests(CommunityFixturesMixin, TestCase):
    def test_report_result_creates_activity_events_and_rank_up(self):
        """
        Первый порог звания — на 0 очках ("Новичок"), следующий — на 10
        ("Любитель"): ставим команду на 9 очков, победа (+3) пересекает порог.
        """
        self.team_a.rating_points = 9
        self.team_a.save(update_fields=["rating_points"])
        match = schedule_match(home_team=self.team_a, away_team=self.team_b, organizer=self.captain_a)

        with self.captureOnCommitCallbacks(execute=True):
            report_match_result(match_id=match.id, reporter=self.captain_a, home_score=3, away_score=0)

        events = ActivityEvent.objects.filter(user=self.captain_a)
        self.assertTrue(events.filter(event_type=ActivityEventType.RATING_CHANGED).exists())
        self.assertTrue(events.filter(event_type=ActivityEventType.RANK_UP).exists())
        # У обоих участников команды-победителя (капитан и игрок) — своя копия события.
        self.assertTrue(ActivityEvent.objects.filter(user=self.player_a).exists())

    def test_losing_team_gets_rating_event_without_rank_up(self):
        match = schedule_match(home_team=self.team_a, away_team=self.team_b, organizer=self.captain_a)

        with self.captureOnCommitCallbacks(execute=True):
            report_match_result(match_id=match.id, reporter=self.captain_a, home_score=0, away_score=3)

        events = ActivityEvent.objects.filter(user=self.captain_a)
        self.assertTrue(events.filter(event_type=ActivityEventType.RATING_CHANGED).exists())
        self.assertFalse(events.filter(event_type=ActivityEventType.RANK_UP).exists())


class ChallengeServiceTests(CommunityFixturesMixin, TestCase):
    def test_create_challenge_notifies_opponent(self):
        challenge = create_challenge(challenger_team=self.team_a, opponent_team=self.team_b, creator=self.captain_a)

        self.assertEqual(challenge.status, ChallengeStatus.PENDING)
        self.assertTrue(
            ActivityEvent.objects.filter(
                user=self.captain_b, event_type=ActivityEventType.CHALLENGE_RECEIVED
            ).exists()
        )

    def test_non_member_cannot_challenge(self):
        with self.assertRaises(NotTeamMember):
            create_challenge(challenger_team=self.team_a, opponent_team=self.team_b, creator=self.outsider)

    def test_cannot_challenge_own_team(self):
        with self.assertRaises(CannotChallengeOwnTeam):
            create_challenge(challenger_team=self.team_a, opponent_team=self.team_a, creator=self.captain_a)

    def test_opponent_accepts(self):
        challenge = create_challenge(challenger_team=self.team_a, opponent_team=self.team_b, creator=self.captain_a)

        accepted = accept_challenge(challenge_id=challenge.id, responder=self.captain_b)

        self.assertEqual(accepted.status, ChallengeStatus.ACCEPTED)
        self.assertTrue(
            ActivityEvent.objects.filter(
                user=self.captain_a, event_type=ActivityEventType.CHALLENGE_ACCEPTED
            ).exists()
        )

    def test_challenger_team_member_cannot_accept_own_challenge(self):
        challenge = create_challenge(challenger_team=self.team_a, opponent_team=self.team_b, creator=self.captain_a)

        with self.assertRaises(NotTeamMember):
            accept_challenge(challenge_id=challenge.id, responder=self.captain_a)

    def test_decline(self):
        challenge = create_challenge(challenger_team=self.team_a, opponent_team=self.team_b, creator=self.captain_a)

        declined = decline_challenge(challenge_id=challenge.id, responder=self.captain_b)

        self.assertEqual(declined.status, ChallengeStatus.DECLINED)

    def test_cannot_respond_twice(self):
        challenge = create_challenge(challenger_team=self.team_a, opponent_team=self.team_b, creator=self.captain_a)
        accept_challenge(challenge_id=challenge.id, responder=self.captain_b)

        with self.assertRaises(ChallengeAlreadyResolved):
            decline_challenge(challenge_id=challenge.id, responder=self.captain_b)

    def test_challenger_can_cancel(self):
        challenge = create_challenge(challenger_team=self.team_a, opponent_team=self.team_b, creator=self.captain_a)

        cancelled = cancel_challenge(challenge_id=challenge.id, canceller=self.captain_a)

        self.assertEqual(cancelled.status, ChallengeStatus.CANCELLED)

    def test_opponent_cannot_cancel(self):
        challenge = create_challenge(challenger_team=self.team_a, opponent_team=self.team_b, creator=self.captain_a)

        with self.assertRaises(NotTeamMember):
            cancel_challenge(challenge_id=challenge.id, canceller=self.captain_b)


class SubscriptionAndStatsTests(CommunityFixturesMixin, TestCase):
    def test_subscribe_creates_captured_payment_and_activates(self):
        subscription = subscribe_team(team=self.team_a, activator=self.captain_a)

        self.assertTrue(subscription.is_active)
        payment = Payment.objects.get(team_subscription=subscription)
        self.assertEqual(payment.status, PaymentStatus.CAPTURED)
        self.assertEqual(payment.amount, Decimal(str(500)))

    def test_non_member_cannot_subscribe(self):
        with self.assertRaises(NotTeamMember):
            subscribe_team(team=self.team_a, activator=self.outsider)

    def test_renewal_extends_from_current_expiry_not_now(self):
        first = subscribe_team(team=self.team_a, activator=self.captain_a)
        original_expiry = first.expires_at

        second = subscribe_team(team=self.team_a, activator=self.captain_a)

        self.assertEqual(
            second.expires_at,
            original_expiry + timedelta(days=30),
        )
        self.assertEqual(Payment.objects.filter(team_subscription=first).count(), 2)

    def test_extended_stats_requires_active_subscription(self):
        with self.assertRaises(SubscriptionRequired):
            get_extended_stats(team=self.team_a)

    def test_extended_stats_after_subscription(self):
        subscribe_team(team=self.team_a, activator=self.captain_a)
        match = schedule_match(home_team=self.team_a, away_team=self.team_b, organizer=self.captain_a)
        report_match_result(match_id=match.id, reporter=self.captain_a, home_score=2, away_score=1)

        stats = get_extended_stats(team=self.team_a)

        self.assertEqual(stats["games_played"], 1)
        self.assertEqual(stats["win_rate_percent"], 100.0)
        self.assertEqual(stats["longest_win_streak"], 1)
        self.assertEqual(len(stats["monthly_breakdown"]), 1)


class CommunityViewsTests(CommunityFixturesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_feed_and_mark_read(self):
        create_challenge(challenger_team=self.team_a, opponent_team=self.team_b, creator=self.captain_a)

        self.client.force_authenticate(user=self.captain_b)
        feed_response = self.client.get("/api/community/feed/")
        self.assertEqual(feed_response.status_code, 200)
        self.assertEqual(len(feed_response.data), 1)

        event_id = feed_response.data[0]["id"]
        mark_response = self.client.post(f"/api/community/feed/{event_id}/mark-read/")
        self.assertEqual(mark_response.status_code, 204)
        self.assertTrue(ActivityEvent.objects.get(pk=event_id).is_read)

    def test_challenge_flow_via_api(self):
        self.client.force_authenticate(user=self.captain_a)
        create_response = self.client.post(
            "/api/community/challenges/", {"challenger_team": self.team_a.id, "opponent_team": self.team_b.id}
        )
        self.assertEqual(create_response.status_code, 201)
        challenge_id = create_response.data["id"]

        self.client.force_authenticate(user=self.captain_b)
        accept_response = self.client.post(f"/api/community/challenges/{challenge_id}/accept/")
        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.data["status"], ChallengeStatus.ACCEPTED)

    def test_news_list(self):
        NewsItem.objects.create(
            title="Открылась новая площадка",
            source_name="Футбол KG",
            source_url="https://example.com/news/1",
            published_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.captain_a)

        response = self.client.get("/api/community/news/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_subscribe_and_extended_stats_via_api(self):
        self.client.force_authenticate(user=self.captain_a)

        subscribe_response = self.client.post(f"/api/community/teams/{self.team_a.id}/subscribe/")
        self.assertEqual(subscribe_response.status_code, 201)
        self.assertTrue(subscribe_response.data["is_active"])

        stats_response = self.client.get(f"/api/community/teams/{self.team_a.id}/extended-stats/")
        self.assertEqual(stats_response.status_code, 200)

    def test_extended_stats_without_subscription_returns_402(self):
        self.client.force_authenticate(user=self.captain_a)

        response = self.client.get(f"/api/community/teams/{self.team_a.id}/extended-stats/")

        self.assertEqual(response.status_code, 402)


class LocalScheduleTests(CommunityFixturesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_includes_tournament_match_with_result(self):
        from apps.tournaments.services import (
            close_registration,
            create_tournament,
            register_team,
            report_tournament_match_result,
            schedule_tournament_match,
        )

        tournament = create_tournament(
            name="Кубок расписания",
            organizer=self.outsider,
            entry_fee=100,
            min_teams=2,
            registration_deadline=timezone.now() + timedelta(hours=1),
        )
        reg_a = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)
        reg_b = register_team(tournament=tournament, team=self.team_b, registrant=self.captain_b)
        close_registration(tournament.id)
        tm = schedule_tournament_match(
            tournament=tournament, round_number=1, home_registration=reg_a, away_registration=reg_b,
            organizer=self.outsider,
        )
        report_tournament_match_result(tournament_match_id=tm.id, reporter=self.captain_a, home_score=2, away_score=1)

        schedule = get_local_schedule()

        row = next(r for r in schedule if r["tournament_match_id"] == tm.id)
        self.assertEqual(row["home_team_name"], self.team_a.name)
        self.assertEqual(row["home_score"], 2)
        self.assertEqual(row["away_score"], 1)
        self.assertIsNone(row["venue_name"])  # матч не привязан к брони площадки

    def test_local_schedule_via_api(self):
        self.client.force_authenticate(user=self.captain_a)

        response = self.client.get("/api/community/local-schedule/")

        self.assertEqual(response.status_code, 200)
