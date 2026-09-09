from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.payments.models import Payment, PaymentStatus
from apps.teams.models import MatchStatus
from apps.teams.services import create_team, join_team

from .models import RegistrationStatus, TournamentStatus
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
    cancel_registration_after_payment_failure,
    close_registration,
    create_tournament,
    disqualify_registration,
    get_standings,
    register_team,
    report_tournament_match_result,
    schedule_tournament_match,
)


class TournamentFixturesMixin:
    def setUp(self):
        super().setUp()
        self.organizer = User.objects.create_user(phone="+996700500001", password="x")
        self.captain_a = User.objects.create_user(phone="+996700500002", password="x")
        self.captain_b = User.objects.create_user(phone="+996700500003", password="x")
        self.captain_c = User.objects.create_user(phone="+996700500004", password="x")
        self.outsider = User.objects.create_user(phone="+996700500005", password="x")

        self.team_a = create_team(name="Альфа Турнир", creator=self.captain_a)
        self.team_b = create_team(name="Бета Турнир", creator=self.captain_b)
        self.team_c = create_team(name="Гамма Турнир", creator=self.captain_c)

    def make_tournament(self, min_teams=2, max_teams=None, deadline_hours=1):
        return create_tournament(
            name="Кубок теста",
            organizer=self.organizer,
            entry_fee=500,
            min_teams=min_teams,
            max_teams=max_teams,
            registration_deadline=timezone.now() + timedelta(hours=deadline_hours),
        )


class TournamentRegistrationTests(TournamentFixturesMixin, TestCase):
    def test_register_holds_entry_fee(self):
        tournament = self.make_tournament()

        registration = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

        self.assertEqual(registration.status, RegistrationStatus.REGISTERED)
        payment = Payment.objects.get(tournament_registration=registration)
        self.assertEqual(payment.status, PaymentStatus.HELD)
        self.assertEqual(payment.amount, 500)

    def test_non_member_cannot_register_team(self):
        tournament = self.make_tournament()

        with self.assertRaises(NotTeamMember):
            register_team(tournament=tournament, team=self.team_a, registrant=self.outsider)

    def test_cannot_register_twice(self):
        tournament = self.make_tournament()
        register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

        with self.assertRaises(AlreadyRegistered):
            register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

    def test_max_teams_enforced(self):
        tournament = self.make_tournament(max_teams=1)
        register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

        with self.assertRaises(TournamentFull):
            register_team(tournament=tournament, team=self.team_b, registrant=self.captain_b)

    def test_deadline_in_past_rejected(self):
        with self.assertRaises(RegistrationDeadlinePassed):
            create_tournament(
                name="Просроченный",
                organizer=self.organizer,
                entry_fee=500,
                registration_deadline=timezone.now() - timedelta(hours=1),
            )

    def test_cancel_registration_releases_payment(self):
        tournament = self.make_tournament()
        registration = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

        cancelled = cancel_registration(registration_id=registration.id, user=self.captain_a)

        self.assertEqual(cancelled.status, RegistrationStatus.CANCELLED)
        payment = Payment.objects.get(tournament_registration=registration)
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)

    def test_outsider_cannot_cancel_registration(self):
        tournament = self.make_tournament()
        registration = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

        with self.assertRaises(NotTeamMember):
            cancel_registration(registration_id=registration.id, user=self.outsider)


