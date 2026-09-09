
  // ---- regression scenarios (injected into the real app.js IIFE) ----
  try {
    global.confirm = function () { return true; };
  } catch (e) {
    Object.defineProperty(global, "confirm", { value: function () { return true; }, configurable: true, writable: true });
  }

  function sleep(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }

  var results = [];
  function record(name, ok, err) {
    results.push({ name: name, ok: ok, err: err });
    var mark = ok ? "PASS" : "FAIL";
    console.log("[" + mark + "] " + name + (err ? (" — " + (err && err.stack ? err.stack.split("\n").slice(0, 3).join(" | ") : err)) : ""));
  }

  async function run(name, fn) {
    try {
      await fn();
      record(name, true);
    } catch (e) {
      record(name, false, e);
    }
  }

  async function main() {
    await run("boot: login-phone renders", async function () {
      state.token = null;
      state.view = "login-phone";
      render();
    });

    await run("login-code renders, including error state", async function () {
      state.view = "login-code";
      state.otpCode = "1234";
      state.authError = "";
      render();
      state.authError = "Неверный код.";
      render();
    });

    state.token = "test-token"; // "залогинились" для всех дальнейших сценариев

    await run("main: initial load + venues fetch", async function () {
      state.view = "main";
      render();
      loadVenues();
      await sleep(20);
    });

    await run("main: time sheet overlay open/close", async function () {
      state.timeSheetOpen = true;
      render();
      state.timeSheetOpen = false;
      render();
    });

    await run("my-bookings: populated list, open a pending one -> confirm screen", async function () {
      state.view = "my-bookings";
      render();
      loadMyBookings();
      await sleep(20);
      var pending = state.myBookingsList.find(function (b) { return b.status === "pending_confirmation"; });
      if (!pending) throw new Error("fixture has no pending_confirmation booking to test with");
      openBookingFromList(pending);
      await sleep(10);
      if (state.view !== "confirm") throw new Error("expected view=confirm, got " + state.view);
      stopBookingWatch();
    });

    await run("my-bookings: empty list renders", async function () {
      var saved = state.myBookingsList;
      state.myBookingsList = [];
      state.view = "my-bookings";
      state.myBookingsLoading = false;
      render();
      state.myBookingsList = saved;
    });

    state.view = "main";
    render();

    await run("team: first visit (has team + members + matches)", async function () {
      goToNav("team");
      await sleep(20);
      if (state.teamLoading) throw new Error("stuck loading on first team visit");
    });

    await run("team subscription: no-subscription CTA (real 402 path) renders", async function () {
      goToNav("team");
      await sleep(20);
      if (!state.teamSubscriptionChecked) throw new Error("subscription check never completed");
      if (state.teamExtendedStats) throw new Error("expected no active subscription (fetch stub simulates 402)");
    });

    await run("team subscription: active-subscription stats section renders, toggle expand", async function () {
      state.teamExtendedStats = {
        team_id: 1, team_name: "Барс FC", rank_title: "Любитель", points_to_next_rank: 18,
        games_played: 4, win_rate_percent: 100.0, longest_win_streak: 4,
        monthly_breakdown: [{ month: "2026-09", wins: 4, draws: 0, losses: 0 }]
      };
      state.teamSubscriptionChecked = true;
      render();
      state.teamStatsExpanded = true;
      render();
      state.teamStatsExpanded = false;
      state.teamExtendedStats = null; // возвращаем как было для следующих сценариев
      render();
    });

    await run("REPRO: team -> tournaments -> team (bug found live, see CLAUDE.md)", async function () {
      goToNav("cup");
      await sleep(20);
      goToNav("team");
      await sleep(20);
      if (state.teamLoading) throw new Error("stuck loading after team -> tournaments -> team");
    });

    await run("team -> feed -> team", async function () {
      goToNav("feed");
      await sleep(20);
      goToNav("team");
      await sleep(20);
      if (state.teamLoading) throw new Error("stuck loading after team -> feed -> team");
    });

    await run("team -> my-bookings -> team", async function () {
      state.view = "my-bookings";
      render();
      loadMyBookings();
      await sleep(20);
      goToNav("team");
      await sleep(20);
      if (state.teamLoading) throw new Error("stuck loading after team -> my-bookings -> team");
    });

    await run("team: invite-info and challenge-picker overlays", async function () {
      goToNav("team");
      await sleep(20);
      state.inviteInfoOpen = true;
      render();
      state.inviteInfoOpen = false;
      render();
      state.challengePickerOpen = true;
      state.challengeCandidatesLoading = false;
      state.challengeCandidates = [{ id: 2, name: "Соколы", district: "Ленинский р-н", rating_points: 3 }];
      render();
      closeChallengePicker();
    });

    await run("team: no-team create/join screen renders", async function () {
      var savedTeam = state.myTeam;
      state.myTeam = null;
      state.teamLoading = false;
      state.teamSearchResults = [{ id: 5, name: "Тестовая FC", district: "", members_count: 3 }];
      render();
      state.teamSearchResults = [];
      render();
      state.myTeam = savedTeam;
    });

    await run("tournaments: list -> detail -> back -> detail again", async function () {
      goToNav("cup");
      await sleep(20);
      openTournamentDetail(2);
      await sleep(20);
      if (state.tournamentDetailLoading) throw new Error("stuck loading tournament detail");
      state.view = "tournaments";
      render();
      openTournamentDetail(2);
      await sleep(20);
    });

    await run("tournaments: empty list renders", async function () {
      var saved = state.tournamentsList;
      state.tournamentsList = [];
      state.view = "tournaments";
      state.tournamentsLoading = false;
      render();
      state.tournamentsList = saved;
    });

    await run("tournaments: create-form overlay open/close", async function () {
      state.tournamentCreateOpen = true;
      render();
      state.tournamentCreateOpen = false;
      render();
    });

    await run("feed: populated + empty render", async function () {
      state.view = "feed";
      render();
      loadFeed();
      await sleep(20);
      var saved = state.feedItems;
      state.feedItems = [];
      state.feedLoading = false;
      render();
      state.feedItems = saved;
    });

    await run("extension offer overlay atop main", async function () {
      state.view = "main";
      render();
      state.extensionOffer = {
        id: 99, venue_name: "Арена Ак-Ордо", price: "800.00",
        confirmation_deadline: new Date(Date.now() + 5 * 60000).toISOString(),
        created_at: new Date().toISOString()
      };
      render();
      state.extensionOffer = null;
      render();
    });

    await run("logout returns to login-phone cleanly", async function () {
      logout();
      if (state.view !== "login-phone") throw new Error("logout left view=" + state.view);
      if (state.token !== null) throw new Error("logout did not clear token");
    });

    var failed = results.filter(function (r) { return !r.ok; });
    console.log("\n" + (results.length - failed.length) + "/" + results.length + " passed.");
    if (failed.length > 0) process.exitCode = 1;
  }

  main();
})();
