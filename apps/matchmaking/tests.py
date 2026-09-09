from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.bookings.services import confirm_booking, create_booking
from apps.teams.services import create_team, join_team
from apps.venues.models import FieldSize, SurfaceType, Venue, VenueMembership, VenueRole

from .models import ApplicationStatus, OpponentRequestStatus, PlayerRequestStatus
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
    match_opponent_request,
)


class MatchmakingFixturesMixin:
    def setUp(self):
        super().setUp()
        self.captain = User.objects.create_user(phone="+996700400001", password="x")
        self.teammate = User.objects.create_user(phone="+996700400002", password="x")
        self.rival_captain = User.objects.create_user(phone="+996700400003", password="x")
        self.free_player = User.objects.create_user(phone="+996700400004", password="x")
        self.venue_admin = User.objects.create_user(phone="+996700400005", password="x")

        self.venue = Venue.objects.create(
            name="Арена матчмейкинга",
            address="ул. Тестовая 2",
            surface_type=SurfaceType.TURF,
            field_size=FieldSize.SEVEN,
            price_per_hour=1000,
        )
        VenueMembership.objects.create(venue=self.venue, user=self.venue_admin, role=VenueRole.VENUE_ADMIN)

        self.team = create_team(name="Барс МатчМейк", creator=self.captain)
        join_team(team=self.team, user=self.teammate)
        self.rival_team = create_team(name="Тигр МатчМейк", creator=self.rival_captain)

        start = timezone.now() + timedelta(hours=5)
        end = start + timedelta(hours=1)
        self.confirmed_booking = confirm_booking(
            booking_id=create_booking(
                client=self.captain, venue=self.venue, start_time=start, end_time=end
            ).booking.id,
            admin_user=self.venue_admin,
        )

        start2 = timezone.now() + timedelta(hours=8)
        end2 = start2 + timedelta(hours=1)
        self.pending_booking = create_booking(
            client=self.captain, venue=self.venue, start_time=start2, end_time=end2
        ).booking


class OpponentRequestServiceTests(MatchmakingFixturesMixin, TestCase):
    def test_create_requires_confirmed_booking(self):
        with self.assertRaises(BookingNotConfirmed):
            create_opponent_request(team=self.team, booking=self.pending_booking, creator=self.captain)

    def test_create_requires_booking_owner(self):
        with self.assertRaises(NotBookingOwner):
            create_opponent_request(team=self.team, booking=self.confirmed_booking, creator=self.teammate)

    def test_create_requires_team_member(self):
        with self.assertRaises(NotTeamMember):
            create_opponent_request(team=self.rival_team, booking=self.confirmed_booking, creator=self.captain)

    def test_match_by_rival_team(self):
        req = create_opponent_request(team=self.team, booking=self.confirmed_booking, creator=self.captain)

        matched = match_opponent_request(request_id=req.id, responder_team=self.rival_team, responder=self.rival_captain)

        self.assertEqual(matched.status, OpponentRequestStatus.MATCHED)
        self.assertEqual(matched.matched_team_id, self.rival_team.id)

    def test_cannot_match_own_request(self):
        req = create_opponent_request(team=self.team, booking=self.confirmed_booking, creator=self.captain)

        with self.assertRaises(CannotRespondToOwnRequest):
            match_opponent_request(request_id=req.id, responder_team=self.team, responder=self.teammate)

    def test_cannot_match_twice(self):
        req = create_opponent_request(team=self.team, booking=self.confirmed_booking, creator=self.captain)
        match_opponent_request(request_id=req.id, responder_team=self.rival_team, responder=self.rival_captain)

        third_team = create_team(name="Орёл МатчМейк", creator=self.free_player)
        with self.assertRaises(RequestAlreadyResolved):
            match_opponent_request(request_id=req.id, responder_team=third_team, responder=self.free_player)

    def test_cancel_request(self):
        req = create_opponent_request(team=self.team, booking=self.confirmed_booking, creator=self.captain)

        cancelled = cancel_opponent_request(request_id=req.id, user=self.captain)

        self.assertEqual(cancelled.status, OpponentRequestStatus.CANCELLED)


class PlayerRequestServiceTests(MatchmakingFixturesMixin, TestCase):
    def test_apply_and_accept_closes_request_when_full(self):
        req = create_player_request(
            team=self.team, booking=self.confirmed_booking, creator=self.captain, spots_needed=1
        )

        application = apply_to_player_request(request_id=req.id, applicant=self.free_player)
        self.assertEqual(application.status, ApplicationStatus.PENDING)

        accepted = accept_application(application_id=application.id, decider=self.captain)

        self.assertEqual(accepted.status, ApplicationStatus.ACCEPTED)
        req.refresh_from_db()
        self.assertEqual(req.status, PlayerRequestStatus.CLOSED)

    def test_team_member_cannot_apply(self):
        req = create_player_request(team=self.team, booking=self.confirmed_booking, creator=self.captain)

        with self.assertRaises(AlreadyTeamMember):
            apply_to_player_request(request_id=req.id, applicant=self.teammate)

    def test_cannot_apply_twice(self):
        req = create_player_request(team=self.team, booking=self.confirmed_booking, creator=self.captain)
        apply_to_player_request(request_id=req.id, applicant=self.free_player)

        with self.assertRaises(AlreadyApplied):
            apply_to_player_request(request_id=req.id, applicant=self.free_player)

    def test_non_member_cannot_accept_application(self):
        req = create_player_request(team=self.team, booking=self.confirmed_booking, creator=self.captain)
        application = apply_to_player_request(request_id=req.id, applicant=self.free_player)

        with self.assertRaises(NotTeamMember):
            accept_application(application_id=application.id, decider=self.rival_captain)


class MatchmakingViewsTests(MatchmakingFixturesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_opponent_request_flow_via_api(self):
        self.client.force_authenticate(user=self.captain)
        create_response = self.client.post(
            "/api/matchmaking/opponent-requests/",
            {"team": self.team.id, "booking": self.confirmed_booking.id, "message": "Ищем соперника уровня 5x5"},
        )
        self.assertEqual(create_response.status_code, 201)
        req_id = create_response.data["id"]

        self.client.force_authenticate(user=self.rival_captain)
        match_response = self.client.post(
            f"/api/matchmaking/opponent-requests/{req_id}/match/", {"responder_team": self.rival_team.id}
        )
        self.assertEqual(match_response.status_code, 200)
        self.assertEqual(match_response.data["status"], OpponentRequestStatus.MATCHED)

    def test_player_request_flow_via_api(self):
        self.client.force_authenticate(user=self.captain)
        create_response = self.client.post(
            "/api/matchmaking/player-requests/",
            {"team": self.team.id, "booking": self.confirmed_booking.id, "spots_needed": 1},
        )
        self.assertEqual(create_response.status_code, 201)
        req_id = create_response.data["id"]

        self.client.force_authenticate(user=self.free_player)
        apply_response = self.client.post(f"/api/matchmaking/player-requests/{req_id}/apply/")
        self.assertEqual(apply_response.status_code, 201)
        application_id = apply_response.data["id"]

        self.client.force_authenticate(user=self.captain)
        accept_response = self.client.post(f"/api/matchmaking/applications/{application_id}/accept/")
        self.assertEqual(accept_response.status_code, 200)
        self.assertEqual(accept_response.data["status"], ApplicationStatus.ACCEPTED)
