"""
Кастомизация Django admin под редизайн (мокап Claude Design, 2026-09-10,
см. apps/frontend/static/admin/futbol_admin.css для полного докстринга):
- site_header/site_title
- порядок разделов в сайдбаре и на дашборде — по логике повседневной
  работы (площадки → брони → платежи → команды/турниры → комьюнити →
  служебное), а не алфавит, который Django даёт по умолчанию
- реальные цифры для карточек дашборда (templates/admin/index.html)

Подключается из apps/frontend/apps.py::FrontendConfig.ready() — apps.frontend
стоит ПОСЛЕДНИМ в INSTALLED_APPS, так что все 16 ModelAdmin по всем
apps/*/admin.py уже зарегистрированы на admin.site к этому моменту.
Патчим методы на самом синглтоне admin.site (через types.MethodType),
а не заводим отдельный AdminSite-подкласс — иначе пришлось бы переписывать
все существующие @admin.register(...) на новый сайт ради косметики.
"""

import types

from django.contrib import admin
from django.db.models import Sum
from django.utils import timezone

_APP_ORDER = [
    "venues",
    "bookings",
    "payments",
    "teams",
    "tournaments",
    "matchmaking",
    "community",
    "notifications",
    "accounts",
]


def _app_sort_key(app):
    label = app["app_label"]
    try:
        return (_APP_ORDER.index(label), app["name"].lower())
    except ValueError:
        return (len(_APP_ORDER), app["name"].lower())


def _get_app_list(self, request, app_label=None):
    app_list = admin.AdminSite.get_app_list(self, request, app_label)
    for app in app_list:
        app["models"].sort(key=lambda m: m["name"])
    app_list.sort(key=_app_sort_key)
    return app_list


def _dashboard_stats():
    from apps.bookings.models import Booking, BookingStatus
    from apps.payments.models import Payment, PaymentStatus
    from apps.venues.models import Venue

    today = timezone.localdate()
    now = timezone.now()

    pending = Booking.objects.filter(status=BookingStatus.PENDING_CONFIRMATION)
    confirmed_today = Booking.objects.filter(
        status=BookingStatus.CONFIRMED, confirmed_at__date=today
    ).count()
    created_today = Booking.objects.filter(created_at__date=today).count()

    today_captured = Payment.objects.filter(status=PaymentStatus.CAPTURED, settled_at__date=today)
    revenue_today = today_captured.aggregate(s=Sum("amount"))["s"] or 0
    commission_today = today_captured.aggregate(s=Sum("commission_amount"))["s"] or 0

    urgent_deadline = now + timezone.timedelta(minutes=15)
    urgent_bookings = list(
        pending.filter(confirmation_deadline__lte=urgent_deadline)
        .select_related("venue")
        .order_by("confirmation_deadline")[:5]
    )

    recent_bookings = list(
        Booking.objects.select_related("venue", "client").order_by("-created_at")[:6]
    )

    return {
        "pending_count": pending.count(),
        "created_today": created_today,
        "confirmed_today": confirmed_today,
        "revenue_today": revenue_today,
        "commission_today": commission_today,
        "active_venues": Venue.objects.filter(is_active=True).count(),
        "urgent_bookings": urgent_bookings,
        "failed_payments": Payment.objects.filter(status=PaymentStatus.FAILED).count(),
        "recent_bookings": recent_bookings,
    }


def _index(self, request, extra_context=None):
    extra_context = extra_context or {}
    extra_context["futbol_stats"] = _dashboard_stats()
    return admin.AdminSite.index(self, request, extra_context)


def install():
    admin.site.site_header = "Футбол — администрирование"
    admin.site.site_title = "Футбол admin"
    admin.site.index_title = "Дашборд"
    admin.site.get_app_list = types.MethodType(_get_app_list, admin.site)
    admin.site.index = types.MethodType(_index, admin.site)
