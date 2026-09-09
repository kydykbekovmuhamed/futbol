// Регрессионный тест для apps/frontend/static/frontend/app.js — без
// браузера и без внешних зависимостей (нет ни Jest, ни jsdom в проекте,
// заводить их ради одного файла ванильного JS не стали). Запуск:
//
//   node apps/frontend/tests/run.js
//
// Читает РЕАЛЬНЫЙ app.js заново при каждом запуске (не копию) — вставляет
// сценарии прямо внутрь его IIFE (после ---- boot маркера вырезается
// оригинальный boot и подставляется наш), так что тест видит любые более
// поздние правки файла. Технику отладки, которой это найдено (краш
// "Команда" после Команда→Турниры→Команда), см. CLAUDE.md и память
// node_harness_for_browser_js_debugging.
"use strict";

var fs = require("fs");
var path = require("path");

var domStub = require("./dom_stub");
var fixtures = require("./fixtures");

var APP_JS_PATH = path.join(__dirname, "..", "static", "frontend", "app.js");
var GENERATED_PATH = path.join(__dirname, "_generated_harness.js");

var appSource = fs.readFileSync(APP_JS_PATH, "utf8");
var bootMarkerIndex = appSource.indexOf("// ---- boot");
if (bootMarkerIndex === -1) {
  console.error("Не нашёл '// ---- boot' в app.js — маркер переименовали? Поправьте run.js.");
  process.exit(2);
}
var appBody = appSource.slice(0, bootMarkerIndex);

var driver = fs.readFileSync(path.join(__dirname, "driver_body.js"), "utf8");

fs.writeFileSync(GENERATED_PATH, appBody + "\n" + driver, "utf8");

domStub.installDomStub();

var FIXTURES_BY_PATH = {
  "/teams/?mine=true": function () { return [fixtures.TEAM]; },
  "/teams/1/members/": function () { return fixtures.TEAM_MEMBERS; },
  "/teams/matches/?team=1": function () { return fixtures.TEAM_MATCHES; },
  "/tournaments/": function () { return fixtures.TOURNAMENTS; },
  "/tournaments/2/": function () { return fixtures.TOURNAMENT_DETAIL; },
  "/tournaments/2/registrations/": function () { return fixtures.TOURNAMENT_REGISTRATIONS; },
  "/tournaments/2/standings/": function () { return fixtures.TOURNAMENT_STANDINGS; },
  "/tournaments/2/matches/": function () { return fixtures.TOURNAMENT_MATCHES; },
  "/bookings/": function () { return fixtures.BOOKINGS; },
  "/community/feed/": function () { return fixtures.FEED_EVENTS; },
  "/community/challenges/": function () { return fixtures.CHALLENGES; },
  "/community/news/": function () { return fixtures.NEWS; }
};

global.fetch = function (url) {
  var pathOnly = url.replace("/api", "");

  // Реалистичная симуляция 402 "нет активной подписки" — то, что реально
  // отдаёт бэкенд по умолчанию (см. apps.community.services.get_extended_stats).
  // Без этого фейковый fetch вернул бы [] (ok:true) на неизвестный путь, и
  // renderTeamSubscriptionSection() упал бы на undefined.monthly_breakdown.
  if (/\/community\/teams\/\d+\/extended-stats\/$/.test(pathOnly)) {
    return Promise.resolve({
      ok: false,
      status: 402,
      text: function () { return Promise.resolve(JSON.stringify({ detail: "Расширенная статистика доступна только по активной подписке команды." })); }
    });
  }

  var fixture = FIXTURES_BY_PATH[pathOnly];
  var data = fixture ? fixture() : (pathOnly.indexOf("/venues/available/") === 0 || pathOnly.indexOf("/venues/available/") !== -1 ? fixtures.VENUES : []);
  return Promise.resolve({
    ok: true,
    status: 200,
    text: function () { return Promise.resolve(JSON.stringify(data)); }
  });
};

process.on("unhandledRejection", function (reason) {
  console.error("UNHANDLED REJECTION: " + (reason && reason.stack ? reason.stack : reason));
  process.exitCode = 1;
});

require(GENERATED_PATH);