class TournamentCloseRegistrationTests(TournamentFixturesMixin, TestCase):
    def test_underfilled_tournament_cancelled_and_refunded(self):
        tournament = self.make_tournament(min_teams=3)
        registration = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

        result = close_registration(tournament.id)

        self.assertEqual(result.status, TournamentStatus.CANCELLED)
        registration.refresh_from_db()
        self.assertEqual(registration.status, RegistrationStatus.CANCELLED)
        payment = Payment.objects.get(tournament_registration=registration)
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)

    def test_filled_tournament_closes_and_captures(self):
        tournament = self.make_tournament(min_teams=2)
        reg_a = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)
        reg_b = register_team(tournament=tournament, team=self.team_b, registrant=self.captain_b)

        result = close_registration(tournament.id)

        self.assertEqual(result.status, TournamentStatus.REGISTRATION_CLOSED)
        for reg in (reg_a, reg_b):
            payment = Payment.objects.get(tournament_registration=reg)
            self.assertEqual(payment.status, PaymentStatus.CAPTURED)

    def test_capture_computes_organizer_commission(self):
        # entry_fee=500, organizer_commission_percent по умолчанию из settings (12%) = 60.00
        tournament = self.make_tournament(min_teams=1)
        registration = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

        close_registration(tournament.id)

        payment = Payment.objects.get(tournament_registration=registration)
        self.assertEqual(payment.commission_amount, Decimal("60.00"))

    def test_refund_does_not_record_commission(self):
        tournament = self.make_tournament(min_teams=5)
        registration = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

        close_registration(tournament.id)  # недобор -> отмена и возврат

        payment = Payment.objects.get(tournament_registration=registration)
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)
        self.assertIsNone(payment.commission_amount)

    def test_close_registration_is_idempotent(self):
        tournament = self.make_tournament(min_teams=1)
        register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)
        close_registration(tournament.id)

        result = close_registration(tournament.id)

        self.assertEqual(result.status, TournamentStatus.REGISTRATION_CLOSED)


