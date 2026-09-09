"""
Реальная интеграция с FreedomPay Кыргызстан (карточный эквайринг с hold).

Проверено по официальной документации (2026-09-09):
https://freedompay.kg/docs/merchant-api/intro
https://freedompay.kg/docs/merchant-api/pay
https://freedompay.kg/docs/merchant-api/payafter

Протокол — классический PayBox-style: подписанные pg_*-параметры, XML-ответы.
Подтверждено документацией: `pg_auto_clearing=0` при инициации платежа даёт
двухфазный hold (авторизация без списания) — до 5 дней на решение — с
последующим `do_capture.php` (списать) или `cancel.php` (снять резерв).
Это и есть провайдер с hold в КР, который искал открытый вопрос 2 из
раздела 8 roadmap.

ВАЖНО, НЕ СДЕЛАНО (см. CLAUDE.md, "Реальные провайдеры" — прочитать перед
включением в проде):

1. **Не протестировано вживую.** Реальных merchant-credentials ещё нет —
   сигнатура и разбор ответов реализованы строго по документации, но без
   прогона через песочницу/боевой API. Перед первым реальным платежом —
   свериться с официальной Postman-коллекцией FreedomPay и тестовыми
   credentials.

2. **Архитектурный разрыв с синхронным flow — частично закрыт.** FreedomPay
   работает через редирект клиента на их платёжную страницу
   (`pg_redirect_url`) и асинхронное подтверждение через вебхук (Result
   URL), а не через мгновенное "списать с этой карты". Что уже сделано:
   `hold()` возвращает `redirect_url` в `PaymentResult`, он доходит до
   `BookingCreationResult.payment_redirect_url` и до тела HTTP-ответа
   `POST /api/bookings/create/`; если вебхук `.../result/` потом сообщает
   о неудаче — и бронь (`expire_booking()`), и регистрация на турнир
   (`cancel_registration_after_payment_failure()`) корректно освобождаются,
   а не зависают навсегда. Чего всё ещё нет — это продуктовое UX-решение,
   а не код: клиент физически не блокируется от использования приложения,
   пока не завершит оплату на странице FreedomPay (нет экрана/индикации
   "ждём подтверждения платежа"). Отдельно: `apps.community.subscribe_team`
   вообще не адаптирован под редирект — списывает синхронно сразу после
   `hold()`, без окна для этого вебхука в принципе; чтобы включить туда
   FreedomPay, её нужно переписать на ту же асинхронную схему, что и бронь.

Функции verify_signature/build_response ниже уже готовы для вебхуков
(apps/payments/views.py) — эта часть закончена независимо от пункта 2.
"""

import hashlib
import logging
import random
import string
from decimal import Decimal
from xml.etree import ElementTree

import requests
from django.conf import settings

from .providers import PaymentProvider, PaymentResult

logger = logging.getLogger(__name__)


class FreedomPayError(Exception):
    """Ошибка на стороне FreedomPay или сети — не удалось выполнить запрос."""


def _generate_salt(length: int = 20) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


def _sign(script_name: str, params: dict) -> str:
    """
    pg_sig = md5("script_name;value1;value2;...;valueN;secret_key"), где
    value1..N — значения параметров (без pg_sig), отсортированных по имени
    ключа. Проверено по документации intro (см. модуль docstring).
    """
    sorted_values = [str(params[key]) for key in sorted(params.keys()) if key != "pg_sig"]
    signature_string = ";".join([script_name, *sorted_values, settings.FREEDOMPAY_SECRET_KEY])
    return hashlib.md5(signature_string.encode("utf-8")).hexdigest()


def verify_signature(script_name: str, params: dict) -> bool:
    """Проверка подписи входящего запроса от FreedomPay (вебхуки check/result)."""
    incoming_sig = params.get("pg_sig", "")
    expected_sig = _sign(script_name, {k: v for k, v in params.items() if k != "pg_sig"})
    return incoming_sig == expected_sig


