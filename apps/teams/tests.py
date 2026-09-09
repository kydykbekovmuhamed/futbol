from django.test import TestCase
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User

from .models import Match, MatchStatus, Team, TeamMembership, TeamRole
from .services import (
    AlreadyTeamMember,
    MatchAlreadyReported,
    NotMatchParticipant,
    NotTeamMember,
    TeamNameTaken,
    create_team,
    join_team,
    leave_team,
    report_match_result,
    schedule_match,
)


class TeamFixturesMixin:
    def setUp(self):
        super().setUp()
        self.captain = User.objects.create_user(phone="+996700300001", password="x")
        self.player = User.objects.create_user(phone="+996700300002", password="x")
        self.outsider = User.objects.create_user(phone="+996700300003", password="x")


class TeamServiceTests(TeamFixturesMixin, TestCase):
    def test_create_team_makes_creator_captain(self):
        team = create_team(name="Барс", creator=self.captain)

        membership = TeamMembership.objects.get(team=team, user=self.captain)
        self.assertEqual(membership.role, TeamRole.CAPTAIN)

    def test_duplicate_team_name_rejected(self):
        create_team(name="Барс", creator=self.captain)

        with self.assertRaises(TeamNameTaken):
            create_team(name="Барс", creator=self.player)

    def test_join_and_leave_team(self):
        team = create_team(name="Барс", creator=self.captain)

        join_team(team=team, user=self.player)
        self.assertTrue(TeamMembership.objects.filter(team=team, user=self.player).exists())

        leave_team(team=team, user=self.player)
        self.assertFalse(TeamMembership.objects.filter(team=team, user=self.player).exists())

    def test_cannot_join_twice(self):
        team = create_team(name="Барс", creator=self.captain)
        join_team(team=team, user=self.player)

        with self.assertRaises(AlreadyTeamMember):
            join_team(team=team, user=self.player)

    def test_leaving_team_you_are_not_in_raises(self):
        team = create_team(name="Барс", creator=self.captain)

        with self.assertRaises(NotTeamMember):
            leave_team(team=team, user=self.outsider)


class MatchServiceTests(TeamFixturesMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.home = create_team(name="Барс", creator=self.captain)
        self.away = create_team(name="Тигр", creator=self.player)

    def test_outsider_cannot_schedule_match(self):
        with self.assertRaises(NotTeamMember):
            schedule_match(home_team=self.home, away_team=self.away, organizer=self.outsider)

    def test_team_member_can_schedule_match(self):
        match = schedule_match(home_team=self.home, away_team=self.away, organizer=self.captain)

        self.assertEqual(match.status, MatchStatus.SCHEDULED)

    def test_report_result_updates_ratings(self):
        match = schedule_match(home_team=self.home, away_team=self.away, organizer=self.captain)

        report_match_result(match_id=match.id, reporter=self.captain, home_score=3, away_score=1)

        self.home.refresh_from_db()
        self.away.refresh_from_db()
        self.assertEqual(self.home.wins, 1)
        self.assertEqual(self.home.rating_points, 3)
        self.assertEqual(self.away.losses, 1)
        self.assertEqual(self.away.rating_points, 0)

    def test_draw_gives_both_teams_a_point(self):
        match = schedule_match(home_team=self.home, away_team=self.away, organizer=self.captain)

        report_match_result(match_id=match.id, reporter=self.captain, home_score=2, away_score=2)

        self.home.refresh_from_db()
        self.away.refresh_from_db()
        self.assertEqual(self.home.draws, 1)
        self.assertEqual(self.away.draws, 1)
        self.assertEqual(self.home.rating_points, 1)
        self.assertEqual(self.away.rating_points, 1)

    def test_outsider_cannot_report_result(self):
        match = schedule_match(home_team=self.home, away_team=self.away, organizer=self.captain)

        with self.assertRaises(NotMatchParticipant):
            report_match_result(match_id=match.id, reporter=self.outsider, home_score=1, away_score=0)

    def test_result_cannot_be_reported_twice(self):
        match = schedule_match(home_team=self.home, away_team=self.away, organizer=self.captain)
        report_match_result(match_id=match.id, reporter=self.captain, home_score=1, away_score=0)

        with self.assertRaises(MatchAlreadyReported):
            report_match_result(match_id=match.id, reporter=self.captain, home_score=2, away_score=2)


class TeamViewsTests(TeamFixturesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def test_create_team_via_api(self):
        self.client.force_authenticate(user=self.captain)

        response = self.client.post("/api/teams/", {"name": "Барс", "district": "Свердловский"})

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Барс")

    def test_join_via_api_then_appears_in_members(self):
        team = create_team(name="Барс", creator=self.captain)
        self.client.force_authenticate(user=self.player)

        join_response = self.client.post(f"/api/teams/{team.id}/join/")
        self.assertEqual(join_response.status_code, 200)

        members_response = self.client.get(f"/api/teams/{team.id}/members/")
        phones = [m["user_phone"] for m in members_response.data]
        self.assertIn(self.player.phone, phones)

    def test_full_match_flow_via_api(self):
        home = create_team(name="Барс", creator=self.captain)
        away = create_team(name="Тигр", creator=self.player)

        self.client.force_authenticate(user=self.captain)
        create_response = self.client.post(
            "/api/teams/matches/", {"home_team": home.id, "away_team": away.id}
        )
        self.assertEqual(create_response.status_code, 201)
        match_id = create_response.data["id"]

        report_response = self.client.post(
            f"/api/teams/matches/{match_id}/report-result/", {"home_score": 4, "away_score": 2}
        )
        self.assertEqual(report_response.status_code, 200)
        self.assertEqual(report_response.data["status"], MatchStatus.PLAYED)
