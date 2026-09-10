(function () {
  "use strict";

  var STORAGE_KEY = "futbol_token";
  var API_BASE = "/api";

  var FIREBASE_CONFIG = {
    apiKey: "AIzaSyAJR17Q-JBedIbtY533ElecSM7MDvy1Og0",
    authDomain: "futbol-app-4f955.firebaseapp.com",
    projectId: "futbol-app-4f955",
    storageBucket: "futbol-app-4f955.firebasestorage.app",
    messagingSenderId: "863563525836",
    appId: "1:863563525836:web:2b98399d3d55f622b3dc69"
  };
  var FIREBASE_VAPID_KEY = "BFCqo0uj_NZN0N0fg_-GnGykLe7G0SKhXkJ_vIyd2SZ1g6Xa02uK4YMMUVF7_gNiOqeoJLwbay5pUnghZSfUBr4";
  var BISHKEK_OFFSET_HOURS = 6;
  var HOURS = []; // 8..23
  for (var h = 8; h <= 23; h++) HOURS.push(h);

  // Бишкек делится на 4 района — фиксированный список вместо свободного текста.
  var DISTRICTS = ["Октябрьский р-н", "Ленинский р-н", "Свердловский р-н", "Первомайский р-н"];

  var ICON = {
    ball: '<svg width="26" height="26" viewBox="0 0 24 24" class="icon"><circle cx="12" cy="12" r="9"/><path d="M12 7l3.2 2.1-1.1 3.6h-4.2l-1.1-3.6z"/><path d="M12 7V3.6M15.2 9.1l3.3-1.2M8.8 9.1l-3.3-1.2M9.9 12.7L7 16.5M14.1 12.7L17 16.5M12 15.7v3.6"/></svg>',
    // Своя эмблема — пятиугольник из 5 клиньев вокруг меньшего центрального
    // пятиугольника (лайм + тёмные швы), гладкий выпуклый силуэт. Намеренно
    // НЕ повторяет форму лого аниме "Blue Lock" (у того контур со впадинами,
    // звездой) — только общий мотив "панель мяча", это разные фигуры.
    emblem: '<svg width="26" height="27" viewBox="0 0 100 104"><polygon points="50.81,7.38 92.19,37.44 66.04,45.15 51.56,34.62" fill="var(--lime)"/><polygon points="92.69,38.98 76.89,87.62 61.47,65.14 67.01,48.11" fill="var(--lime)"/><polygon points="75.57,88.58 24.43,88.58 41.05,66.97 58.95,66.97" fill="var(--lime)"/><polygon points="23.11,87.62 7.31,38.98 32.99,48.11 38.53,65.14" fill="var(--lime)"/><polygon points="7.81,37.44 49.19,7.38 48.44,34.62 33.96,45.15" fill="var(--lime)"/><polygon points="50.00,36.20 65.03,47.12 59.29,64.78 40.71,64.78 34.97,47.12" fill="var(--bg)"/></svg>',
    bell: '<svg width="19" height="19" viewBox="0 0 24 24" class="icon"><path d="M6 8a6 6 0 0 1 12 0c0 5 2 6 2 6H4s2-1 2-6z"/><path d="M10 20a2 2 0 0 0 4 0"/></svg>',
    search: '<svg width="21" height="21" viewBox="0 0 24 24" class="icon"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/></svg>',
    team: '<svg width="21" height="21" viewBox="0 0 24 24" class="icon"><circle cx="9" cy="8" r="3"/><path d="M3 20c0-3.5 2.7-6 6-6s6 2.5 6 6"/><circle cx="17" cy="9" r="2.5"/><path d="M15.5 14c2.5.3 4.5 2.3 4.5 6"/></svg>',
    cup: '<svg width="21" height="21" viewBox="0 0 24 24" class="icon"><path d="M7 4h10v4a5 5 0 0 1-10 0V4z"/><path d="M7 5H4v2a3 3 0 0 0 3 3"/><path d="M17 5h3v2a3 3 0 0 1-3 3"/><path d="M10 14v3h4v-3"/><path d="M8 20h8"/></svg>',
    feed: '<svg width="21" height="21" viewBox="0 0 24 24" class="icon"><path d="M4 11l8-7 8 7"/><path d="M6 10v9h12v-9"/></svg>',
    close: '<svg width="15" height="15" viewBox="0 0 24 24" class="icon"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    chevron: '<svg width="14" height="14" viewBox="0 0 24 24" style="stroke:var(--lime-ink);fill:none;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round;"><path d="M9 6l6 6-6 6"/></svg>',
    chevronDown: '<svg width="17" height="17" viewBox="0 0 24 24" class="icon" style="color:var(--muted);"><path d="M6 9l6 6 6-6"/></svg>',
    envelope: '<svg width="20" height="20" viewBox="0 0 24 24" class="icon" style="color:var(--lime);"><rect x="3" y="5" width="18" height="14" rx="2"/><path d="M3 7l9 6 9-6"/></svg>',
    phone: '<svg width="20" height="20" viewBox="0 0 24 24" class="icon" style="color:var(--orange);"><path d="M6 3h4l1 5-2.5 1.5a12 12 0 0 0 6 6L16 13l5 1v4a2 2 0 0 1-2 2A16 16 0 0 1 4 5a2 2 0 0 1 2-2z"/></svg>',
    lock: '<svg width="19" height="19" viewBox="0 0 24 24" class="icon" style="color:var(--lime);"><rect x="5" y="11" width="14" height="9" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/></svg>',
    check: '<svg width="40" height="40" viewBox="0 0 24 24" style="stroke:var(--lime);fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;"><path d="M5 13l4 4L19 7"/></svg>',
    cross: '<svg width="40" height="40" viewBox="0 0 24 24" style="stroke:var(--red, oklch(0.62 0.21 25));fill:none;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round;"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    chevronLeft: '<svg width="16" height="16" viewBox="0 0 24 24" class="icon"><path d="M15 6l-6 6 6 6"/></svg>',
    logoutDoor: '<svg width="15" height="15" viewBox="0 0 24 24" class="icon"><circle cx="12" cy="12" r="3"/><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1"/></svg>',
    cup2: '<svg width="34" height="34" viewBox="0 0 24 24" style="stroke:var(--lime);fill:none;stroke-width:1.6;stroke-linecap:round;stroke-linejoin:round;"><path d="M7 4h10v4a5 5 0 0 1-10 0V4z"/><path d="M7 5H4v2a3 3 0 0 0 3 3"/><path d="M17 5h3v2a3 3 0 0 1-3 3"/><path d="M10 14v3h4v-3"/><path d="M8 20h8"/></svg>',
    swords: '<svg width="17" height="17" viewBox="0 0 24 24" style="stroke:oklch(0.15 0.02 40);fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round;"><path d="M13 2L3 14h7l-1 8 11-13h-7l1-7z"/></svg>',
    swordsOrange: '<svg width="26" height="26" viewBox="0 0 24 24" style="stroke:var(--orange);fill:none;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;flex:0 0 auto;"><path d="M13 2L3 14h7l-1 8 11-13h-7l1-7z"/></svg>',
    trendUp: '<svg width="24" height="24" viewBox="0 0 24 24" style="stroke:var(--lime);fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round;flex:0 0 auto;"><path d="M4 19V10M11 19V5M18 19v-7"/></svg>',
    person: '<svg width="17" height="17" viewBox="0 0 24 24" class="icon" style="color:var(--muted);"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8"/></svg>',
    list: '<svg width="17" height="17" viewBox="0 0 24 24" class="icon"><path d="M8 6h13M8 12h13M8 18h13"/><path d="M3 6h.01M3 12h.01M3 18h.01"/></svg>',
    slidersFilter: '<svg width="15" height="15" viewBox="0 0 24 24" class="icon"><line x1="4" y1="6" x2="20" y2="6"/><circle cx="9" cy="6" r="2"/><line x1="4" y1="18" x2="20" y2="18"/><circle cx="15" cy="18" r="2"/></svg>',
    plus: '<svg width="17" height="17" viewBox="0 0 24 24" class="icon"><path d="M12 5v14M5 12h14"/></svg>'
  };

  var SURFACE_META = {
    hall: { label: "ЗАЛ", cls: "sash-hall" },
    turf: { label: "ГАЗОН", cls: "sash-turf" },
    stadium: { label: "СТАДИОН", cls: "sash-stadium" }
  };

  // ---- state ---------------------------------------------------------

  var state = {
    token: localStorage.getItem(STORAGE_KEY) || null,
    view: "login-phone",
    phone: "",
    otpCode: "",
    authError: "",
    authBusy: false,
    dateOffset: 0,
    customDateParts: null, // {y,m,day} — задаётся ручным вводом даты в шторке, dateOffset становится -1
    hour: defaultHour(0),
    timeSheetOpen: false,
    filters: { district: "", surface_type: "", field_size: "", price_max: "" },
    venues: [],
    venuesLoading: false,
    venuesError: "",
    bookingBusyVenueId: null,
    booking: null,
    resolution: null, // "confirmed" | "unavailable"
    pollHandle: null,
    tickHandle: null,
    extensionOffer: null, // текущая бронь-продление в статусе extension_pending, если есть
    extensionBusy: false,
    extensionWatchHandle: null,

    // ---- team profile (TeamProfile.dc.html) ----
    teamLoading: false,
    myTeam: null, // объект команды пользователя, или null (ещё не загружено/нет команды)
    teamMembers: [],
    teamMatches: [], // только status==="played"
    teamCreateBusy: false,
    teamCreateError: "",
    teamSearchQuery: "",
    teamSearchResults: [],
    teamSearchLoading: false,
    teamJoinBusyId: null,
    challengePickerOpen: false,
    inviteInfoOpen: false,
    challengeCandidates: [],
    challengeCandidatesLoading: false,
    challengeBusy: false,

    // ---- activity feed (Feed.dc.html) ----
    feedLoading: false,
    feedItems: [], // объединённые ActivityEvent + вызовы + результаты матчей + новости

    // ---- my bookings (не из макета — очевидный пробел: забронировать можно, посмотреть историю негде) ----
    myBookingsLoading: false,
    myBookingsList: [],

    // ---- tournaments (не из макета — бэкенд был полностью готов, экрана не было вообще) ----
    tournamentsLoading: false,
    tournamentsList: [],
    tournamentCreateOpen: false,
    tournamentCreateBusy: false,
    tournamentCreateError: "",
    tournamentDetailLoading: false,
    tournamentDetail: null,
    tournamentRegistrations: [],
    tournamentStandings: [],
    tournamentMatches: [],
    tournamentRegisterBusy: false,

    // ---- team subscription / extended stats (не из макета — бэкенд был готов, экрана не было) ----
    teamSubscriptionChecked: false,
    teamExtendedStats: null, // не null => подписка активна (сам факт успешного ответа extended-stats/)
    teamStatsExpanded: false,
    teamSubscribeBusy: false
  };
  state.view = state.token ? "main" : "login-phone";

  // ---- time helpers (Asia/Bishkek, UTC+6, no DST) ---------------------

  function bishkekNow() {
    return new Date(Date.now() + BISHKEK_OFFSET_HOURS * 3600 * 1000);
  }

  function bishkekDateParts(offsetDays) {
    var d = bishkekNow();
    d.setUTCDate(d.getUTCDate() + offsetDays);
    return { y: d.getUTCFullYear(), m: d.getUTCMonth(), day: d.getUTCDate() };
  }

  function isoFromBishkek(parts, hour) {
    return new Date(Date.UTC(parts.y, parts.m, parts.day, hour - BISHKEK_OFFSET_HOURS, 0, 0)).toISOString();
  }

  function sameDateParts(a, b) {
    return a.y === b.y && a.m === b.m && a.day === b.day;
  }

  function defaultHourForParts(parts) {
    if (!sameDateParts(parts, bishkekDateParts(0))) return HOURS[0];
    var currentHour = bishkekNow().getUTCHours();
    for (var i = 0; i < HOURS.length; i++) {
      if (HOURS[i] > currentHour) return HOURS[i];
    }
    return HOURS[HOURS.length - 1];
  }

  function defaultHour(offsetDays) {
    return defaultHourForParts(bishkekDateParts(offsetDays));
  }

  function dateLabel(offsetDays) {
    if (offsetDays === 0) return "Сегодня";
    if (offsetDays === 1) return "Завтра";
    return dateLabelForParts(bishkekDateParts(offsetDays));
  }

  function dateLabelForParts(p) {
    var d = new Date(Date.UTC(p.y, p.m, p.day, 12));
    var s = new Intl.DateTimeFormat("ru-RU", { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" }).format(d);
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  // Текущий выбор даты — либо один из 4 быстрых вариантов (dateOffset 0..3),
  // либо произвольная дата из <input type="date"> в шторке (dateOffset===-1).
  function selectedDateParts() {
    if (state.dateOffset === -1 && state.customDateParts) return state.customDateParts;
    return bishkekDateParts(state.dateOffset);
  }

  function selectedDateLabel() {
    if (state.dateOffset === -1 && state.customDateParts) return dateLabelForParts(state.customDateParts);
    return dateLabel(state.dateOffset);
  }

  function datePartsToInputValue(p) {
    var mm = String(p.m + 1).padStart(2, "0");
    var dd = String(p.day).padStart(2, "0");
    return p.y + "-" + mm + "-" + dd;
  }

  function inputValueToDateParts(value) {
    var parts = value.split("-");
    return { y: parseInt(parts[0], 10), m: parseInt(parts[1], 10) - 1, day: parseInt(parts[2], 10) };
  }

  function formatTimeBishkek(isoString) {
    return new Intl.DateTimeFormat("ru-RU", { hour: "2-digit", minute: "2-digit", timeZone: "Asia/Bishkek" }).format(new Date(isoString));
  }

  function formatDateBishkek(isoString) {
    var s = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "long", timeZone: "Asia/Bishkek" }).format(new Date(isoString));
    return s;
  }

  function money(v) {
    return Math.round(parseFloat(v)).toLocaleString("ru-RU");
  }

  function pluralize(n, one, few, many) {
    var mod10 = n % 10, mod100 = n % 100;
    if (mod10 === 1 && mod100 !== 11) return one;
    if (mod10 >= 2 && mod10 <= 4 && (mod100 < 10 || mod100 >= 20)) return few;
    return many;
  }

  // ---- API --------------------------------------------------------------

  function apiFetch(path, opts) {
    opts = opts || {};
    var headers = { "Content-Type": "application/json" };
    if (opts.auth !== false && state.token) headers["Authorization"] = "Token " + state.token;
    return fetch(API_BASE + path, {
      method: opts.method || "GET",
      headers: headers,
      credentials: "omit", // не отправлять сессионную cookie Django admin — иначе DRF SessionAuthentication требует CSRF-токен, которого у нас нет (авторизация только по Token)
      body: opts.body ? JSON.stringify(opts.body) : undefined
    }).then(function (res) {
      return res.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        if (!res.ok) {
          var message = extractErrorMessage(data) || ("Ошибка сервера (" + res.status + ")");
          var err = new Error(message);
          err.status = res.status;
          err.data = data;
          throw err;
        }
        return data;
      });
    });
  }

  // ---- push-уведомления (Firebase Cloud Messaging) ----------------------
  // typeof firebase === "undefined" делает всю функцию безопасным no-op
  // под Node-тест-харнессом (apps/frontend/tests/), где SDK не грузится —
  // без этой проверки тесты падали бы на ReferenceError. По той же причине
  // проверяем каждый Web API отдельно (Notification, navigator.serviceWorker)
  // вместо того чтобы полагаться на их наличие.
  function initPushNotifications() {
    if (typeof firebase === "undefined") return;
    if (typeof navigator === "undefined" || !("serviceWorker" in navigator)) return;
    if (typeof Notification === "undefined" || Notification.permission === "denied") return;

    navigator.serviceWorker.register("/static/frontend/firebase-messaging-sw.js")
      .then(function (registration) {
        var app = firebase.apps && firebase.apps.length ? firebase.apps[0] : firebase.initializeApp(FIREBASE_CONFIG);
        var messaging = firebase.messaging(app);

        function registerToken() {
          messaging.getToken({ vapidKey: FIREBASE_VAPID_KEY, serviceWorkerRegistration: registration })
            .then(function (token) {
              if (!token) return;
              return apiFetch("/notifications/device-tokens/", { method: "POST", body: { token: token, platform: "web" } });
            })
            .catch(function (err) { console.error("Push token error:", err); });
        }

        if (Notification.permission === "granted") {
          registerToken();
        } else if (Notification.permission === "default") {
          Notification.requestPermission().then(function (permission) {
            if (permission === "granted") registerToken();
          });
        }

        // Пуш, пришедший, пока вкладка открыта и активна — фоновый обработчик
        // в firebase-messaging-sw.js покрывает случай закрытой/неактивной вкладки.
        messaging.onMessage(function (payload) {
          var title = (payload.notification && payload.notification.title) || "Футбол";
          var body = (payload.notification && payload.notification.body) || "";
          showToast(title + (body ? ": " + body : ""));
        });
      })
      .catch(function (err) { console.error("Push service worker registration failed:", err); });
  }

  function extractErrorMessage(data) {
    if (!data) return null;
    if (typeof data.detail === "string") return data.detail;
    for (var key in data) {
      if (Object.prototype.hasOwnProperty.call(data, key)) {
        var v = data[key];
        if (Array.isArray(v) && v.length) return v[0];
        if (typeof v === "string") return v;
      }
    }
    return null;
  }

  // ---- render scaffolding -------------------------------------------

  var root = document.getElementById("app");
  var toastTimer = null;

  function render() {
    var html = '<div class="app-shell">';
    switch (state.view) {
      case "login-phone": html += renderLoginPhone(); break;
      case "login-code": html += renderLoginCode(); break;
      case "main": html += renderMain(); break;
      case "confirm": html += renderConfirm(); break;
      case "result": html += renderResult(); break;
      case "team": html += renderTeam(); break;
      case "feed": html += renderFeed(); break;
      case "my-bookings": html += renderMyBookings(); break;
      case "tournaments": html += renderTournaments(); break;
      case "tournament-detail": html += renderTournamentDetail(); break;
    }
    html += "</div>";
    if (state.challengePickerOpen) html += renderChallengePicker();
    if (state.inviteInfoOpen) html += renderInviteInfo();
    if (state.tournamentCreateOpen) html += renderTournamentCreateForm();
    if (state.extensionOffer) html += renderExtensionOffer();
    root.innerHTML = html;
    bind();
  }

  function showToast(message) {
    var el = document.createElement("div");
    el.className = "toast";
    el.textContent = message;
    document.body.appendChild(el);
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.remove(); }, 2600);
  }

  // ---- views: auth ----------------------------------------------------

  function renderLoginPhone() {
    return (
      '<div class="center-screen">' +
        '<div>' + ICON.emblem + "</div>" +
        '<div class="disp" style="font-size:30px;">ФУТБОЛ</div>' +
        '<div style="color:var(--muted);font-size:14px;max-width:280px;">Введите номер телефона — пришлём код подтверждения.</div>' +
        '<div style="width:100%;max-width:280px;">' +
          '<div class="field-label">Телефон</div>' +
          '<input id="phone-input" class="text-input" type="tel" inputmode="tel" placeholder="+996700000000" value="' + escapeAttr(state.phone) + '">' +
          (state.authError ? '<div class="error-text">' + escapeHtml(state.authError) + "</div>" : "") +
        "</div>" +
        '<button id="request-otp-btn" class="btn-primary" style="max-width:280px;" ' + (state.authBusy ? "disabled" : "") + ">" +
          (state.authBusy ? '<span class="spinner"></span>' : "Получить код") +
        "</button>" +
      "</div>"
    );
  }

  function renderLoginCode() {
    return (
      '<div class="center-screen">' +
        '<div class="icon-btn" id="back-to-phone" style="align-self:flex-start;">' + ICON.close + "</div>" +
        '<div class="disp" style="font-size:26px;">КОД ИЗ SMS</div>' +
        '<div style="color:var(--muted);font-size:13px;max-width:280px;">Отправили код на ' + escapeHtml(state.phone) + '. В dev-режиме код виден в консоли сервера (лог "[MOCK SMS]").</div>' +
        '<input id="otp-code-input" class="text-input" style="max-width:200px;text-align:center;font-size:28px;letter-spacing:0.3em;font-weight:700;" type="text" inputmode="numeric" pattern="[0-9]*" maxlength="6" autocomplete="one-time-code" value="' + escapeAttr(state.otpCode) + '">' +
        (state.authError ? '<div class="error-text">' + escapeHtml(state.authError) + "</div>" : "") +
        '<button id="verify-otp-btn" class="btn-primary" style="max-width:280px;" ' + (state.authBusy ? "disabled" : "") + ">" +
          (state.authBusy ? '<span class="spinner"></span>' : "Войти") +
        "</button>" +
        '<button id="resend-otp-btn" class="btn-secondary" style="max-width:280px;">Отправить код ещё раз</button>' +
      "</div>"
    );
  }

  // ---- view: main (search) ---------------------------------------------

  function renderMain() {
    var districtOptions = '<option value="">Район</option>';
    DISTRICTS.forEach(function (d) {
      districtOptions += '<option value="' + escapeAttr(d) + '"' + (state.filters.district === d ? " selected" : "") + ">" + escapeHtml(d) + "</option>";
    });

    var filters = (
      '<div class="filters-row-wrap fade-wrap"><div class="filters-row hscroll">' +
        '<select id="filter-district" class="select-pill">' + districtOptions + "</select>" +
        '<select id="filter-surface" class="select-pill">' +
          '<option value="">Покрытие</option>' +
          '<option value="turf"' + (state.filters.surface_type === "turf" ? " selected" : "") + ">Газон</option>" +
          '<option value="hall"' + (state.filters.surface_type === "hall" ? " selected" : "") + ">Зал</option>" +
          '<option value="stadium"' + (state.filters.surface_type === "stadium" ? " selected" : "") + ">Стадион</option>" +
        "</select>" +
        '<select id="filter-size" class="select-pill">' +
          '<option value="">Размер</option>' +
          '<option value="5x5"' + (state.filters.field_size === "5x5" ? " selected" : "") + ">5×5</option>" +
          '<option value="7x7"' + (state.filters.field_size === "7x7" ? " selected" : "") + ">7×7</option>" +
          '<option value="11x11"' + (state.filters.field_size === "11x11" ? " selected" : "") + ">11×11</option>" +
        "</select>" +
        '<select id="filter-price" class="select-pill">' +
          '<option value="">Цена</option>' +
          '<option value="500"' + (state.filters.price_max === "500" ? " selected" : "") + ">до 500</option>" +
          '<option value="1000"' + (state.filters.price_max === "1000" ? " selected" : "") + ">до 1000</option>" +
          '<option value="2000"' + (state.filters.price_max === "2000" ? " selected" : "") + ">до 2000</option>" +
        "</select>" +
      "</div></div>"
    );

    var resultsHeader;
    if (state.venuesLoading) {
      resultsHeader = '<div class="results-header"><span class="spinner"></span></div>';
    } else if (state.venuesError) {
      resultsHeader = '<div class="results-header"><span style="color:var(--muted);font-size:13px;">' + escapeHtml(state.venuesError) + "</span></div>";
    } else {
      var n = state.venues.length;
      resultsHeader =
        '<div class="results-header"><div>' +
          '<span class="disp" style="font-size:26px;color:var(--lime);">' + n + "</span>" +
          '<span style="font-size:14px;color:var(--muted);"> ' + pluralize(n, "площадка свободна", "площадки свободно", "площадок свободно") +
          " на " + state.hour + ":00–" + (state.hour + 1) + ":00</span>" +
        "</div></div>";
    }

    var list = "";
    if (!state.venuesLoading && !state.venuesError) {
      if (state.venues.length === 0) {
        list = '<div style="padding:0 20px;color:var(--muted);font-size:13px;">Ничего не найдено на это время — попробуйте другой час или снимите фильтры.</div>';
      } else {
        list = '<div class="venue-list">' + state.venues.map(renderVenueCard).join("") + "</div>";
      }
    }

    return (
      '<div class="pitch-banner">' +
        '<div class="top-bar">' +
          '<div style="display:flex;align-items:center;gap:9px;">' + ICON.emblem + '<div class="disp" style="font-size:22px;line-height:1;color:var(--text);text-shadow:0 2px 8px rgba(0,0,0,0.55);">MATCH DAY</div></div>' +
          '<div style="display:flex;gap:8px;">' +
            '<div class="icon-btn" id="my-bookings-btn" title="Мои брони">' + ICON.list + "</div>" +
            '<div class="icon-btn" id="logout-btn" title="Выйти">' + ICON.bell + '<div style="position:absolute;top:8px;right:8px;width:7px;height:7px;border-radius:50%;background:var(--orange);"></div></div>' +
          "</div>" +
        "</div>" +
        '<div class="headline"><div class="disp" style="color:var(--text);text-shadow:0 2px 10px rgba(0,0,0,0.55);">НА КАКОЕ<br>ВРЕМЯ?</div><p style="text-shadow:0 1px 6px rgba(0,0,0,0.55);">Показываем все свободные площадки на выбранный час — сами не ищите, где занято.</p></div>' +
      "</div>" +
      '<div class="time-select-row" id="time-select-trigger">' +
        "<span>" + escapeHtml(selectedDateLabel()) + ", " + state.hour + ":00–" + (state.hour + 1) + ":00</span>" +
        ICON.chevronDown +
      "</div>" +
      filters +
      resultsHeader +
      list +
      renderBottomNav("search") +
      (state.timeSheetOpen ? renderTimeSheet() : "")
    );
  }

  function renderTimeSheet() {
    var dayPills = "";
    for (var i = 0; i < 4; i++) {
      dayPills += '<div class="pill' + (state.dateOffset === i ? " active" : "") + '" data-sheet-day="' + i + '">' + dateLabel(i) + "</div>";
    }

    var hourCells = "";
    HOURS.forEach(function (hh) {
      var active = state.hour === hh;
      hourCells += '<div class="hour-cell' + (active ? " active" : "") + '" data-sheet-hour="' + hh + '">' + hh + "–" + (hh + 1) + "</div>";
    });

    var minDate = datePartsToInputValue(bishkekDateParts(0));
    var currentDate = datePartsToInputValue(selectedDateParts());

    return (
      '<div class="sheet-backdrop" id="time-sheet-backdrop">' +
        '<div class="sheet-panel">' +
          '<div class="sheet-handle"></div>' +
          '<div class="sheet-header"><div class="disp" style="font-size:18px;">НА КАКОЕ ВРЕМЯ?</div><div class="icon-btn" id="sheet-close-btn">' + ICON.close + "</div></div>" +
          '<div class="sheet-section-label">День</div>' +
          '<div class="sheet-day-row hscroll">' + dayPills +
            '<input type="date" id="sheet-custom-date" class="pill date-input-pill' + (state.dateOffset === -1 ? " active" : "") + '" min="' + minDate + '" value="' + currentDate + '">' +
          "</div>" +
          '<div class="sheet-section-label">Час</div>' +
          '<div class="sheet-hour-grid">' + hourCells + "</div>" +
        "</div>" +
      "</div>"
    );
  }

  function renderVenueCard(v) {
    var meta = SURFACE_META[v.surface_type] || { label: v.surface_type, cls: "sash-hall" };
    var busy = state.bookingBusyVenueId === v.id;
    return (
      '<div class="card venue-card">' +
        '<div class="sash ' + meta.cls + '">' + meta.label + "</div>" +
        '<div class="venue-card-head">' +
          "<div>" +
            '<div class="disp" style="font-size:22px;line-height:1;">' + escapeHtml(v.name.toUpperCase()) + "</div>" +
            '<div style="font-size:12.5px;color:var(--muted);margin-top:6px;">' + escapeHtml(v.district || v.address) + "</div>" +
          "</div>" +
          '<div style="text-align:right;flex:0 0 auto;">' +
            '<div class="disp" style="font-size:24px;color:var(--lime);">' + money(v.price_per_hour) + "</div>" +
            '<div style="font-size:11px;color:var(--muted);margin-top:-4px;">сом/час</div>' +
          "</div>" +
        "</div>" +
        '<div class="venue-card-foot">' +
          '<div class="pill" style="padding:5px 10px;font-size:11.5px;">' + v.field_size.replace("x", "×") + "</div>" +
          '<button class="book-btn" data-venue-id="' + v.id + '" ' + (busy ? "disabled" : "") + ">" +
            (busy ? '<span class="spinner"></span>' : "Забронировать" + ICON.chevron) +
          "</button>" +
        "</div>" +
      "</div>"
    );
  }

  function renderBottomNav(active) {
    function item(key, icon, label) {
      return '<button class="nav-item' + (active === key ? " active" : "") + '" data-nav="' + key + '">' + icon + "<span>" + label + "</span></button>";
    }
    return (
      '<div class="bottom-nav">' +
        item("search", ICON.search, "Поиск") +
        item("team", ICON.team, "Команда") +
        item("cup", ICON.cup, "Турниры") +
        item("feed", ICON.feed, "Лента") +
      "</div>"
    );
  }

  function bindBottomNav() {
    document.querySelectorAll('[data-nav]').forEach(function (el) {
      el.addEventListener("click", function () { goToNav(el.getAttribute("data-nav")); });
    });
  }

  function goToNav(key) {
    if (key === "search") {
      state.view = "main";
      render();
      loadVenues();
      return;
    }
    if (key === "team") {
      state.view = "team";
      render();
      loadMyTeam();
      return;
    }
    if (key === "feed") {
      state.view = "feed";
      render();
      loadFeed();
      return;
    }
    if (key === "cup") {
      state.view = "tournaments";
      render();
      loadTournaments();
      return;
    }
    showToast("Этот раздел ещё в разработке");
  }

  // ---- view: confirm (waiting for venue admin) -------------------------

  function renderConfirm() {
    var b = state.booking;
    if (!b) return "";

    var deadline = new Date(b.confirmation_deadline).getTime();
    var created = new Date(b.created_at).getTime();
    var now = Date.now();
    var totalMs = Math.max(deadline - created, 1);
    var remainingMs = Math.max(deadline - now, 0);
    var fraction = Math.min(Math.max(remainingMs / totalMs, 0), 1);

    var mm = Math.floor(remainingMs / 60000);
    var ss = Math.floor((remainingMs % 60000) / 1000);
    var timeText = (mm < 10 ? "0" : "") + mm + ":" + (ss < 10 ? "0" : "") + ss;

    var circumference = 578;
    var dashoffset = Math.round(circumference * (1 - fraction));

    return (
      '<div class="confirm-header">' +
        '<div class="booking-tag">БРОНЬ #' + b.id + "</div>" +
        '<div class="icon-btn" id="confirm-close-btn">' + ICON.close + "</div>" +
      "</div>" +
      '<div class="ring-wrap">' +
        '<div class="ring">' +
          '<svg width="210" height="210" viewBox="0 0 210 210" style="transform:rotate(-90deg);">' +
            '<circle cx="105" cy="105" r="92" fill="none" stroke="var(--surface2)" stroke-width="14"/>' +
            '<circle cx="105" cy="105" r="92" fill="none" stroke="var(--lime)" stroke-width="14" stroke-linecap="round" stroke-dasharray="' + circumference + '" stroke-dashoffset="' + dashoffset + '"/>' +
          "</svg>" +
          '<div class="ring-center"><div class="disp">' + timeText + '</div><div class="ring-sub">ДО АВТООТМЕНЫ</div></div>' +
        "</div>" +
        '<div class="ring-title">ЖДЁМ ПОДТВЕРЖДЕНИЯ<br>АДМИНИСТРАТОРА</div>' +
      "</div>" +
      '<div class="section-pad">' +
        '<div class="card channel-card">' +
          '<div class="channel-icon">' + ICON.envelope + "</div>" +
          '<div class="channel-note">Push-уведомление</div>' +
          '<div class="disp" style="font-size:15px;color:var(--muted);margin-left:auto;">ИЛИ</div>' +
          '<div class="channel-icon">' + ICON.phone + "</div>" +
          '<div class="channel-note">Звонок</div>' +
        "</div>" +
        '<div style="font-size:11.5px;color:var(--muted);margin-top:8px;padding:0 4px;">Отправлены оба канала одновременно — админ подтверждает любым: тапом в приложении или ответом на звонок.</div>' +
      "</div>" +
      '<div class="section-pad">' +
        '<div class="card deposit-card">' +
          '<div class="deposit-icon">' + ICON.lock + "</div>" +
          '<div style="flex:1;">' +
            '<div style="font-size:12px;color:var(--muted);">Задаток зарезервирован</div>' +
            '<div class="disp" style="font-size:22px;color:var(--lime);line-height:1.1;">' + money(b.deposit_amount) + " СОМ</div>" +
          "</div>" +
          '<div style="font-size:10.5px;color:var(--muted);text-align:right;max-width:96px;line-height:1.3;">спишется только после подтверждения</div>' +
        "</div>" +
      "</div>" +
      '<div class="section-pad">' +
        '<div class="card" style="padding:16px;">' +
          '<div class="summary-row"><div class="disp" style="font-size:18px;">' + escapeHtml(b.venue_name.toUpperCase()) + '</div><div class="disp" style="font-size:18px;color:var(--lime);">' + formatTimeBishkek(b.start_time) + "–" + formatTimeBishkek(b.end_time) + "</div></div>" +
          '<div style="height:1px;background:var(--line);margin:12px 0;"></div>' +
          '<div class="summary-sub"><div>' + formatDateBishkek(b.start_time) + "</div></div>" +
        "</div>" +
      "</div>" +
      '<div class="footnote">Если админ не ответит за ' + Math.round(totalMs / 60000) + ' минут — бронь отменится, а задаток вернётся автоматически.</div>'
    );
  }

  // ---- view: result (confirmed / unavailable) ---------------------------

  function renderResult() {
    var ok = state.resolution === "confirmed";
    var b = state.booking;
    return (
      '<div class="center-screen">' +
        '<div class="status-icon-wrap ' + (ok ? "success" : "fail") + '">' + (ok ? ICON.check : ICON.cross) + "</div>" +
        '<div class="disp" style="font-size:26px;">' + (ok ? "БРОНЬ ПОДТВЕРЖДЕНА" : "СЛОТ НЕДОСТУПЕН") + "</div>" +
        '<div style="color:var(--muted);font-size:14px;max-width:280px;">' +
          (ok
            ? "Увидимся на поле — задаток списан, площадка ждёт вас."
            : "Администратор не подтвердил бронь вовремя. Задаток уже возвращён — попробуйте другое время.") +
        "</div>" +
        (ok && b ? (
          '<div class="card" style="padding:16px;width:100%;max-width:280px;text-align:left;">' +
            '<div class="disp" style="font-size:16px;">' + escapeHtml(b.venue_name.toUpperCase()) + "</div>" +
            '<div style="font-size:12.5px;color:var(--muted);margin-top:4px;">' + formatDateBishkek(b.start_time) + ", " + formatTimeBishkek(b.start_time) + "–" + formatTimeBishkek(b.end_time) + "</div>" +
          "</div>"
        ) : "") +
        '<button id="result-done-btn" class="btn-primary" style="max-width:280px;">К поиску</button>' +
      "</div>"
    );
  }

  // ---- view: team profile (TeamProfile.dc.html) --------------------------

  var ROLE_LABEL = { captain: "Капитан", member: "Игрок" };
  var MATCH_RESULT_COLOR = { win: "var(--lime)", draw: "var(--orange)", loss: "var(--red, oklch(0.62 0.21 25))" };

  function matchOutcomeForTeam(match, teamId) {
    var isHome = match.home_team === teamId;
    var mine = isHome ? match.home_score : match.away_score;
    var theirs = isHome ? match.away_score : match.home_score;
    if (mine > theirs) return "win";
    if (mine < theirs) return "loss";
    return "draw";
  }

  function teamHeader(rightContent) {
    return (
      '<div style="display:flex;align-items:center;justify-content:space-between;padding:26px 20px 0;">' +
        '<div class="icon-btn" id="team-back-btn">' + ICON.chevronLeft + "</div>" +
        '<div style="font-size:12.5px;font-weight:700;color:var(--muted);letter-spacing:0.05em;">КОМАНДА</div>' +
        (rightContent || '<div style="width:38px;"></div>') +
      "</div>"
    );
  }

  function renderTeam() {
    if (state.teamLoading) {
      return teamHeader() + '<div class="center-screen"><span class="spinner"></span></div>' + renderBottomNav("team");
    }
    if (!state.myTeam) {
      return renderTeamCreateForm();
    }

    var t = state.myTeam;
    var progress = t.points_to_next_rank != null
      ? Math.min(Math.max(t.rating_points / (t.rating_points + t.points_to_next_rank), 0), 1)
      : 1;
    var winRate = t.games_played > 0 ? Math.round((t.wins / t.games_played) * 100) + "%" : "—";

    var formSquares = "";
    var recent = state.teamMatches.slice(0, 5);
    for (var i = 0; i < 5; i++) {
      var m = recent[i];
      var bg = m ? MATCH_RESULT_COLOR[matchOutcomeForTeam(m, t.id)] : "var(--surface2)";
      formSquares += '<div style="width:22px;height:22px;border-radius:6px;background:' + bg + ';"></div>';
    }

    var roster = state.teamMembers.map(function (m) {
      return (
        '<div class="card" style="padding:12px 14px;display:flex;align-items:center;gap:12px;">' +
          '<div class="avatar">' + ICON.person + "</div>" +
          '<div style="flex:1;">' +
            '<div style="font-weight:600;font-size:14px;">' + escapeHtml(m.user_phone) + "</div>" +
            '<div style="font-size:11px;color:var(--muted);">' + (ROLE_LABEL[m.role] || m.role) + "</div>" +
          "</div>" +
          (m.role === "captain" ? '<div style="background:var(--lime);color:var(--lime-ink);font-size:10px;font-weight:700;padding:4px 9px;border-radius:7px;">КАПИТАН</div>' : "") +
        "</div>"
      );
    }).join("");

    return (
      teamHeader('<div class="icon-btn" id="team-leave-btn" title="Выйти из команды">' + ICON.logoutDoor + "</div>") +

      '<div style="display:flex;align-items:center;gap:16px;padding:20px 20px 0;">' +
        '<svg width="72" height="72" viewBox="0 0 72 72">' +
          '<polygon points="36,3 66,20 66,50 36,69 6,50 6,20" fill="var(--surface)" stroke="var(--lime)" stroke-width="2"/>' +
          '<polygon points="36,16 55,27 55,45 36,56 17,45 17,27" fill="none" stroke="var(--lime)" stroke-width="1.4" opacity="0.55"/>' +
          '<text x="36" y="43" font-family="\'Big Shoulders Display\',sans-serif" font-weight="900" font-size="24" fill="var(--lime)" text-anchor="middle">' + escapeHtml((t.name[0] || "?").toUpperCase()) + "</text>" +
        "</svg>" +
        "<div>" +
          '<div class="disp" style="font-size:28px;line-height:0.95;">' + escapeHtml(t.name.toUpperCase()) + "</div>" +
          '<div style="font-size:12.5px;color:var(--muted);margin-top:5px;">' + escapeHtml(t.district || "Район не указан") + " · с " + new Date(t.created_at).getFullYear() + "</div>" +
        "</div>" +
      "</div>" +

      '<div style="margin:20px 20px 0;">' +
        '<div class="card" style="padding:18px;position:relative;overflow:hidden;">' +
          '<div style="position:absolute;top:0;right:0;width:140px;height:140px;background:radial-gradient(circle,oklch(0.87 0.22 126 / 0.15),transparent 70%);"></div>' +
          '<div style="position:relative;display:flex;align-items:center;justify-content:space-between;">' +
            '<div style="display:flex;align-items:center;gap:12px;">' + ICON.cup2 +
              '<div><div style="font-size:11px;color:var(--muted);">ЗВАНИЕ</div><div class="disp" style="font-size:22px;color:var(--lime);line-height:1;">' + escapeHtml(t.rank_title.toUpperCase()) + "</div></div>" +
            "</div>" +
            '<div style="text-align:right;"><div class="disp" style="font-size:30px;line-height:1;">' + t.rating_points + '</div><div style="font-size:10.5px;color:var(--muted);">очков</div></div>' +
          "</div>" +
          '<div style="position:relative;margin-top:16px;height:7px;border-radius:4px;background:var(--surface2);overflow:hidden;"><div style="width:' + Math.round(progress * 100) + '%;height:100%;background:linear-gradient(90deg,var(--lime),oklch(0.9 0.2 126));"></div></div>' +
          '<div style="position:relative;font-size:11px;color:var(--muted);margin-top:8px;">' +
            (t.points_to_next_rank != null ? t.points_to_next_rank + " очков до следующего звания" : "Высшее звание достигнуто!") +
          "</div>" +
        "</div>" +
      "</div>" +

      '<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;padding:14px 20px 0;">' +
        '<div class="card" style="padding:14px 8px;text-align:center;"><div class="disp" style="font-size:26px;">' + t.games_played + '</div><div style="font-size:10px;color:var(--muted);">матчи</div></div>' +
        '<div class="card" style="padding:14px 8px;text-align:center;"><div class="disp" style="font-size:26px;color:var(--lime);">' + t.wins + '</div><div style="font-size:10px;color:var(--muted);">победы</div></div>' +
        '<div class="card" style="padding:14px 8px;text-align:center;"><div class="disp" style="font-size:26px;">' + winRate + '</div><div style="font-size:10px;color:var(--muted);">побед</div></div>' +
      "</div>" +

      '<div style="display:flex;align-items:center;justify-content:space-between;padding:16px 20px 0;">' +
        '<div style="font-size:11.5px;color:var(--muted);font-weight:600;">ПОСЛЕДНИЕ 5</div>' +
        '<div style="display:flex;gap:6px;">' + formSquares + "</div>" +
      "</div>" +

      renderTeamSubscriptionSection() +

      '<div style="padding:22px 20px 0;">' +
        '<div style="display:flex;align-items:baseline;justify-content:space-between;">' +
          '<div class="disp" style="font-size:19px;">СОСТАВ</div>' +
          '<div style="display:flex;align-items:center;gap:10px;">' +
            '<div id="team-invite-btn" style="font-size:12px;color:var(--lime);font-weight:600;cursor:pointer;">+ Пригласить</div>' +
            '<div style="font-size:12px;color:var(--muted);">' + state.teamMembers.length + " " + pluralize(state.teamMembers.length, "игрок", "игрока", "игроков") + "</div>" +
          "</div>" +
        "</div>" +
        '<div style="display:flex;flex-direction:column;gap:10px;margin-top:12px;">' + (roster || '<div style="color:var(--muted);font-size:13px;">Пока никого, кроме вас.</div>') + "</div>" +
      "</div>" +

      '<div style="padding:20px 20px 26px;">' +
        '<button id="team-challenge-btn" style="width:100%;background:var(--orange);color:oklch(0.15 0.02 40);font-weight:700;font-size:15px;padding:16px;border-radius:15px;text-align:center;display:flex;align-items:center;justify-content:center;gap:8px;border:none;cursor:pointer;">' +
          ICON.swords + "Бросить вызов" +
        "</button>" +
      "</div>" +

      renderBottomNav("team")
    );
  }

  function renderTeamSubscriptionSection() {
    if (!state.teamSubscriptionChecked) {
      return '<div style="padding:16px 20px 0;"><div class="card" style="padding:16px;text-align:center;"><span class="spinner"></span></div></div>';
    }

    if (!state.teamExtendedStats) {
      return (
        '<div style="padding:16px 20px 0;">' +
          '<div class="card" style="padding:16px;display:flex;align-items:center;justify-content:space-between;gap:10px;">' +
            '<div><div style="font-weight:700;font-size:14px;">Расширенная статистика</div><div style="font-size:11.5px;color:var(--muted);margin-top:2px;">Помесячная разбивка, серии побед — по подписке</div></div>' +
            '<button id="team-subscribe-btn" style="background:var(--lime);color:var(--lime-ink);font-weight:700;font-size:12.5px;padding:9px 14px;border-radius:10px;border:none;cursor:pointer;white-space:nowrap;" ' + (state.teamSubscribeBusy ? "disabled" : "") + ">" +
              (state.teamSubscribeBusy ? '<span class="spinner"></span>' : "Оформить") +
            "</button>" +
          "</div>" +
        "</div>"
      );
    }

    var stats = state.teamExtendedStats;
    var monthsHtml = stats.monthly_breakdown.map(function (m) {
      return '<div style="display:flex;justify-content:space-between;font-size:12px;color:var(--muted);padding:4px 0;"><div>' + escapeHtml(m.month) + "</div><div>" + m.wins + "В " + m.draws + "Н " + m.losses + "П</div></div>";
    }).join("");

    return (
      '<div style="padding:16px 20px 0;">' +
        '<div class="card" style="padding:16px;">' +
          '<div style="display:flex;align-items:center;justify-content:space-between;cursor:pointer;" id="team-stats-toggle">' +
            '<div style="font-weight:700;font-size:14px;color:var(--lime);">Расширенная статистика</div>' +
            ICON.chevronDown +
          "</div>" +
          (state.teamStatsExpanded ? (
            '<div style="margin-top:12px;">' +
              '<div style="display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted);"><div>Win rate</div><div style="color:var(--text);font-weight:600;">' + stats.win_rate_percent + '%</div></div>' +
              '<div style="display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted);margin-top:6px;"><div>Лучшая серия побед</div><div style="color:var(--text);font-weight:600;">' + stats.longest_win_streak + "</div></div>" +
              (monthsHtml ? '<div style="height:1px;background:var(--line);margin:12px 0;"></div>' + monthsHtml : "") +
            "</div>"
          ) : "") +
        "</div>" +
      "</div>"
    );
  }

  function renderTeamCreateForm() {
    var districtOptions = '<option value="">Без района</option>';
    DISTRICTS.forEach(function (d) { districtOptions += '<option value="' + escapeAttr(d) + '">' + escapeHtml(d) + "</option>"; });

    return (
      teamHeader() +
      '<div class="center-screen" style="flex:0;padding-top:40px;">' +
        '<div style="color:var(--lime);">' + ICON.cup2 + "</div>" +
        '<div class="disp" style="font-size:26px;">У ВАС ЕЩЁ НЕТ КОМАНДЫ</div>' +
        '<div style="color:var(--muted);font-size:14px;max-width:280px;">Создайте команду — рейтинг, состав и вызовы появятся сразу.</div>' +
        '<div style="width:100%;max-width:280px;">' +
          '<div class="field-label">Название</div>' +
          '<input id="team-name-input" class="text-input" placeholder="Барс FC">' +
        "</div>" +
        '<div style="width:100%;max-width:280px;">' +
          '<div class="field-label">Район (необязательно)</div>' +
          '<select id="team-district-input" class="text-input">' + districtOptions + "</select>" +
        "</div>" +
        (state.teamCreateError ? '<div class="error-text">' + escapeHtml(state.teamCreateError) + "</div>" : "") +
        '<button id="team-create-btn" class="btn-primary" style="max-width:280px;" ' + (state.teamCreateBusy ? "disabled" : "") + ">" +
          (state.teamCreateBusy ? '<span class="spinner"></span>' : "Создать команду") +
        "</button>" +
      "</div>" +
      renderTeamJoinSection() +
      renderBottomNav("team")
    );
  }

  function renderTeamJoinSection() {
    var resultsHtml;
    if (state.teamSearchLoading) {
      resultsHtml = '<div style="text-align:center;padding:16px;"><span class="spinner"></span></div>';
    } else if (state.teamSearchQuery && state.teamSearchResults.length === 0) {
      resultsHtml = '<div style="color:var(--muted);font-size:13px;text-align:center;padding:12px;">Ничего не нашлось.</div>';
    } else {
      resultsHtml = state.teamSearchResults.map(function (t) {
        var busy = state.teamJoinBusyId === t.id;
        return (
          '<div class="card" style="padding:12px 14px;display:flex;align-items:center;gap:10px;">' +
            '<div style="flex:1;"><div style="font-weight:700;font-size:14px;">' + escapeHtml(t.name) + '</div><div style="font-size:11px;color:var(--muted);margin-top:2px;">' + escapeHtml(t.district || "Район не указан") + " · " + t.members_count + " " + pluralize(t.members_count, "игрок", "игрока", "игроков") + "</div></div>" +
            '<button class="team-join-btn" data-team-id="' + t.id + '" ' + (busy ? "disabled" : "") + ' style="background:var(--lime);color:var(--lime-ink);font-weight:700;font-size:12.5px;padding:8px 14px;border-radius:10px;border:none;cursor:pointer;">' +
              (busy ? '<span class="spinner"></span>' : "Вступить") +
            "</button>" +
          "</div>"
        );
      }).join("");
    }

    return (
      '<div style="padding:8px 20px 0;">' +
        '<div style="height:1px;background:var(--line);margin:8px 0 20px;"></div>' +
        '<div class="disp" style="font-size:19px;">ИЛИ ВСТУПИТЕ В СУЩЕСТВУЮЩУЮ</div>' +
        '<input id="team-search-input" class="text-input" style="margin-top:10px;" placeholder="Название команды" value="' + escapeAttr(state.teamSearchQuery) + '">' +
        '<div style="display:flex;flex-direction:column;gap:10px;margin-top:12px;">' + resultsHtml + "</div>" +
      "</div>"
    );
  }

  function renderChallengePicker() {
    var list;
    if (state.challengeCandidatesLoading) {
      list = '<div style="text-align:center;padding:20px;"><span class="spinner"></span></div>';
    } else if (state.challengeCandidates.length === 0) {
      list = '<div style="color:var(--muted);font-size:13px;text-align:center;padding:20px;">Других команд пока нет.</div>';
    } else {
      list = state.challengeCandidates.map(function (c) {
        return (
          '<div class="card challenge-candidate" data-team-id="' + c.id + '" style="padding:14px;display:flex;align-items:center;justify-content:between;gap:10px;cursor:pointer;">' +
            '<div style="flex:1;"><div style="font-weight:700;font-size:14px;">' + escapeHtml(c.name) + '</div><div style="font-size:11px;color:var(--muted);margin-top:2px;">' + escapeHtml(c.district || "Район не указан") + " · " + c.rating_points + " очков</div></div>" +
            ICON.chevron.replace("var(--lime-ink)", "var(--muted)") +
          "</div>"
        );
      }).join("");
    }

    return (
      '<div class="sheet-backdrop" id="challenge-picker-backdrop" style="z-index:46;">' +
        '<div class="sheet-panel">' +
          '<div class="sheet-handle"></div>' +
          '<div class="sheet-header"><div class="disp" style="font-size:18px;">КОМУ БРОСИТЬ ВЫЗОВ?</div><div class="icon-btn" id="challenge-picker-close">' + ICON.close + "</div></div>" +
          '<div style="display:flex;flex-direction:column;gap:10px;margin-top:10px;">' + list + "</div>" +
        "</div>" +
      "</div>"
    );
  }

  function renderInviteInfo() {
    var name = state.myTeam ? state.myTeam.name : "";
    return (
      '<div class="sheet-backdrop" id="invite-info-backdrop" style="z-index:46;">' +
        '<div class="sheet-panel">' +
          '<div class="sheet-handle"></div>' +
          '<div class="sheet-header"><div class="disp" style="font-size:18px;">КАК ПРИГЛАСИТЬ</div><div class="icon-btn" id="invite-info-close">' + ICON.close + "</div></div>" +
          '<div style="font-size:13.5px;color:var(--muted);line-height:1.5;margin-top:6px;">Прямых приглашений пока нет — друг вступает сам: открывает Футбол → «Команда» → находит вашу команду по названию → жмёт «Вступить».</div>' +
          '<div class="card" style="padding:16px;margin-top:16px;display:flex;align-items:center;justify-content:space-between;gap:10px;">' +
            '<div class="disp" style="font-size:20px;">' + escapeHtml(name.toUpperCase()) + "</div>" +
            '<div id="invite-copy-name-btn" style="background:var(--lime);color:var(--lime-ink);font-weight:700;font-size:12px;padding:8px 12px;border-radius:10px;cursor:pointer;white-space:nowrap;">Скопировать</div>' +
          "</div>" +
          '<div style="font-size:11.5px;color:var(--muted);margin-top:10px;">Отправьте название другу любым удобным способом — он найдёт команду по нему в поиске.</div>' +
        "</div>" +
      "</div>"
    );
  }

  // ---- view: activity feed (Feed.dc.html) --------------------------------

  function relativeLabel(iso) {
    var diffMs = Date.now() - new Date(iso).getTime();
    var minutes = Math.floor(diffMs / 60000);
    if (minutes < 1) return "только что";
    if (minutes < 60) return minutes + " " + pluralize(minutes, "минуту", "минуты", "минут") + " назад";
    var hours = Math.floor(minutes / 60);
    if (hours < 24) return hours + " " + pluralize(hours, "час", "часа", "часов") + " назад";
    var days = Math.floor(hours / 24);
    if (days === 1) return "вчера";
    if (days < 7) return days + " " + pluralize(days, "день", "дня", "дней") + " назад";
    return formatDateBishkek(iso);
  }

  function renderFeedCard(item) {
    if (item.kind === "event") {
      var e = item.data;
      if (e.event_type === "rank_up") {
        return (
          '<div class="card feed-card" style="background:linear-gradient(135deg, oklch(0.24 0.03 126) 0%, var(--surface) 60%);border-color:oklch(0.87 0.22 126 / 0.35);">' +
            '<div class="feed-bar" style="background:var(--lime);"></div>' +
            '<div style="display:flex;gap:12px;padding-left:4px;">' + ICON.cup2 +
              '<div><div class="disp" style="font-size:18px;color:var(--lime);line-height:1.1;">' + escapeHtml(e.title.toUpperCase()) + "</div>" +
              (e.body ? '<div style="font-size:12.5px;color:var(--muted);margin-top:4px;">' + escapeHtml(e.body) + "</div>" : "") + "</div>" +
            "</div>" +
            '<div style="font-size:10.5px;color:var(--muted);margin-top:10px;padding-left:42px;">' + relativeLabel(e.created_at) + "</div>" +
          "</div>"
        );
      }
      var icon = e.event_type === "rating_changed" ? ICON.trendUp : ICON.swordsOrange;
      var barColor = e.event_type === "rating_changed" ? "var(--lime)" : "var(--orange)";
      return (
        '<div class="card feed-card">' +
          '<div class="feed-bar" style="background:' + barColor + ';"></div>' +
          '<div style="display:flex;align-items:center;gap:12px;padding-left:4px;">' + icon +
            '<div style="flex:1;"><div style="font-weight:700;font-size:14px;">' + escapeHtml(e.title) + "</div>" +
            (e.body ? '<div style="font-size:12.5px;color:var(--muted);margin-top:3px;">' + escapeHtml(e.body) + "</div>" : "") + "</div>" +
          "</div>" +
          '<div style="font-size:10.5px;color:var(--muted);margin-top:8px;padding-left:36px;">' + relativeLabel(e.created_at) + "</div>" +
        "</div>"
      );
    }

    if (item.kind === "challenge") {
      var c = item.data;
      return (
        '<div class="card feed-card">' +
          '<div class="feed-bar" style="background:var(--orange);"></div>' +
          '<div style="display:flex;gap:12px;padding-left:4px;">' + ICON.swordsOrange +
            '<div style="flex:1;"><div style="font-weight:700;font-size:14.5px;">' + escapeHtml(c.challenger_team_name) + " бросили вызов</div>" +
            '<div style="font-size:12px;color:var(--muted);margin-top:3px;">' + (c.proposed_time ? "Хотят сыграть " + formatDateBishkek(c.proposed_time) + ", " + formatTimeBishkek(c.proposed_time) : "Время пока не предложено") + "</div></div>" +
          "</div>" +
          '<div style="display:flex;gap:8px;margin-top:14px;padding-left:38px;">' +
            '<div class="challenge-accept-btn" data-challenge-id="' + c.id + '" style="flex:1;background:var(--lime);color:var(--lime-ink);font-weight:700;font-size:12.5px;padding:9px;border-radius:10px;text-align:center;cursor:pointer;">Принять</div>' +
            '<div class="challenge-decline-btn" data-challenge-id="' + c.id + '" style="flex:1;border:1.5px solid var(--line);color:var(--muted);font-weight:600;font-size:12.5px;padding:9px;border-radius:10px;text-align:center;cursor:pointer;">Отклонить</div>' +
          "</div>" +
        "</div>"
      );
    }

    if (item.kind === "match") {
      var m = item.data;
      var myId = state.myTeam ? state.myTeam.id : null;
      var isHome = m.home_team === myId;
      var myName = isHome ? m.home_team_name : m.away_team_name;
      var theirName = isHome ? m.away_team_name : m.home_team_name;
      var myScore = isHome ? m.home_score : m.away_score;
      var theirScore = isHome ? m.away_score : m.home_score;
      return (
        '<div class="card feed-card">' +
          '<div class="feed-bar" style="background:var(--surface2);"></div>' +
          '<div style="display:flex;align-items:center;justify-content:space-between;padding-left:4px;">' +
            '<div style="font-size:12.5px;color:var(--muted);">Товарищеский матч</div>' +
            '<div style="font-size:10.5px;color:var(--muted);">' + relativeLabel(m.played_at || m.created_at) + "</div>" +
          "</div>" +
          '<div style="display:flex;align-items:center;justify-content:space-between;margin-top:10px;padding-left:4px;">' +
            '<div style="font-weight:700;font-size:14.5px;">' + escapeHtml(myName) + "</div>" +
            '<div class="disp" style="font-size:26px;color:var(--lime);">' + myScore + " : " + theirScore + "</div>" +
            '<div style="font-weight:700;font-size:14.5px;color:var(--muted);">' + escapeHtml(theirName) + "</div>" +
          "</div>" +
        "</div>"
      );
    }

    var n = item.data;
    return (
      '<div class="card feed-card" style="padding:14px 16px;">' +
        '<div style="display:flex;align-items:center;gap:10px;">' +
          '<div style="font-size:10px;font-weight:700;color:var(--muted);letter-spacing:0.04em;padding:3px 8px;border:1px solid var(--line);border-radius:6px;">' + escapeHtml(n.source_name.toUpperCase()) + "</div>" +
          '<div style="font-size:10.5px;color:var(--muted);">' + relativeLabel(n.published_at) + "</div>" +
        "</div>" +
        '<a href="' + escapeAttr(n.source_url) + '" target="_blank" rel="noopener" style="display:block;font-size:13.5px;margin-top:8px;color:var(--text);">' + escapeHtml(n.title) + "</a>" +
      "</div>"
    );
  }

  function renderFeed() {
    var body;
    if (state.feedLoading) {
      body = '<div class="center-screen"><span class="spinner"></span></div>';
    } else if (state.feedItems.length === 0) {
      body = '<div style="padding:0 20px;color:var(--muted);font-size:13px;">Пока пусто — сыграйте матч или бросьте вызов, чтобы тут что-то появилось.</div>';
    } else {
      body = '<div style="display:flex;flex-direction:column;gap:12px;padding:14px 20px 24px;">' + state.feedItems.map(renderFeedCard).join("") + "</div>";
    }

    return (
      '<div style="display:flex;align-items:center;justify-content:space-between;padding:26px 20px 4px;">' +
        '<div class="disp" style="font-size:32px;">ЛЕНТА</div>' +
        '<div class="icon-btn">' + ICON.slidersFilter + "</div>" +
      "</div>" +
      body +
      renderBottomNav("feed")
    );
  }

  // ---- view: my bookings (не из макета — история броней) ----------------

  var BOOKING_STATUS_COLOR = {
    confirmed: "var(--lime)",
    pending_confirmation: "var(--orange)",
    extension_pending: "var(--orange)",
    declined: "var(--red, oklch(0.62 0.21 25))",
    expired: "var(--red, oklch(0.62 0.21 25))",
    cancelled: "var(--muted)",
    completed: "var(--muted)"
  };

  function renderMyBookings() {
    var body;
    if (state.myBookingsLoading) {
      body = '<div class="center-screen"><span class="spinner"></span></div>';
    } else if (state.myBookingsList.length === 0) {
      body = (
        '<div class="center-screen">' +
          '<div style="color:var(--muted);font-size:14px;">Броней пока нет — самое время что-то забронировать.</div>' +
          '<button id="my-bookings-empty-search-btn" class="btn-primary" style="max-width:240px;">К поиску</button>' +
        "</div>"
      );
    } else {
      body = '<div style="display:flex;flex-direction:column;gap:12px;padding:14px 20px 24px;">' + state.myBookingsList.map(renderMyBookingCard).join("") + "</div>";
    }

    return (
      '<div style="display:flex;align-items:center;justify-content:space-between;padding:26px 20px 0;">' +
        '<div class="icon-btn" id="my-bookings-back-btn">' + ICON.chevronLeft + "</div>" +
        '<div style="font-size:12.5px;font-weight:700;color:var(--muted);letter-spacing:0.05em;">МОИ БРОНИ</div>' +
        '<div style="width:38px;"></div>' +
      "</div>" +
      body
    );
  }

  function renderMyBookingCard(b) {
    var clickable = b.status === "pending_confirmation" || b.status === "extension_pending";
    var color = BOOKING_STATUS_COLOR[b.status] || "var(--muted)";
    return (
      '<div class="card my-booking-card" ' + (clickable ? 'data-booking-id="' + b.id + '" style="padding:16px;cursor:pointer;"' : 'style="padding:16px;"') + '>' +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">' +
          '<div><div class="disp" style="font-size:18px;">' + escapeHtml(b.venue_name.toUpperCase()) + '</div>' +
          '<div style="font-size:12px;color:var(--muted);margin-top:4px;">' + formatDateBishkek(b.start_time) + ", " + formatTimeBishkek(b.start_time) + "–" + formatTimeBishkek(b.end_time) + "</div></div>" +
          '<div style="background:' + color + ';color:var(--bg);font-size:10px;font-weight:700;padding:4px 9px;border-radius:7px;white-space:nowrap;">' + escapeHtml(b.status_display.toUpperCase()) + "</div>" +
        "</div>" +
        '<div style="height:1px;background:var(--line);margin:12px 0;"></div>' +
        '<div style="display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted);">' +
          "<div>Задаток " + money(b.deposit_amount) + " сом</div>" +
          (clickable ? '<div style="color:var(--lime);font-weight:600;">Смотреть →</div>' : "") +
        "</div>" +
      "</div>"
    );
  }

  // ---- view: tournaments (не из макета — бэкенд был готов, экрана не было) ----

  var TOURNAMENT_STATUS_COLOR = {
    registration_open: "var(--lime)",
    registration_closed: "var(--orange)",
    cancelled: "var(--red, oklch(0.62 0.21 25))",
    completed: "var(--muted)"
  };

  function renderTournaments() {
    var body;
    if (state.tournamentsLoading) {
      body = '<div class="center-screen"><span class="spinner"></span></div>';
    } else if (state.tournamentsList.length === 0) {
      body = (
        '<div class="center-screen">' +
          '<div style="color:var(--muted);font-size:14px;">Турниров пока нет — создайте первый.</div>' +
          '<button id="tournament-empty-create-btn" class="btn-primary" style="max-width:240px;">Создать турнир</button>' +
        "</div>"
      );
    } else {
      body = '<div style="display:flex;flex-direction:column;gap:12px;padding:14px 20px 24px;">' + state.tournamentsList.map(renderTournamentCard).join("") + "</div>";
    }

    return (
      '<div style="display:flex;align-items:center;justify-content:space-between;padding:26px 20px 4px;">' +
        '<div class="disp" style="font-size:32px;">ТУРНИРЫ</div>' +
        '<div class="icon-btn" id="tournament-create-btn">' + ICON.plus + "</div>" +
      "</div>" +
      body +
      renderBottomNav("cup")
    );
  }

  function renderTournamentCard(t) {
    var color = TOURNAMENT_STATUS_COLOR[t.status] || "var(--muted)";
    var teamsLabel = t.registered_teams_count + (t.max_teams ? "/" + t.max_teams : "") + " " + pluralize(t.registered_teams_count, "команда", "команды", "команд");
    return (
      '<div class="card tournament-card" data-tournament-id="' + t.id + '" style="padding:16px;cursor:pointer;">' +
        (t.sponsor_name ? '<div style="font-size:10px;font-weight:700;color:var(--muted);letter-spacing:0.04em;margin-bottom:8px;">ПРИ ПОДДЕРЖКЕ ' + escapeHtml(t.sponsor_name.toUpperCase()) + "</div>" : "") +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">' +
          '<div class="disp" style="font-size:20px;line-height:1.05;">' + escapeHtml(t.name.toUpperCase()) + "</div>" +
          '<div style="background:' + color + ';color:var(--bg);font-size:10px;font-weight:700;padding:4px 9px;border-radius:7px;white-space:nowrap;">' + escapeHtml(t.status_display.toUpperCase()) + "</div>" +
        "</div>" +
        '<div style="height:1px;background:var(--line);margin:12px 0;"></div>' +
        '<div style="display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted);">' +
          "<div>Взнос " + money(t.entry_fee) + " сом · " + teamsLabel + "</div>" +
          "<div>до " + formatDateBishkek(t.registration_deadline) + "</div>" +
        "</div>" +
      "</div>"
    );
  }

  function renderTournamentCreateForm() {
    return (
      '<div class="sheet-backdrop" id="tournament-create-backdrop" style="z-index:46;">' +
        '<div class="sheet-panel">' +
          '<div class="sheet-handle"></div>' +
          '<div class="sheet-header"><div class="disp" style="font-size:18px;">НОВЫЙ ТУРНИР</div><div class="icon-btn" id="tournament-create-close">' + ICON.close + "</div></div>" +
          '<div style="display:flex;flex-direction:column;gap:14px;margin-top:10px;">' +
            '<div><div class="field-label">Название</div><input id="tournament-name-input" class="text-input" placeholder="Кубок офиса"></div>' +
            '<div><div class="field-label">При поддержке (необязательно)</div><input id="tournament-sponsor-input" class="text-input" placeholder="Название бренда"></div>' +
            '<div style="display:flex;gap:10px;">' +
              '<div style="flex:1;"><div class="field-label">Взнос с команды, сом</div><input id="tournament-fee-input" class="text-input" type="number" min="0" value="1000"></div>' +
              '<div style="flex:1;"><div class="field-label">Мин. команд</div><input id="tournament-min-input" class="text-input" type="number" min="2" value="4"></div>' +
            "</div>" +
            '<div><div class="field-label">Макс. команд (необязательно)</div><input id="tournament-max-input" class="text-input" type="number" min="2" placeholder="Без лимита"></div>' +
            '<div><div class="field-label">Дедлайн регистрации</div><input id="tournament-deadline-input" class="text-input" type="datetime-local"></div>' +
            (state.tournamentCreateError ? '<div class="error-text">' + escapeHtml(state.tournamentCreateError) + "</div>" : "") +
            '<button id="tournament-create-submit-btn" class="btn-primary" ' + (state.tournamentCreateBusy ? "disabled" : "") + ">" +
              (state.tournamentCreateBusy ? '<span class="spinner"></span>' : "Создать") +
            "</button>" +
          "</div>" +
        "</div>" +
      "</div>"
    );
  }

  function renderTournamentDetail() {
    if (state.tournamentDetailLoading || !state.tournamentDetail) {
      return (
        '<div style="display:flex;align-items:center;justify-content:space-between;padding:26px 20px 0;">' +
          '<div class="icon-btn" id="tournament-detail-back-btn">' + ICON.chevronLeft + "</div>" +
          '<div style="font-size:12.5px;font-weight:700;color:var(--muted);letter-spacing:0.05em;">ТУРНИР</div>' +
          '<div style="width:38px;"></div>' +
        "</div>" +
        '<div class="center-screen"><span class="spinner"></span></div>'
      );
    }

    var t = state.tournamentDetail;
    var color = TOURNAMENT_STATUS_COLOR[t.status] || "var(--muted)";
    var myReg = state.myTeam ? state.tournamentRegistrations.find(function (r) { return r.team === state.myTeam.id && r.status === "registered"; }) : null;

    var actionHtml = "";
    if (t.status === "registration_open") {
      if (myReg) {
        actionHtml = (
          '<div class="card" style="padding:16px;display:flex;align-items:center;justify-content:space-between;gap:10px;">' +
            '<div><div style="font-weight:700;font-size:14px;color:var(--lime);">Вы зарегистрированы</div><div style="font-size:11.5px;color:var(--muted);margin-top:2px;">' + escapeHtml(state.myTeam.name) + "</div></div>" +
            '<div id="tournament-cancel-reg-btn" style="color:var(--muted);font-weight:600;font-size:12.5px;cursor:pointer;text-decoration:underline;">Отменить</div>' +
          "</div>"
        );
      } else if (state.myTeam) {
        actionHtml = (
          '<button id="tournament-register-btn" class="btn-primary" ' + (state.tournamentRegisterBusy ? "disabled" : "") + ">" +
            (state.tournamentRegisterBusy ? '<span class="spinner"></span>' : "Зарегистрировать «" + escapeHtml(state.myTeam.name) + "»") +
          "</button>"
        );
      } else {
        actionHtml = '<div style="color:var(--muted);font-size:13px;text-align:center;">Нужна своя команда, чтобы зарегистрироваться — создайте её на вкладке «Команда».</div>';
      }
    }

    var teamsHtml = state.tournamentRegistrations.filter(function (r) { return r.status === "registered"; }).map(function (r) {
      return '<div class="card" style="padding:12px 14px;font-weight:600;font-size:13.5px;">' + escapeHtml(r.team_name) + "</div>";
    }).join("");

    var standingsHtml = "";
    if (state.tournamentStandings.length > 0) {
      standingsHtml = (
        '<div style="padding:22px 20px 0;">' +
          '<div class="disp" style="font-size:19px;">ТАБЛИЦА</div>' +
          '<div style="display:flex;flex-direction:column;gap:8px;margin-top:12px;">' +
            state.tournamentStandings.map(function (row, i) {
              return (
                '<div class="card" style="padding:12px 14px;display:flex;align-items:center;gap:12px;">' +
                  '<div class="disp" style="font-size:16px;color:var(--muted);width:20px;">' + (i + 1) + "</div>" +
                  '<div style="flex:1;font-weight:600;font-size:13.5px;">' + escapeHtml(row.team_name) + "</div>" +
                  '<div style="font-size:11px;color:var(--muted);">И ' + row.played + " · В " + row.wins + " · Н " + row.draws + " · П " + row.losses + "</div>" +
                  '<div class="disp" style="font-size:18px;color:var(--lime);width:28px;text-align:right;">' + row.points + "</div>" +
                "</div>"
              );
            }).join("") +
          "</div>" +
        "</div>"
      );
    }

    var matchesHtml = "";
    if (state.tournamentMatches.length > 0) {
      matchesHtml = (
        '<div style="padding:22px 20px 24px;">' +
          '<div class="disp" style="font-size:19px;">МАТЧИ</div>' +
          '<div style="display:flex;flex-direction:column;gap:8px;margin-top:12px;">' +
            state.tournamentMatches.map(function (m) {
              var played = m.match_status === "played";
              return (
                '<div class="card" style="padding:12px 14px;">' +
                  '<div style="font-size:10.5px;color:var(--muted);margin-bottom:6px;">РАУНД ' + m.round_number + "</div>" +
                  '<div style="display:flex;align-items:center;justify-content:space-between;">' +
                    '<div style="font-weight:600;font-size:13.5px;flex:1;">' + escapeHtml(m.home_team_name) + "</div>" +
                    '<div class="disp" style="font-size:18px;color:' + (played ? "var(--lime)" : "var(--muted)") + ';padding:0 10px;">' + (played ? m.home_score + " : " + m.away_score : "—") + "</div>" +
                    '<div style="font-weight:600;font-size:13.5px;flex:1;text-align:right;">' + escapeHtml(m.away_team_name) + "</div>" +
                  "</div>" +
                "</div>"
              );
            }).join("") +
          "</div>" +
        "</div>"
      );
    }

    return (
      '<div style="display:flex;align-items:center;justify-content:space-between;padding:26px 20px 0;">' +
        '<div class="icon-btn" id="tournament-detail-back-btn">' + ICON.chevronLeft + "</div>" +
        '<div style="font-size:12.5px;font-weight:700;color:var(--muted);letter-spacing:0.05em;">ТУРНИР</div>' +
        '<div style="width:38px;"></div>' +
      "</div>" +
      '<div style="padding:16px 20px 0;">' +
        (t.sponsor_name ? '<div style="font-size:10px;font-weight:700;color:var(--muted);letter-spacing:0.04em;margin-bottom:8px;">ПРИ ПОДДЕРЖКЕ ' + escapeHtml(t.sponsor_name.toUpperCase()) + "</div>" : "") +
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px;">' +
          '<div class="disp" style="font-size:26px;line-height:1.05;">' + escapeHtml(t.name.toUpperCase()) + "</div>" +
          '<div style="background:' + color + ';color:var(--bg);font-size:10px;font-weight:700;padding:4px 9px;border-radius:7px;white-space:nowrap;">' + escapeHtml(t.status_display.toUpperCase()) + "</div>" +
        "</div>" +
        (t.description ? '<div style="font-size:13px;color:var(--muted);margin-top:8px;">' + escapeHtml(t.description) + "</div>" : "") +
      "</div>" +
      '<div style="padding:16px 20px 0;">' +
        '<div class="card" style="padding:16px;display:flex;justify-content:space-between;font-size:12.5px;color:var(--muted);">' +
          "<div>Взнос " + money(t.entry_fee) + " сом</div>" +
          "<div>" + t.registered_teams_count + (t.max_teams ? "/" + t.max_teams : "") + " команд</div>" +
          "<div>до " + formatDateBishkek(t.registration_deadline) + "</div>" +
        "</div>" +
      "</div>" +
      (actionHtml ? '<div style="padding:16px 20px 0;">' + actionHtml + "</div>" : "") +
      (teamsHtml ? '<div style="padding:22px 20px 0;"><div class="disp" style="font-size:19px;">КОМАНДЫ</div><div style="display:flex;flex-direction:column;gap:8px;margin-top:12px;">' + teamsHtml + "</div></div>" : "") +
      standingsHtml +
      matchesHtml
    );
  }

  // ---- overlay: extension offer (roadmap 2.3, ExtendGame.dc.html) -------

  function renderExtensionOffer() {
    var b = state.extensionOffer;
    var deadline = new Date(b.confirmation_deadline).getTime();
    var created = new Date(b.created_at).getTime();
    var now = Date.now();
    var totalMs = Math.max(deadline - created, 1);
    var remainingMs = Math.max(deadline - now, 0);
    var fraction = Math.min(Math.max(remainingMs / totalMs, 0), 1);
    var minutesLeft = Math.max(Math.ceil(remainingMs / 60000), 0);

    return (
      '<div class="ext-backdrop">' +
        '<div class="ext-sheet">' +
          '<div class="ext-sheet-stripe"></div>' +
          '<div class="sheet-handle"></div>' +
          '<div style="display:flex;align-items:center;gap:10px;color:var(--orange);">' + ICON.bell +
            '<div style="font-size:12.5px;font-weight:700;color:var(--orange);letter-spacing:0.03em;">ДО КОНЦА СЛОТА ' + minutesLeft + " МИН</div>" +
          "</div>" +
          '<div class="disp" style="font-size:38px;line-height:0.98;margin-top:14px;">ПРОДЛИТЬ<br>ЕЩЁ НА ЧАС?</div>' +
          '<div style="font-size:13.5px;color:var(--muted);margin-top:10px;line-height:1.4;">Площадка свободна следующим часом — успейте занять её первыми, пока не перехватили.</div>' +
          '<div style="display:flex;align-items:baseline;gap:8px;margin-top:22px;">' +
            '<div class="disp" style="font-size:32px;color:var(--lime);">+' + money(b.price) + "</div>" +
            '<div style="font-size:13px;color:var(--muted);">сом за час</div>' +
          "</div>" +
          '<div style="display:flex;flex-direction:column;gap:10px;margin-top:20px;">' +
            '<button id="ext-confirm-btn" class="btn-primary" ' + (state.extensionBusy ? "disabled" : "") + ">" +
              (state.extensionBusy ? '<span class="spinner"></span>' : "Продлить") +
            "</button>" +
            '<div id="ext-decline-btn" style="color:var(--muted);font-weight:600;font-size:13.5px;padding:6px;text-align:center;cursor:pointer;">Нет, спасибо</div>' +
          "</div>" +
          '<div class="ext-progress"><div class="ext-progress-fill" style="width:' + Math.round(fraction * 100) + '%;"></div></div>' +
          '<div style="text-align:center;font-size:10.5px;color:var(--muted);margin-top:8px;">Слот придержан для вас, пока вы решаете</div>' +
        "</div>" +
      "</div>"
    );
  }

  function startExtensionWatch() {
    stopExtensionWatch();
    checkForExtensionOffer();
    state.extensionWatchHandle = setInterval(checkForExtensionOffer, 20000);
  }

  function stopExtensionWatch() {
    if (state.extensionWatchHandle) clearInterval(state.extensionWatchHandle);
    state.extensionWatchHandle = null;
  }

  function checkForExtensionOffer() {
    if (!state.token || state.extensionOffer) return;
    apiFetch("/bookings/")
      .then(function (list) {
        var found = (list || []).find(function (b) { return b.status === "extension_pending"; });
        if (found) {
          state.extensionOffer = found;
          render();
        }
      })
      .catch(function () {}); // фоновый опрос — молча игнорируем сетевые сбои, следующий тик повторит
  }

  function resolveExtensionOffer(action) {
    if (state.extensionBusy || !state.extensionOffer) return;
    var id = state.extensionOffer.id;
    var path = "/bookings/" + id + "/extension/" + action + "/";
    state.extensionBusy = true;
    render();
    apiFetch(path, { method: "POST" })
      .then(function () {
        state.extensionBusy = false;
        state.extensionOffer = null;
        render();
        showToast(action === "confirm" ? "Игра продлена ещё на час" : "Хорошо, до встречи в следующий раз");
        if (state.view === "main") loadVenues();
      })
      .catch(function (err) {
        state.extensionBusy = false;
        if (err.status === 409) {
          // Уже разрешилось (например, автоотмена по таймауту сработала раньше) — просто закрыть.
          state.extensionOffer = null;
        }
        render();
        showToast(err.message || "Не удалось обработать продление.");
      });
  }

  // ---- actions: team profile (TeamProfile.dc.html) ----------------------

  function asArray(data) {
    return Array.isArray(data) ? data : (data && data.results) || [];
  }

  function loadMyTeam() {
    state.teamLoading = true;
    render();
    apiFetch("/teams/?mine=true")
      .then(function (data) {
        var teams = asArray(data);
        if (teams.length === 0) {
          state.myTeam = null;
          state.teamMembers = [];
          state.teamMatches = [];
          state.teamLoading = false;
          render();
          return;
        }
        state.myTeam = teams[0];
        checkTeamSubscription(teams[0].id); // не блокирует основной рендер — своя мини-загрузка в секции
        return loadTeamMembersAndMatches(teams[0].id).then(function () {
          state.teamLoading = false;
          render();
        });
      })
      .catch(function (err) {
        if (err.status === 401) return logout();
        state.teamLoading = false;
        render();
        showToast(err.message || "Не удалось загрузить команду.");
      });
  }

  function loadTeamMembersAndMatches(teamId) {
    return Promise.all([
      apiFetch("/teams/" + teamId + "/members/"),
      apiFetch("/teams/matches/?team=" + teamId)
    ]).then(function (results) {
      state.teamMembers = asArray(results[0]);
      state.teamMatches = asArray(results[1]).filter(function (m) { return m.status === "played"; });
    });
  }

  function checkTeamSubscription(teamId) {
    // Отдельного "проверить подписку" эндпойнта нет — extended-stats/ и есть
    // проверка: 200 с данными значит активна, 402 значит нет. Тот же контракт,
    // которым бэкенд уже был покрыт тестами (apps.community.tests).
    state.teamSubscriptionChecked = false;
    apiFetch("/community/teams/" + teamId + "/extended-stats/")
      .then(function (data) {
        state.teamExtendedStats = data;
        state.teamSubscriptionChecked = true;
        render();
      })
      .catch(function (err) {
        state.teamExtendedStats = null; // 402 (нет подписки) или любая другая ошибка — не блокируем профиль
        state.teamSubscriptionChecked = true;
        render();
      });
  }

  function subscribeTeamAction() {
    if (state.teamSubscribeBusy || !state.myTeam) return;
    state.teamSubscribeBusy = true;
    render();
    apiFetch("/community/teams/" + state.myTeam.id + "/subscribe/", { method: "POST" })
      .then(function (data) {
        state.teamSubscribeBusy = false;
        if (data.payment_redirect_url) {
          showToast("Переходим к оплате подписки...");
          window.location.href = data.payment_redirect_url;
          return;
        }
        showToast("Подписка оформлена!");
        checkTeamSubscription(state.myTeam.id);
      })
      .catch(function (err) {
        state.teamSubscribeBusy = false;
        render();
        showToast(err.message || "Не удалось оформить подписку.");
      });
  }

  function createTeamSubmit(name, district) {
    if (!name || state.teamCreateBusy) return;
    state.teamCreateBusy = true;
    state.teamCreateError = "";
    render();
    apiFetch("/teams/", { method: "POST", body: { name: name, district: district || "" } })
      .then(function (team) {
        state.teamCreateBusy = false;
        state.myTeam = team;
        state.teamMembers = [];
        state.teamMatches = [];
        render();
      })
      .catch(function (err) {
        state.teamCreateBusy = false;
        state.teamCreateError = err.message;
        render();
      });
  }

  function searchTeams(query) {
    state.teamSearchQuery = query;
    if (!query) {
      state.teamSearchResults = [];
      state.teamSearchLoading = false;
      render();
      return;
    }
    state.teamSearchLoading = true;
    render();
    apiFetch("/teams/?search=" + encodeURIComponent(query))
      .then(function (data) {
        state.teamSearchResults = asArray(data);
        state.teamSearchLoading = false;
        render();
      })
      .catch(function () {
        state.teamSearchLoading = false;
        render();
      });
  }

  function joinTeamAction(teamId) {
    if (state.teamJoinBusyId) return;
    state.teamJoinBusyId = teamId;
    render();
    apiFetch("/teams/" + teamId + "/join/", { method: "POST" })
      .then(function (team) {
        state.teamJoinBusyId = null;
        state.myTeam = team;
        state.teamSearchQuery = "";
        state.teamSearchResults = [];
        return loadTeamMembersAndMatches(team.id);
      })
      .then(function () {
        render();
        showToast("Вы вступили в «" + state.myTeam.name + "»!");
      })
      .catch(function (err) {
        state.teamJoinBusyId = null;
        render();
        showToast(err.message || "Не удалось вступить в команду.");
      });
  }

  function leaveTeamAction() {
    if (!state.myTeam) return;
    if (!confirm("Выйти из команды «" + state.myTeam.name + "»?")) return;
    apiFetch("/teams/" + state.myTeam.id + "/leave/", { method: "POST" })
      .then(function () {
        state.myTeam = null;
        state.teamMembers = [];
        state.teamMatches = [];
        render();
        showToast("Вы вышли из команды.");
      })
      .catch(function (err) {
        showToast(err.message || "Не удалось выйти из команды.");
      });
  }

  function openChallengePicker() {
    if (!state.myTeam) return;
    state.challengePickerOpen = true;
    state.challengeCandidatesLoading = true;
    state.challengeCandidates = [];
    render();
    apiFetch("/teams/")
      .then(function (data) {
        var myId = state.myTeam.id;
        state.challengeCandidates = asArray(data).filter(function (t) { return t.id !== myId; });
        state.challengeCandidatesLoading = false;
        render();
      })
      .catch(function (err) {
        state.challengeCandidatesLoading = false;
        render();
        showToast(err.message || "Не удалось загрузить список команд.");
      });
  }

  function closeChallengePicker() {
    state.challengePickerOpen = false;
    render();
  }

  function sendChallenge(opponentTeamId) {
    if (state.challengeBusy || !state.myTeam) return;
    state.challengeBusy = true;
    render();
    apiFetch("/community/challenges/", {
      method: "POST",
      body: { challenger_team: state.myTeam.id, opponent_team: opponentTeamId }
    })
      .then(function () {
        state.challengeBusy = false;
        state.challengePickerOpen = false;
        render();
        showToast("Вызов отправлен!");
      })
      .catch(function (err) {
        state.challengeBusy = false;
        render();
        showToast(err.message || "Не удалось отправить вызов.");
      });
  }

  // Подгружает state.myTeam (+ состав/матчи), если ещё не загружена в этой
  // сессии — используется везде, где нужна "моя команда", но экран мог быть
  // открыт напрямую, минуя вкладку "Команда".
  function ensureMyTeamLoaded() {
    if (state.myTeam) return Promise.resolve();
    return apiFetch("/teams/?mine=true").then(function (data) {
      var teams = asArray(data);
      if (teams.length) {
        state.myTeam = teams[0];
        return loadTeamMembersAndMatches(teams[0].id);
      }
    });
  }

  // ---- actions: activity feed (Feed.dc.html) -----------------------------

  function loadFeed() {
    state.feedLoading = true;
    render();

    ensureMyTeamLoaded()
      .then(function () {
        return Promise.all([
          apiFetch("/community/feed/"),
          apiFetch("/community/challenges/"),
          apiFetch("/community/news/")
        ]);
      })
      .then(function (results) {
        var events = asArray(results[0]);
        var challenges = asArray(results[1]);
        var news = asArray(results[2]);
        var myTeamId = state.myTeam ? state.myTeam.id : null;

        var items = [];

        events.forEach(function (e) {
          if (e.event_type === "challenge_received") return; // покажем как actionable-карточку ниже, не дублируем
          items.push({ kind: "event", ts: e.created_at, data: e });
        });

        challenges
          .filter(function (c) { return c.status === "pending" && c.opponent_team === myTeamId; })
          .forEach(function (c) { items.push({ kind: "challenge", ts: c.created_at, data: c }); });

        state.teamMatches.slice(0, 3).forEach(function (m) {
          items.push({ kind: "match", ts: m.played_at || m.created_at, data: m });
        });

        news.forEach(function (n) { items.push({ kind: "news", ts: n.published_at, data: n }); });

        items.sort(function (a, b) { return new Date(b.ts) - new Date(a.ts); });

        state.feedItems = items;
        state.feedLoading = false;
        render();
      })
      .catch(function (err) {
        if (err.status === 401) return logout();
        state.feedLoading = false;
        render();
        showToast(err.message || "Не удалось загрузить ленту.");
      });
  }

  function respondToChallenge(challengeId, action) {
    apiFetch("/community/challenges/" + challengeId + "/" + action + "/", { method: "POST" })
      .then(function () {
        showToast(action === "accept" ? "Вызов принят!" : "Вызов отклонён.");
        loadFeed();
      })
      .catch(function (err) {
        showToast(err.message || "Не удалось обработать вызов.");
      });
  }

  // ---- event binding ----------------------------------------------------

  function bind() {
    if (state.view === "login-phone") {
      var phoneInput = document.getElementById("phone-input");
      phoneInput.addEventListener("input", function (e) { state.phone = e.target.value; });
      phoneInput.addEventListener("keydown", function (e) { if (e.key === "Enter") requestOtp(); });
      document.getElementById("request-otp-btn").addEventListener("click", requestOtp);
    }

    if (state.view === "login-code") {
      document.getElementById("back-to-phone").addEventListener("click", function () {
        state.view = "login-phone";
        state.authError = "";
        render();
      });
      var codeInput = document.getElementById("otp-code-input");
      codeInput.addEventListener("input", function (e) {
        var v = e.target.value.replace(/\D/g, "").slice(0, 6);
        state.otpCode = v;
        e.target.value = v;
        if (v.length === 6) verifyOtp();
      });
      codeInput.addEventListener("keydown", function (e) { if (e.key === "Enter") verifyOtp(); });
      codeInput.focus();
      document.getElementById("verify-otp-btn").addEventListener("click", verifyOtp);
      document.getElementById("resend-otp-btn").addEventListener("click", requestOtp);
    }

    if (state.view === "main") {
      document.getElementById("logout-btn").addEventListener("click", logout);
      document.getElementById("my-bookings-btn").addEventListener("click", function () {
        state.view = "my-bookings";
        render();
        loadMyBookings();
      });
      bindScrollFade(document.querySelector(".filters-row-wrap"), document.querySelector(".filters-row"));

      document.getElementById("time-select-trigger").addEventListener("click", function () {
        state.timeSheetOpen = true;
        render();
      });

      if (state.timeSheetOpen) {
        document.getElementById("time-sheet-backdrop").addEventListener("click", function (e) {
          if (e.target.id === "time-sheet-backdrop") {
            state.timeSheetOpen = false;
            render();
          }
        });
        document.getElementById("sheet-close-btn").addEventListener("click", function () {
          state.timeSheetOpen = false;
          render();
        });
        document.querySelectorAll("[data-sheet-day]").forEach(function (el) {
          el.addEventListener("click", function () {
            var offset = parseInt(el.getAttribute("data-sheet-day"), 10);
            state.dateOffset = offset;
            state.customDateParts = null;
            state.hour = defaultHour(offset);
            render();
            loadVenues();
          });
        });
        document.getElementById("sheet-custom-date").addEventListener("change", function (e) {
          if (!e.target.value) return;
          var parts = inputValueToDateParts(e.target.value);
          state.dateOffset = -1;
          state.customDateParts = parts;
          state.hour = defaultHourForParts(parts);
          render();
          loadVenues();
        });
        document.querySelectorAll("[data-sheet-hour]").forEach(function (el) {
          el.addEventListener("click", function () {
            state.hour = parseInt(el.getAttribute("data-sheet-hour"), 10);
            state.timeSheetOpen = false;
            render();
            loadVenues();
          });
        });
      }

      document.getElementById("filter-district").addEventListener("change", function (e) {
        state.filters.district = e.target.value;
        loadVenues();
      });
      document.getElementById("filter-surface").addEventListener("change", function (e) {
        state.filters.surface_type = e.target.value;
        loadVenues();
      });
      document.getElementById("filter-size").addEventListener("change", function (e) {
        state.filters.field_size = e.target.value;
        loadVenues();
      });
      document.getElementById("filter-price").addEventListener("change", function (e) {
        state.filters.price_max = e.target.value;
        loadVenues();
      });
      document.querySelectorAll(".book-btn").forEach(function (el) {
        el.addEventListener("click", function () {
          bookVenue(parseInt(el.getAttribute("data-venue-id"), 10));
        });
      });
      bindBottomNav();
    }

    if (state.view === "confirm") {
      document.getElementById("confirm-close-btn").addEventListener("click", function () {
        if (confirm("Вернуться к поиску? Бронь останется активной — администратор всё равно её обработает, а результат будет виден в списке ваших броней.")) {
          stopBookingWatch();
          state.booking = null;
          state.view = "main";
          render();
          loadVenues();
        }
      });
    }

    if (state.view === "result") {
      document.getElementById("result-done-btn").addEventListener("click", function () {
        state.booking = null;
        state.resolution = null;
        state.view = "main";
        render();
        loadVenues();
      });
    }

    if (state.view === "team") {
      document.getElementById("team-back-btn").addEventListener("click", function () {
        state.view = "main";
        render();
        loadVenues();
      });
      bindBottomNav();

      if (!state.myTeam && !state.teamLoading) {
        document.getElementById("team-create-btn").addEventListener("click", function () {
          var name = document.getElementById("team-name-input").value.trim();
          var district = document.getElementById("team-district-input").value;
          createTeamSubmit(name, district);
        });
        var searchEl = document.getElementById("team-search-input");
        var searchTimer = null;
        searchEl.addEventListener("input", function (e) {
          var q = e.target.value;
          clearTimeout(searchTimer);
          searchTimer = setTimeout(function () { searchTeams(q); }, 400);
        });
        document.querySelectorAll(".team-join-btn").forEach(function (el) {
          el.addEventListener("click", function () { joinTeamAction(parseInt(el.getAttribute("data-team-id"), 10)); });
        });
      }

      var leaveBtn = document.getElementById("team-leave-btn");
      if (leaveBtn) {
        leaveBtn.addEventListener("click", leaveTeamAction);
        document.getElementById("team-challenge-btn").addEventListener("click", openChallengePicker);
        document.getElementById("team-invite-btn").addEventListener("click", function () {
          state.inviteInfoOpen = true;
          render();
        });
      }
      var subscribeBtn = document.getElementById("team-subscribe-btn");
      if (subscribeBtn) subscribeBtn.addEventListener("click", subscribeTeamAction);
      var statsToggle = document.getElementById("team-stats-toggle");
      if (statsToggle) {
        statsToggle.addEventListener("click", function () {
          state.teamStatsExpanded = !state.teamStatsExpanded;
          render();
        });
      }
    }

    if (state.view === "feed") {
      bindBottomNav();
      document.querySelectorAll(".challenge-accept-btn").forEach(function (el) {
        el.addEventListener("click", function () { respondToChallenge(el.getAttribute("data-challenge-id"), "accept"); });
      });
      document.querySelectorAll(".challenge-decline-btn").forEach(function (el) {
        el.addEventListener("click", function () { respondToChallenge(el.getAttribute("data-challenge-id"), "decline"); });
      });
    }

    if (state.view === "my-bookings") {
      document.getElementById("my-bookings-back-btn").addEventListener("click", function () {
        state.view = "main";
        render();
        loadVenues();
      });
      var emptySearchBtn = document.getElementById("my-bookings-empty-search-btn");
      if (emptySearchBtn) {
        emptySearchBtn.addEventListener("click", function () {
          state.view = "main";
          render();
          loadVenues();
        });
      }
      document.querySelectorAll(".my-booking-card[data-booking-id]").forEach(function (el) {
        el.addEventListener("click", function () {
          var id = parseInt(el.getAttribute("data-booking-id"), 10);
          var b = state.myBookingsList.find(function (x) { return x.id === id; });
          if (b) openBookingFromList(b);
        });
      });
    }

    if (state.view === "tournaments") {
      bindBottomNav();
      document.getElementById("tournament-create-btn").addEventListener("click", function () {
        state.tournamentCreateOpen = true;
        render();
      });
      var emptyCreateBtn = document.getElementById("tournament-empty-create-btn");
      if (emptyCreateBtn) {
        emptyCreateBtn.addEventListener("click", function () {
          state.tournamentCreateOpen = true;
          render();
        });
      }
      document.querySelectorAll(".tournament-card[data-tournament-id]").forEach(function (el) {
        el.addEventListener("click", function () {
          openTournamentDetail(parseInt(el.getAttribute("data-tournament-id"), 10));
        });
      });
    }

    if (state.view === "tournament-detail") {
      document.getElementById("tournament-detail-back-btn").addEventListener("click", function () {
        state.view = "tournaments";
        render();
        loadTournaments();
      });
      var regBtn = document.getElementById("tournament-register-btn");
      if (regBtn) regBtn.addEventListener("click", registerMyTeamForTournament);
      var cancelRegBtn = document.getElementById("tournament-cancel-reg-btn");
      if (cancelRegBtn) {
        cancelRegBtn.addEventListener("click", function () {
          if (!state.myTeam) return;
          var myReg = state.tournamentRegistrations.find(function (r) { return r.team === state.myTeam.id && r.status === "registered"; });
          if (myReg) cancelMyTournamentRegistration(myReg.id);
        });
      }
    }

    if (state.tournamentCreateOpen) {
      document.getElementById("tournament-create-backdrop").addEventListener("click", function (e) {
        if (e.target.id === "tournament-create-backdrop") { state.tournamentCreateOpen = false; render(); }
      });
      document.getElementById("tournament-create-close").addEventListener("click", function () {
        state.tournamentCreateOpen = false;
        render();
      });
      document.getElementById("tournament-create-submit-btn").addEventListener("click", function () {
        var name = document.getElementById("tournament-name-input").value.trim();
        var sponsor = document.getElementById("tournament-sponsor-input").value.trim();
        var fee = document.getElementById("tournament-fee-input").value;
        var minTeams = document.getElementById("tournament-min-input").value;
        var maxTeams = document.getElementById("tournament-max-input").value;
        var deadlineLocal = document.getElementById("tournament-deadline-input").value;
        if (!name || !fee || !deadlineLocal) {
          state.tournamentCreateError = "Заполните название, взнос и дедлайн.";
          render();
          return;
        }
        submitTournamentCreate({
          name: name,
          sponsor_name: sponsor,
          entry_fee: fee,
          min_teams: minTeams ? parseInt(minTeams, 10) : 4,
          max_teams: maxTeams ? parseInt(maxTeams, 10) : null,
          registration_deadline: new Date(deadlineLocal).toISOString()
        });
      });
    }

    // Шторка выбора соперника для вызова — может появиться поверх экрана команды.
    if (state.challengePickerOpen) {
      document.getElementById("challenge-picker-backdrop").addEventListener("click", function (e) {
        if (e.target.id === "challenge-picker-backdrop") closeChallengePicker();
      });
      document.getElementById("challenge-picker-close").addEventListener("click", closeChallengePicker);
      document.querySelectorAll(".challenge-candidate").forEach(function (el) {
        el.addEventListener("click", function () { sendChallenge(parseInt(el.getAttribute("data-team-id"), 10)); });
      });
    }

    if (state.inviteInfoOpen) {
      document.getElementById("invite-info-backdrop").addEventListener("click", function (e) {
        if (e.target.id === "invite-info-backdrop") { state.inviteInfoOpen = false; render(); }
      });
      document.getElementById("invite-info-close").addEventListener("click", function () {
        state.inviteInfoOpen = false;
        render();
      });
      document.getElementById("invite-copy-name-btn").addEventListener("click", function () {
        var name = state.myTeam ? state.myTeam.name : "";
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(name).then(function () {
            showToast("Скопировано: " + name);
          }).catch(function () {
            showToast("Не удалось скопировать — название: " + name);
          });
        } else {
          showToast("Название команды: " + name);
        }
      });
    }

    // Оверлей продления игры — может появиться поверх любого экрана, поэтому
    // биндится отдельно от per-view блоков выше.
    if (state.extensionOffer) {
      document.getElementById("ext-confirm-btn").addEventListener("click", function () { resolveExtensionOffer("confirm"); });
      document.getElementById("ext-decline-btn").addEventListener("click", function () { resolveExtensionOffer("decline"); });
    }
  }

  // ---- actions: auth ------------------------------------------------

  function requestOtp() {
    if (!state.phone || state.authBusy) return;
    state.authBusy = true;
    state.authError = "";
    render();
    apiFetch("/auth/otp/request/", { method: "POST", auth: false, body: { phone: state.phone } })
      .then(function () {
        state.authBusy = false;
        state.otpCode = "";
        state.view = "login-code";
        render();
        showToast("Код отправлен (в dev — смотрите консоль сервера)");
      })
      .catch(function (err) {
        state.authBusy = false;
        state.authError = err.message;
        render();
      });
  }

  function verifyOtp() {
    if (state.authBusy) return;
    var code = state.otpCode;
    if (code.length !== 6) return;
    state.authBusy = true;
    state.authError = "";
    render();
    apiFetch("/auth/otp/verify/", { method: "POST", auth: false, body: { phone: state.phone, code: code } })
      .then(function (data) {
        state.token = data.token;
        localStorage.setItem(STORAGE_KEY, data.token);
        state.authBusy = false;
        state.view = "main";
        render();
        loadVenues();
        startExtensionWatch();
        initPushNotifications();
      })
      .catch(function (err) {
        state.authBusy = false;
        state.authError = err.message;
        state.otpCode = "";
        render();
      });
  }

  function logout() {
    if (!confirm("Выйти из аккаунта?")) return;
    stopBookingWatch();
    stopExtensionWatch();
    state.extensionOffer = null;
    state.challengePickerOpen = false;
    state.inviteInfoOpen = false;
    state.timeSheetOpen = false;
    state.myTeam = null;
    state.teamSubscriptionChecked = false;
    state.teamExtendedStats = null;
    state.teamStatsExpanded = false;
    state.token = null;
    localStorage.removeItem(STORAGE_KEY);
    state.view = "login-phone";
    state.phone = "";
    state.venues = [];
    state.dateOffset = 0;
    state.customDateParts = null;
    state.hour = defaultHour(0);
    render();
  }

  // ---- actions: search / booking -----------------------------------

  function loadMyBookings() {
    state.myBookingsLoading = true;
    render();
    apiFetch("/bookings/")
      .then(function (data) {
        state.myBookingsList = asArray(data);
        state.myBookingsLoading = false;
        render();
      })
      .catch(function (err) {
        if (err.status === 401) return logout();
        state.myBookingsLoading = false;
        render();
        showToast(err.message || "Не удалось загрузить брони.");
      });
  }

  function openBookingFromList(b) {
    if (b.status !== "pending_confirmation" && b.status !== "extension_pending") return;
    state.booking = b;
    state.view = "confirm";
    render();
    startBookingWatch();
  }

  // ---- actions: tournaments -----------------------------------------

  function loadTournaments() {
    state.tournamentsLoading = true;
    render();
    apiFetch("/tournaments/")
      .then(function (data) {
        state.tournamentsList = asArray(data);
        state.tournamentsLoading = false;
        render();
      })
      .catch(function (err) {
        if (err.status === 401) return logout();
        state.tournamentsLoading = false;
        render();
        showToast(err.message || "Не удалось загрузить турниры.");
      });
  }

  function openTournamentDetail(id) {
    state.view = "tournament-detail";
    state.tournamentDetailLoading = true;
    state.tournamentDetail = null;
    render();

    ensureMyTeamLoaded()
      .then(function () {
        return Promise.all([
          apiFetch("/tournaments/" + id + "/"),
          apiFetch("/tournaments/" + id + "/registrations/"),
          apiFetch("/tournaments/" + id + "/standings/"),
          apiFetch("/tournaments/" + id + "/matches/")
        ]);
      })
      .then(function (results) {
        state.tournamentDetail = results[0];
        state.tournamentRegistrations = asArray(results[1]);
        state.tournamentStandings = asArray(results[2]);
        state.tournamentMatches = asArray(results[3]);
        state.tournamentDetailLoading = false;
        render();
      })
      .catch(function (err) {
        if (err.status === 401) return logout();
        state.tournamentDetailLoading = false;
        render();
        showToast(err.message || "Не удалось загрузить турнир.");
      });
  }

  function submitTournamentCreate(payload) {
    if (state.tournamentCreateBusy) return;
    state.tournamentCreateBusy = true;
    state.tournamentCreateError = "";
    render();
    apiFetch("/tournaments/", { method: "POST", body: payload })
      .then(function () {
        state.tournamentCreateBusy = false;
        state.tournamentCreateOpen = false;
        render();
        loadTournaments();
      })
      .catch(function (err) {
        state.tournamentCreateBusy = false;
        state.tournamentCreateError = err.message;
        render();
      });
  }

  function registerMyTeamForTournament() {
    if (state.tournamentRegisterBusy || !state.myTeam || !state.tournamentDetail) return;
    state.tournamentRegisterBusy = true;
    render();
    apiFetch("/tournaments/" + state.tournamentDetail.id + "/registrations/", {
      method: "POST",
      body: { team: state.myTeam.id }
    })
      .then(function () {
        state.tournamentRegisterBusy = false;
        showToast("Команда зарегистрирована!");
        openTournamentDetail(state.tournamentDetail.id);
      })
      .catch(function (err) {
        state.tournamentRegisterBusy = false;
        render();
        showToast(err.message || "Не удалось зарегистрироваться.");
      });
  }

  function cancelMyTournamentRegistration(registrationId) {
    if (!confirm("Отменить регистрацию на турнир? Взнос вернётся.")) return;
    apiFetch("/tournaments/registrations/" + registrationId + "/cancel/", { method: "POST" })
      .then(function () {
        showToast("Регистрация отменена, взнос возвращён.");
        openTournamentDetail(state.tournamentDetail.id);
      })
      .catch(function (err) {
        showToast(err.message || "Не удалось отменить регистрацию.");
      });
  }

  function loadVenues() {
    var parts = selectedDateParts();
    var start = isoFromBishkek(parts, state.hour);
    var end = isoFromBishkek(parts, state.hour + 1);

    var qs = new URLSearchParams();
    qs.set("start", start);
    qs.set("end", end);
    if (state.filters.district) qs.set("district", state.filters.district);
    if (state.filters.surface_type) qs.set("surface_type", state.filters.surface_type);
    if (state.filters.field_size) qs.set("field_size", state.filters.field_size);
    if (state.filters.price_max) qs.set("price_max", state.filters.price_max);

    state.venuesLoading = true;
    state.venuesError = "";
    render();

    apiFetch("/venues/available/?" + qs.toString())
      .then(function (data) {
        state.venues = Array.isArray(data) ? data : (data.results || []);
        state.venuesLoading = false;
        render();
      })
      .catch(function (err) {
        if (err.status === 401) return logout();
        state.venuesLoading = false;
        state.venuesError = err.message;
        render();
      });
  }

  function bookVenue(venueId) {
    var parts = selectedDateParts();
    var start = isoFromBishkek(parts, state.hour);
    var end = isoFromBishkek(parts, state.hour + 1);

    state.bookingBusyVenueId = venueId;
    render();

    apiFetch("/bookings/create/", { method: "POST", body: { venue: venueId, start_time: start, end_time: end } })
      .then(function (data) {
        state.bookingBusyVenueId = null;
        if (data.payment_redirect_url) {
          showToast("Переходим к оплате задатка...");
          window.location.href = data.payment_redirect_url;
          return;
        }
        state.booking = data;
        state.view = "confirm";
        render();
        startBookingWatch();
      })
      .catch(function (err) {
        state.bookingBusyVenueId = null;
        if (err.status === 401) return logout();
        if (err.status === 409) {
          showToast(err.message || "Этот слот только что забронировали.");
          loadVenues();
          return;
        }
        showToast(err.message || "Не удалось создать бронь.");
        render();
      });
  }

  function startBookingWatch() {
    stopBookingWatch();
    state.tickHandle = setInterval(function () {
      if (state.view === "confirm") render();
    }, 1000);
    state.pollHandle = setInterval(pollBookingStatus, 4000);
  }

  function stopBookingWatch() {
    if (state.tickHandle) clearInterval(state.tickHandle);
    if (state.pollHandle) clearInterval(state.pollHandle);
    state.tickHandle = null;
    state.pollHandle = null;
  }

  function pollBookingStatus() {
    if (!state.booking) return;
    apiFetch("/bookings/")
      .then(function (list) {
        var found = (list || []).find(function (b) { return b.id === state.booking.id; });
        if (!found) return;
        state.booking = found;
        if (found.status === "confirmed") {
          stopBookingWatch();
          state.resolution = "confirmed";
          state.view = "result";
          render();
        } else if (found.status !== "pending_confirmation" && found.status !== "extension_pending") {
          // declined / expired / cancelled — единый месседж клиенту (roadmap 8, вопрос 1)
          stopBookingWatch();
          state.resolution = "unavailable";
          state.view = "result";
          render();
        }
      })
      .catch(function (err) {
        if (err.status === 401) { stopBookingWatch(); logout(); }
      });
  }

  // ---- utils ----------------------------------------------------------

  // wrapEl — не скроллящаяся обёртка с классом .fade-wrap (тень всегда у её
  // краёв); scrollEl — фактический overflow-x:auto элемент внутри неё.
  function bindScrollFade(wrapEl, scrollEl) {
    if (!wrapEl || !scrollEl) return;
    function update() {
      var maxScroll = scrollEl.scrollWidth - scrollEl.clientWidth;
      wrapEl.classList.toggle("can-scroll-left", scrollEl.scrollLeft > 4);
      wrapEl.classList.toggle("can-scroll-right", scrollEl.scrollLeft < maxScroll - 4);
    }
    scrollEl.addEventListener("scroll", update);
    update();
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function escapeAttr(s) { return escapeHtml(s); }

  // ---- boot -------------------------------------------------------------

  render();
  if (state.view === "main") {
    loadVenues();
    startExtensionWatch();
    initPushNotifications();
  }
})();