def build_xml_response(script_name: str, status: str, **extra_fields) -> str:
    """
    Ответ мерчанта на check/result-запросы FreedomPay — тоже подписанный XML.
    script_name: "check" | "result" (какому вебхуку отвечаем — влияет на
    подпись). status: "ok" | "rejected" | "error".
    """
    fields = {"pg_status": status, "pg_salt": _generate_salt(), **extra_fields}
    fields["pg_sig"] = _sign(script_name, fields)

    root = ElementTree.Element("response")
    for key, value in fields.items():
        ElementTree.SubElement(root, key).text = str(value)
    return ElementTree.tostring(root, encoding="unicode")


def _parse_xml_response(xml_text: str) -> dict:
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError as exc:
        raise FreedomPayError(f"Не удалось разобрать XML-ответ FreedomPay: {exc}") from exc
    return {child.tag: child.text for child in root}


def _post(script_name: str, params: dict) -> dict:
    signed_params = {**params, "pg_merchant_id": settings.FREEDOMPAY_MERCHANT_ID}
    signed_params["pg_sig"] = _sign(script_name, signed_params)

    url = f"{settings.FREEDOMPAY_BASE_URL.rstrip('/')}/{script_name}"
    try:
        response = requests.post(url, data=signed_params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise FreedomPayError(f"Ошибка сети при обращении к FreedomPay ({script_name}): {exc}") from exc

    return _parse_xml_response(response.text)


class FreedomPayProvider(PaymentProvider):
    """
    Стратегия — HOLD_CAPTURE: init_payment с pg_auto_clearing=0 резервирует
    (авторизует) деньги без списания, do_capture списывает, cancel снимает
    резерв. Настоящий hold, а не эмуляция — см. модуль docstring.
    """

    strategy = "hold_capture"

    def hold(self, *, reference: str, amount: Decimal) -> PaymentResult:
        try:
            data = _post(
                "init_payment.php",
                {
                    "pg_order_id": reference,
                    "pg_amount": str(amount),
                    "pg_description": "Задаток за бронирование — Футбол",
                    "pg_auto_clearing": "0",  # ключевой параметр: hold, а не мгновенное списание
                    "pg_salt": _generate_salt(),
                },
            )
        except FreedomPayError as exc:
            return PaymentResult(success=False, error=str(exc))

        if data.get("pg_status") != "ok":
            return PaymentResult(success=False, error=data.get("pg_error_description", "Неизвестная ошибка FreedomPay"))

        return PaymentResult(
            success=True,
            external_id=data.get("pg_payment_id", ""),
            redirect_url=data.get("pg_redirect_url", ""),
        )

    def capture(self, *, payment) -> PaymentResult:
        try:
            data = _post(
                "do_capture.php",
                {
                    "pg_payment_id": payment.external_id,
                    "pg_clearing_amount": str(payment.amount),
                    "pg_salt": _generate_salt(),
                },
            )
        except FreedomPayError as exc:
            return PaymentResult(success=False, error=str(exc))

        success = data.get("pg_status") == "ok"
        return PaymentResult(
            success=success,
            external_id=payment.external_id,
            error="" if success else data.get("pg_error_description", "Не удалось списать платёж"),
        )

    def release(self, *, payment) -> PaymentResult:
        # release() в apps.bookings/apps.tournaments вызывается только для
        # платежей в статусе HELD (ещё не списанных) — поэтому здесь всегда
        # cancel (снятие резерва), а не revoke (возврат уже списанного).
        try:
            data = _post(
                "cancel.php",
                {"pg_payment_id": payment.external_id, "pg_salt": _generate_salt()},
            )
        except FreedomPayError as exc:
            return PaymentResult(success=False, error=str(exc))

        success = data.get("pg_status") == "ok"
        return PaymentResult(
            success=success,
            external_id=payment.external_id,
            error="" if success else data.get("pg_error_description", "Не удалось снять резерв"),
        )
