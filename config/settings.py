"""
Django settings for config project (MVP — Этап 1, см. CLAUDE.md и
football-app-roadmap.md).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me")
DEBUG = env_bool("DJANGO_DEBUG", True)
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.postgres",
    "rest_framework",
    "rest_framework.authtoken",
    "django_filters",
    "apps.accounts",
    "apps.venues",
    "apps.bookings",
    "apps.payments",
    "apps.notifications",
    "apps.teams",
    "apps.matchmaking",
    "apps.tournaments",
    "apps.community",
    "apps.frontend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Без неё LANGUAGE_CODE="ru" не активируется надёжно на каждый запрос —
    # штатные строки Django admin (в т.ч. текст select2-виджетов у
    # autocomplete-полей, "Select an option") оставались английскими.
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        # Только BASE_DIR/templates/admin/ — оверрайды для редизайна Django
        # admin (apps/frontend/templates/ не годится: apps.frontend стоит
        # ПОСЛЕДНИМ в INSTALLED_APPS, а APP_DIRS ищет по порядку — раньше
        # нашёлся бы стандартный шаблон из django.contrib.admin. Отдельная
        # папка верхнего уровня в DIRS всегда проверяется первой.
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


# Database — Postgres обязателен: используем ExclusionConstraint (btree_gist)
# для защиты от двойного бронирования на уровне БД (apps/bookings/models.py).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "futbol"),
        "USER": os.environ.get("POSTGRES_USER", "futbol"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "futbol"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
    }
}

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization — Кыргызстан, продукт на русском.
LANGUAGE_CODE = "ru"
TIME_ZONE = "Asia/Bishkek"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Без этого apps.*.logger.info(...) (в т.ч. mock-провайдер уведомлений —
# "[MOCK SMS] -> +996...: Код для входа: ...") не долетал бы до консоли
# runserver: у Django по умолчанию настроены только django.* логгеры.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {"apps": {"handlers": ["console"], "level": "INFO", "propagate": False}},
}


REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}


# Celery — фоновые задачи для таймеров подтверждения/продления (roadmap 2.2, 2.3).
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_TRACK_STARTED = True


# Бизнес-параметры бронирования (roadmap 2.2, 2.3) — вынесены в settings,
# чтобы не хардкодить в бизнес-логике.
BOOKING_CONFIRMATION_TIMEOUT_MINUTES = int(os.environ.get("BOOKING_CONFIRMATION_TIMEOUT_MINUTES", 10))
BOOKING_CONFIRMATION_REMINDER_BEFORE_MINUTES = int(
    os.environ.get("BOOKING_CONFIRMATION_REMINDER_BEFORE_MINUTES", 2)
)
BOOKING_EXTENSION_PROMPT_BEFORE_MINUTES = int(os.environ.get("BOOKING_EXTENSION_PROMPT_BEFORE_MINUTES", 15))
BOOKING_EXTENSION_DURATION_MINUTES = int(os.environ.get("BOOKING_EXTENSION_DURATION_MINUTES", 60))

# Вход/регистрация по SMS-коду (без пароля) — см. apps/accounts.
OTP_TTL_MINUTES = int(os.environ.get("OTP_TTL_MINUTES", 5))
OTP_REQUEST_COOLDOWN_SECONDS = int(os.environ.get("OTP_REQUEST_COOLDOWN_SECONDS", 60))
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", 5))

# Монетизация (roadmap, раздел 3 и 4.1) — комиссия платформы. Пока нет
# реального платёжного провайдера, это только схема/расчёт для отчётности,
# без фактического перечисления денег площадкам/организаторам (payout).
DEFAULT_VENUE_COMMISSION_PERCENT = os.environ.get("DEFAULT_VENUE_COMMISSION_PERCENT", "10")
DEFAULT_TOURNAMENT_ORGANIZER_COMMISSION_PERCENT = os.environ.get(
    "DEFAULT_TOURNAMENT_ORGANIZER_COMMISSION_PERCENT", "12"
)

# Платёжная стратегия по умолчанию для новых площадок, пока не подтверждён
# провайдер с hold в КР (roadmap, раздел 8, вопрос 2). См. apps/payments.
DEFAULT_PAYMENT_STRATEGY = os.environ.get("DEFAULT_PAYMENT_STRATEGY", "charge_auto_refund")

# Задаток — процент от стоимости брони (roadmap 2.2 не фиксирует конкретную
# цифру, вынесено в settings, чтобы менять без правки кода).
BOOKING_DEPOSIT_PERCENT = int(os.environ.get("BOOKING_DEPOSIT_PERCENT", 30))


# Реальные провайдеры (roadmap, раздел 8, вопросы 2 и 4). Пусты по умолчанию
# — код падает обратно на mock-реализации (apps/payments/providers.py,
# apps/notifications/providers.py), пока не заданы настоящие ключи.

# FreedomPay Кыргызстан — см. apps/payments/freedompay.py. API проверен по
# официальной документации (freedompay.kg/docs/merchant-api), но НЕ
# протестирован вживую — реальных merchant-credentials ещё нет.
FREEDOMPAY_MERCHANT_ID = os.environ.get("FREEDOMPAY_MERCHANT_ID", "")
FREEDOMPAY_SECRET_KEY = os.environ.get("FREEDOMPAY_SECRET_KEY", "")
FREEDOMPAY_BASE_URL = os.environ.get("FREEDOMPAY_BASE_URL", "https://api.freedompay.kg")
FREEDOMPAY_RESULT_URL = os.environ.get("FREEDOMPAY_RESULT_URL", "")
FREEDOMPAY_CHECK_URL = os.environ.get("FREEDOMPAY_CHECK_URL", "")

# Firebase Cloud Messaging (push) — путь к service account JSON.
FIREBASE_CREDENTIALS_PATH = os.environ.get("FIREBASE_CREDENTIALS_PATH", "")

# Infobip (SMS + автозвонок/TTS) — см. apps/notifications/infobip.py.
INFOBIP_API_KEY = os.environ.get("INFOBIP_API_KEY", "")
INFOBIP_BASE_URL = os.environ.get("INFOBIP_BASE_URL", "")
INFOBIP_SENDER = os.environ.get("INFOBIP_SENDER", "FutbolApp")


# Этап 3 — удержание (roadmap, раздел 5 и 6). Пороги "званий" команды по
# очкам рейтинга (apps.teams.Team.rating_points) — косметика, легко менять.
TEAM_RANK_THRESHOLDS = [
    (0, "Новичок"),
    (10, "Любитель"),
    (30, "Крепкий середняк"),
    (60, "Профи"),
    (100, "Легенда двора"),
]

# Подписка команды (roadmap, раздел 3: "Подписка игроков/команд") — разовая
# оплата на фиксированный срок, не рекуррентный биллинг (см. docstring
# apps.community.models.TeamSubscription).
TEAM_SUBSCRIPTION_PRICE = os.environ.get("TEAM_SUBSCRIPTION_PRICE", "500")
TEAM_SUBSCRIPTION_DURATION_DAYS = int(os.environ.get("TEAM_SUBSCRIPTION_DURATION_DAYS", 30))