class TournamentMatchTests(TournamentFixturesMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.tournament = self.make_tournament(min_teams=2)
        self.reg_a = register_team(tournament=self.tournament, team=self.team_a, registrant=self.captain_a)
        self.reg_b = register_team(tournament=self.tournament, team=self.team_b, registrant=self.captain_b)
        close_registration(self.tournament.id)

    def test_only_organizer_can_schedule_match(self):
        with self.assertRaises(NotTournamentOrganizer):
            schedule_tournament_match(
                tournament=self.tournament,
                round_number=1,
                home_registration=self.reg_a,
                away_registration=self.reg_b,
                organizer=self.captain_a,
            )

    def test_organizer_schedules_and_result_updates_standings(self):
        tm = schedule_tournament_match(
            tournament=self.tournament,
            round_number=1,
            home_registration=self.reg_a,
            away_registration=self.reg_b,
            organizer=self.organizer,
        )
        self.assertEqual(tm.match.status, MatchStatus.SCHEDULED)

        report_tournament_match_result(
            tournament_match_id=tm.id, reporter=self.captain_a, home_score=3, away_score=1
        )

        standings = get_standings(self.tournament.id)
        self.assertEqual(standings[0]["team_id"], self.team_a.id)
        self.assertEqual(standings[0]["points"], 3)
        self.assertEqual(standings[1]["points"], 0)

    def test_cannot_schedule_match_for_registration_from_other_tournament(self):
        other_tournament = self.make_tournament(min_teams=1)
        other_reg = register_team(tournament=other_tournament, team=self.team_c, registrant=self.captain_c)

        with self.assertRaises(RegistrationNotEligible):
            schedule_tournament_match(
                tournament=self.tournament,
                round_number=1,
                home_registration=self.reg_a,
                away_registration=other_reg,
                organizer=self.organizer,
            )

    def test_disqualify_forfeits_payment(self):
        disqualify_registration(registration_id=self.reg_b.id, organizer=self.organizer)

        self.reg_b.refresh_from_db()
        self.assertEqual(self.reg_b.status, RegistrationStatus.DISQUALIFIED)
        payment = Payment.objects.get(tournament_registration=self.reg_b)
        self.assertEqual(payment.status, PaymentStatus.CAPTURED)  # взнос не возвращён

    def test_disqualify_twice_raises(self):
        disqualify_registration(registration_id=self.reg_b.id, organizer=self.organizer)

        with self.assertRaises(RegistrationAlreadyResolved):
            disqualify_registration(registration_id=self.reg_b.id, organizer=self.organizer)


class TournamentViewsTests(TournamentFixturesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_full_tournament_flow_via_api(self):
        self.client.force_authenticate(user=self.organizer)
        create_response = self.client.post(
            "/api/tournaments/",
            {
                "name": "Кубок API",
                "entry_fee": "500.00",
                "min_teams": 2,
                "registration_deadline": (timezone.now() + timedelta(hours=1)).isoformat(),
            },
        )
        self.assertEqual(create_response.status_code, 201)
        tournament_id = create_response.data["id"]

        self.client.force_authenticate(user=self.captain_a)
        reg_a_response = self.client.post(
            f"/api/tournaments/{tournament_id}/registrations/", {"team": self.team_a.id}
        )
        self.assertEqual(reg_a_response.status_code, 201)

        self.client.force_authenticate(user=self.captain_b)
        reg_b_response = self.client.post(
            f"/api/tournaments/{tournament_id}/registrations/", {"team": self.team_b.id}
        )
        self.assertEqual(reg_b_response.status_code, 201)

        close_registration(tournament_id)

        self.client.force_authenticate(user=self.organizer)
        match_response = self.client.post(
            f"/api/tournaments/{tournament_id}/matches/",
            {
                "round_number": 1,
                "home_registration": reg_a_response.data["id"],
                "away_registration": reg_b_response.data["id"],
            },
        )
        self.assertEqual(match_response.status_code, 201)
        match_id = match_response.data["id"]

        self.client.force_authenticate(user=self.captain_a)
        result_response = self.client.post(
            f"/api/tournaments/matches/{match_id}/report-result/", {"home_score": 2, "away_score": 0}
        )
        self.assertEqual(result_response.status_code, 200)

        standings_response = self.client.get(f"/api/tournaments/{tournament_id}/standings/")
        self.assertEqual(standings_response.status_code, 200)
        self.assertEqual(standings_response.data[0]["team_id"], self.team_a.id)


class PaymentFailureCleanupTests(TournamentFixturesMixin, TestCase):
    """
    Симметрично apps/bookings/tests.py::ConfirmDeclineBookingTests — здесь
    проверяется тот же путь на уровне сервиса (не только через вебхук,
    см. apps/payments/tests.py::FreedomPayWebhookTests, которая гоняет
    этот же сценарий сквозным HTTP-запросом).
    """

    def test_cancels_registered_registration_and_frees_slot(self):
        """
        Вызов напрямую (не через вебхук) застаёт платёж ещё в HELD — release()
        отрабатывает штатно и возвращает деньги (REFUNDED). FAILED — только
        когда вебхук сам уже пометил платёж так до этого вызова, см.
        apps/payments/tests.py::test_failed_result_cancels_tournament_registration_and_frees_slot.
        """
        tournament = self.make_tournament(min_teams=1, max_teams=1)
        registration = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)

        result = cancel_registration_after_payment_failure(registration.id)

        self.assertEqual(result.status, RegistrationStatus.CANCELLED)
        payment = Payment.objects.get(tournament_registration=registration)
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)

        # Место под max_teams=1 освободилось.
        second = register_team(tournament=tournament, team=self.team_b, registrant=self.captain_b)
        self.assertEqual(second.status, RegistrationStatus.REGISTERED)

    def test_noop_if_already_cancelled_by_user(self):
        """Гонка: пользователь сам отменил регистрацию раньше, чем пришёл вебхук о неудаче."""
        tournament = self.make_tournament(min_teams=1)
        registration = register_team(tournament=tournament, team=self.team_a, registrant=self.captain_a)
        cancel_registration(registration_id=registration.id, user=self.captain_a)

        result = cancel_registration_after_payment_failure(registration.id)

        self.assertEqual(result.status, RegistrationStatus.CANCELLED)
        payment = Payment.objects.get(tournament_registration=registration)
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)  # оставлен как есть от cancel_registration

    def test_noop_for_unknown_registration(self):
        result = cancel_registration_after_payment_failure(999999)
        self.assertIsNone(result)
