// Реалистичные формы ответов API (проверены вживую через curl/requests в
// ходе разработки, см. CLAUDE.md) — держим их тут, а не выдумываем на месте,
// чтобы тесты падали на реальных несовпадениях полей, а не пропускали их.
"use strict";

var TEAM = {
  id: 1, name: "Барс FC", district: "Октябрьский р-н", description: "",
  rating_points: 12, wins: 4, draws: 0, losses: 0, games_played: 4,
  members_count: 2, rank_title: "Любитель", points_to_next_rank: 18,
  created_at: "2026-09-09T18:15:21.046409+06:00"
};

var TEAM_MEMBERS = [
  { id: 3, user: 8, user_phone: "+996700000001", role: "member", joined_at: "2026-09-09T18:32:09.623842+06:00" },
  { id: 1, user: 9, user_phone: "+996990820720", role: "captain", joined_at: "2026-09-09T18:15:21.051666+06:00" }
];

var TEAM_MATCHES = [
  { id: 4, booking: null, home_team: 1, home_team_name: "Барс FC", away_team: 2, away_team_name: "Соколы", status: "played", status_display: "Сыгран", home_score: 2, away_score: 0, played_at: "2026-09-09T18:37:27.175023+06:00", created_at: "2026-09-09T18:37:27.163146+06:00" },
  { id: 1, booking: null, home_team: 1, home_team_name: "Барс FC", away_team: 2, away_team_name: "Соколы", status: "played", status_display: "Сыгран", home_score: 4, away_score: 2, played_at: "2026-09-09T18:15:45.733970+06:00", created_at: "2026-09-09T18:15:45.717959+06:00" }
];

var TOURNAMENTS = [
  { id: 1, name: "Кубок офиса", description: "", sponsor_name: "Строй-Сервис", organizer: 9, entry_fee: "1000.00", min_teams: 2, max_teams: 8, registration_deadline: "2026-09-12T21:51:04.160370+06:00", status: "registration_open", status_display: "Регистрация открыта", registered_teams_count: 0, created_at: "2026-09-09T21:51:04.497996+06:00" },
  { id: 2, name: "Летний кубок дворов", description: "", sponsor_name: "", organizer: 9, entry_fee: "1500.00", min_teams: 4, max_teams: 16, registration_deadline: "2026-09-14T21:51:46.0+06:00", status: "registration_open", status_display: "Регистрация открыта", registered_teams_count: 1, created_at: "2026-09-09T21:51:46.0+06:00" }
];

var TOURNAMENT_DETAIL = TOURNAMENTS[1];

var TOURNAMENT_REGISTRATIONS = [
  { id: 1, tournament: 2, team: 1, team_name: "Барс FC", status: "registered", status_display: "Зарегистрирована (взнос зарезервирован)", created_at: "2026-09-09T21:51:46.5+06:00" }
];

var TOURNAMENT_STANDINGS = [
  { registration_id: 1, team_id: 1, team_name: "Барс FC", played: 0, wins: 0, draws: 0, losses: 0, points: 0 }
];

var TOURNAMENT_MATCHES = [];

var BOOKINGS = [
  { id: 29, venue: 10, venue_name: "Арена Ак-Ордо", start_time: "2026-09-11T20:55:38.146592+06:00", end_time: "2026-09-11T21:55:38.146592+06:00", status: "confirmed", status_display: "Подтверждена", price: "800.00", deposit_amount: "240.00", confirmation_deadline: "2026-09-11T16:55:38.0+06:00", extended_from: null, created_at: "2026-09-09T16:55:38.0+06:00" },
  { id: 30, venue: 11, venue_name: "Спорт-Сити Восток-5", start_time: "2026-09-12T18:00:00+06:00", end_time: "2026-09-12T19:00:00+06:00", status: "pending_confirmation", status_display: "Ждёт подтверждения администратора", price: "650.00", deposit_amount: "195.00", confirmation_deadline: "2026-09-12T17:10:00+06:00", extended_from: null, created_at: "2026-09-12T17:00:00+06:00" }
];

var VENUES = [
  { id: 10, name: "Арена Ак-Ордо", district: "Октябрьский р-н", address: "ул. Молодая Гвардия, 15", latitude: null, longitude: null, surface_type: "turf", surface_type_display: "Искусственный газон", field_size: "7x7", price_per_hour: "800.00", description: "" }
];

var FEED_EVENTS = [
  { id: 1, event_type: "rank_up", event_type_display: "Новое звание команды", title: "Новое звание: Любитель", body: "«Барс FC» теперь «Любитель». До следующего звания: 18 очков.", is_read: false, created_at: "2026-09-09T18:37:27.2+06:00" },
  { id: 2, event_type: "rating_changed", event_type_display: "Изменение рейтинга команды", title: "Рейтинг команды изменился", body: "«Барс FC»: +3 очков, теперь 12.", is_read: false, created_at: "2026-09-09T18:37:27.1+06:00" }
];

var CHALLENGES = [
  { id: 1, challenger_team: 2, challenger_team_name: "Соколы", opponent_team: 1, opponent_team_name: "Барс FC", message: "Реванш?", proposed_time: null, status: "pending", status_display: "Ожидает ответа", created_at: "2026-09-09T18:15:45.8+06:00", responded_at: null }
];

var NEWS = [
  { id: 1, title: "Открылась новая площадка с подогревом в Джале", source_name: "Футбол KG", source_url: "https://example.com/news/1", published_at: "2026-09-09T10:00:00+06:00" }
];

var EXTENDED_STATS = {
  team_id: 1, team_name: "Барс FC", rank_title: "Любитель", points_to_next_rank: 18,
  games_played: 4, win_rate_percent: 100.0, longest_win_streak: 4,
  monthly_breakdown: [{ month: "2026-09", wins: 4, draws: 0, losses: 0 }]
};

module.exports = {
  TEAM: TEAM, TEAM_MEMBERS: TEAM_MEMBERS, TEAM_MATCHES: TEAM_MATCHES,
  TOURNAMENTS: TOURNAMENTS, TOURNAMENT_DETAIL: TOURNAMENT_DETAIL,
  TOURNAMENT_REGISTRATIONS: TOURNAMENT_REGISTRATIONS, TOURNAMENT_STANDINGS: TOURNAMENT_STANDINGS,
  TOURNAMENT_MATCHES: TOURNAMENT_MATCHES,
  BOOKINGS: BOOKINGS, VENUES: VENUES,
  FEED_EVENTS: FEED_EVENTS, CHALLENGES: CHALLENGES, NEWS: NEWS,
  EXTENDED_STATS: EXTENDED_STATS
};
