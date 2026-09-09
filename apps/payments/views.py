"""
Вебхуки FreedomPay (check/result) — см. apps/payments/freedompay.py про то,
чего здесь ещё не хватает для полного включения в проде (redirect-flow).

Без DRF-аутентификации: FreedomPay — внешний сервис, доверие строится на
проверке подписи (pg_sig), а не на токене пользователя.
"""

import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .freedompay import build_xml_response, verify_signature
from .models import Payment, PaymentStatus

logger = logging.getLogger(__name__)


def _find_payment_by_order_id(pg_order_id: str) -> Payment | None:
    """
    Наш `reference` (см. apps.bookings/apps.tournaments) — "booking-<id>"
    или "tournament-entry-<id>", он же передаётся в FreedomPay как pg_order_id.
    """
    if pg_order_id.startswith("booking-"):
        return Payment.objects.filter(booking_id=pg_order_id.removeprefix("booking-")).first()
    if pg_order_id.startswith("tournament-entry-"):
        return Payment.objects.filter(
            tournament_registration_id=pg_order_id.removeprefix("tournament-entry-")
        ).first()
    return None


@csrf_exempt
@require_POST
def freedompay_check(request):
    params = request.POST.dict()
    if not verify_signature("check", params):
        logger.warning("FreedomPay check: неверная подпись, pg_order_id=%s", params.get("pg_order_id"))
        return HttpResponse(
            build_xml_response("check", "error", pg_description="Неверная подпись"),
            content_type="application/xml",
        )

    payment = _find_payment_by_order_id(params.get("pg_order_id", ""))
    if payment is None:
        return HttpResponse(
            build_xml_response("check", "rejected", pg_description="Заказ не найден"),
            content_type="application/xml",
        )
    if payment.status != PaymentStatus.HELD:
        return HttpResponse(
            build_xml_response("check", "rejected", pg_description="Заказ уже обработан"),
            content_type="application/xml",
        )

    return HttpResponse(build_xml_response("check", "ok"), content_type="application/xml")


@csrf_exempt
@require_POST
def freedompay_result(request):
    """
    При неуспехе (pg_result != "1") — помечаем Payment как FAILED и
    освобождаем то, под что резервировались деньги: для брони —
    expire_booking(), для взноса за турнир —
    cancel_registration_after_payment_failure() (тот же безопасный
    идемпотентный путь, что и таймаут подтверждения/закрытие регистрации).
    Для подписки команды (apps.community) — эквивалента пока нет:
    subscribe_team() списывает синхронно сразу после hold(), не оставляя
    окна для этого вебхука в принципе; чтобы реально работать с редиректом
    FreedomPay, её ещё нужно переписать на ту же асинхронную схему, что и
    бронь (см. apps/payments/freedompay.py, пункт 2 — продуктовое решение
    по UX всего redirect-flow, не только код).
    """
    params = request.POST.dict()
    if not verify_signature("result", params):
        logger.warning("FreedomPay result: неверная подпись, pg_order_id=%s", params.get("pg_order_id"))
        return HttpResponse(
            build_xml_response("result", "error", pg_description="Неверная подпись"),
            content_type="application/xml",
        )

    payment = _find_payment_by_order_id(params.get("pg_order_id", ""))
    if payment is None:
        return HttpResponse(
            build_xml_response("result", "rejected", pg_description="Заказ не найден"),
            content_type="application/xml",
        )

    pg_payment_id = params.get("pg_payment_id", "")
    if pg_payment_id:
        payment.external_id = pg_payment_id

    if params.get("pg_result") == "1":
        logger.info("FreedomPay result: платёж %s подтверждён (hold успешен)", pg_payment_id)
        payment.save(update_fields=["external_id"])
    else:
        payment.status = PaymentStatus.FAILED
        payment.save(update_fields=["external_id", "status"])
        logger.error(
            "FreedomPay result: платёж %s не удался (pg_result=%s), pg_order_id=%s",
            pg_payment_id,
            params.get("pg_result"),
            params.get("pg_order_id"),
        )
        if payment.booking_id:
            from apps.bookings.services import expire_booking

            expire_booking(payment.booking_id)
        elif payment.tournament_registration_id:
            from apps.tournaments.services import cancel_registration_after_payment_failure

            cancel_registration_after_payment_failure(payment.tournament_registration_id)

    return HttpResponse(build_xml_response("result", "ok"), content_type="application/xml")
