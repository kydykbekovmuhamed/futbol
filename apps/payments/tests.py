"""
Реальных merchant-credentials FreedomPay нет — тесты не бьют по живому API,
а проверяют то, что можно проверить без него: детерминированность и
устойчивость к подделке подписи, правильность формы запроса (через мок
requests.post) и разбор XML-ответов. Это не замена прогону против
песочницы FreedomPay перед реальным запуском (см. apps/payments/freedompay.py).
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.bookings.models import Booking, BookingStatus
from apps.bookings.services import create_booking
from apps.teams.services import create_team as create_football_team
from apps.tournaments.models import RegistrationStatus
from apps.tournaments.services import create_tournament, register_team
from apps.venues.models import FieldSize, SurfaceType, Venue

from .freedompay import FreedomPayProvider, _sign, build_xml_response, verify_signature
from .models import Payment, PaymentStatus, PaymentStrategy
from .providers import MockChargeAutoRefundProvider, MockHoldCaptureProvider, get_payment_provider

FREEDOMPAY_SETTINGS = dict(
    FREEDOMPAY_MERCHANT_ID="test-merchant",
    FREEDOMPAY_SECRET_KEY="test-secret",
    FREEDOMPAY_BASE_URL="https://api.freedompay.kg",
)


class SignatureTests(TestCase):
    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_signature_is_deterministic(self):
        params = {"pg_order_id": "booking-1", "pg_amount": "300.00"}

        sig1 = _sign("init_payment.php", params)
        sig2 = _sign("init_payment.php", params)

        self.assertEqual(sig1, sig2)
        self.assertEqual(len(sig1), 32)  # md5 hex digest

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_signature_changes_with_params(self):
        sig_a = _sign("init_payment.php", {"pg_order_id": "booking-1", "pg_amount": "300.00"})
        sig_b = _sign("init_payment.php", {"pg_order_id": "booking-2", "pg_amount": "300.00"})

        self.assertNotEqual(sig_a, sig_b)

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_verify_signature_roundtrip(self):
        params = {"pg_order_id": "booking-1", "pg_amount": "300.00", "pg_result": "1"}
        params["pg_sig"] = _sign("result", params)

        self.assertTrue(verify_signature("result", params))

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_verify_signature_rejects_tampered_payload(self):
        params = {"pg_order_id": "booking-1", "pg_amount": "300.00", "pg_result": "1"}
        params["pg_sig"] = _sign("result", params)
        params["pg_amount"] = "999.00"  # злоумышленник подменил сумму после подписи

        self.assertFalse(verify_signature("result", params))

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_build_xml_response_is_self_verifiable(self):
        xml_text = build_xml_response("check", "ok")

        # Наш же собственный ответ должен проходить проверку той же подписью.
        import re

        fields = dict(re.findall(r"<(\w+)>([^<]*)</\1>", xml_text))
        self.assertTrue(verify_signature("check", fields))
        self.assertEqual(fields["pg_status"], "ok")


class FreedomPayProviderTests(TestCase):
    """Мокаем requests.post — проверяем форму запроса и разбор ответа, не сеть."""

    @override_settings(**FREEDOMPAY_SETTINGS)
    @patch("apps.payments.freedompay.requests.post")
    def test_hold_sends_auto_clearing_zero_and_parses_redirect(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200,
            text=(
                "<response><pg_status>ok</pg_status><pg_payment_id>777</pg_payment_id>"
                "<pg_redirect_url>https://pay.freedompay.kg/abc</pg_redirect_url></response>"
            ),
        )
        mock_post.return_value.raise_for_status = Mock()

        provider = FreedomPayProvider()
        result = provider.hold(reference="booking-1", amount=Decimal("300.00"))

        self.assertTrue(result.success)
        self.assertEqual(result.external_id, "777")
        self.assertEqual(result.redirect_url, "https://pay.freedompay.kg/abc")

        called_url, called_kwargs = mock_post.call_args[0][0], mock_post.call_args[1]
        self.assertTrue(called_url.endswith("/init_payment.php"))
        sent_data = called_kwargs["data"]
        self.assertEqual(sent_data["pg_auto_clearing"], "0")  # ключевое: hold, не мгновенное списание
        self.assertEqual(sent_data["pg_order_id"], "booking-1")
        self.assertIn("pg_sig", sent_data)

    @override_settings(**FREEDOMPAY_SETTINGS)
    @patch("apps.payments.freedompay.requests.post")
    def test_hold_failure_reported(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200,
            text="<response><pg_status>error</pg_status><pg_error_description>Карта отклонена</pg_error_description></response>",
        )
        mock_post.return_value.raise_for_status = Mock()

        provider = FreedomPayProvider()
        result = provider.hold(reference="booking-2", amount=Decimal("100.00"))

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Карта отклонена")

    @override_settings(**FREEDOMPAY_SETTINGS)
    @patch("apps.payments.freedompay.requests.post")
    def test_capture_uses_do_capture_endpoint(self, mock_post):
        mock_post.return_value = Mock(status_code=200, text="<response><pg_status>ok</pg_status></response>")
        mock_post.return_value.raise_for_status = Mock()

        payment = Mock(external_id="777", amount=Decimal("300.00"))
        result = FreedomPayProvider().capture(payment=payment)

        self.assertTrue(result.success)
        called_url = mock_post.call_args[0][0]
        self.assertTrue(called_url.endswith("/do_capture.php"))
        self.assertEqual(mock_post.call_args[1]["data"]["pg_payment_id"], "777")

    @override_settings(**FREEDOMPAY_SETTINGS)
    @patch("apps.payments.freedompay.requests.post")
    def test_release_uses_cancel_not_revoke(self, mock_post):
        """release() вызывается только для ещё не списанных (HELD) платежей — всегда cancel, не revoke."""
        mock_post.return_value = Mock(status_code=200, text="<response><pg_status>ok</pg_status></response>")
        mock_post.return_value.raise_for_status = Mock()

        payment = Mock(external_id="777")
        FreedomPayProvider().release(payment=payment)

        called_url = mock_post.call_args[0][0]
        self.assertTrue(called_url.endswith("/cancel.php"))

    @override_settings(**FREEDOMPAY_SETTINGS)
    @patch("apps.payments.freedompay.requests.post")
    def test_network_error_is_reported_not_raised(self, mock_post):
        import requests

        mock_post.side_effect = requests.ConnectionError("boom")

        result = FreedomPayProvider().hold(reference="booking-3", amount=Decimal("100.00"))

        self.assertFalse(result.success)
        self.assertIn("boom", result.error)


class ProviderSelectionTests(TestCase):
    def test_falls_back_to_mock_without_credentials(self):
        with override_settings(FREEDOMPAY_MERCHANT_ID="", FREEDOMPAY_SECRET_KEY=""):
            provider = get_payment_provider(PaymentStrategy.HOLD_CAPTURE)
        self.assertIsInstance(provider, MockHoldCaptureProvider)

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_uses_freedompay_when_configured(self):
        provider = get_payment_provider(PaymentStrategy.HOLD_CAPTURE)
        self.assertIsInstance(provider, FreedomPayProvider)

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_charge_auto_refund_never_uses_freedompay(self):
        """FreedomPay реализует только hold_capture — для charge_auto_refund всегда mock."""
        provider = get_payment_provider(PaymentStrategy.CHARGE_AUTO_REFUND)
        self.assertIsInstance(provider, MockChargeAutoRefundProvider)


class FreedomPayWebhookTests(TestCase):
    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_check_rejects_invalid_signature(self):
        response = self.client.post(
            "/api/payments/freedompay/check/", {"pg_order_id": "booking-1", "pg_sig": "wrong"}
        )
        self.assertIn(b"error", response.content)

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_check_rejects_unknown_order(self):
        params = {"pg_order_id": "booking-999999"}
        params["pg_sig"] = _sign("check", params)

        response = self.client.post("/api/payments/freedompay/check/", params)

        self.assertIn(b"rejected", response.content)

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_result_rejects_invalid_signature(self):
        response = self.client.post(
            "/api/payments/freedompay/result/",
            {"pg_order_id": "booking-1", "pg_result": "1", "pg_sig": "wrong"},
        )
        self.assertIn(b"error", response.content)

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_failed_result_expires_booking_and_frees_slot(self):
        """
        Раньше это было незакрытым архитектурным разрывом (см.
        apps/payments/freedompay.py): вебхук об асинхронной неудаче платежа
        только помечал Payment как FAILED, а бронь оставалась висеть
        навсегда, физически блокируя слот. Теперь неудача освобождает слот
        тем же путём, что и обычный таймаут подтверждения.
        """
        client_user = User.objects.create_user(phone="+996700900001", password="x")
        other_client = User.objects.create_user(phone="+996700900002", password="x")
        venue = Venue.objects.create(
            name="Арена вебхука", address="ул. Тест", surface_type=SurfaceType.TURF,
            field_size=FieldSize.SEVEN, price_per_hour=1000,
        )
        start = timezone.now() + timedelta(hours=2)
        end = start + timedelta(hours=1)
        result = create_booking(client=client_user, venue=venue, start_time=start, end_time=end)
        booking_id = result.booking.id

        params = {"pg_order_id": f"booking-{booking_id}", "pg_result": "0", "pg_payment_id": "fp-777"}
        params["pg_sig"] = _sign("result", params)

        response = self.client.post("/api/payments/freedompay/result/", params)

        self.assertIn(b"ok", response.content)
        booking = Booking.objects.get(pk=booking_id)
        self.assertEqual(booking.status, BookingStatus.EXPIRED)
        payment = Payment.objects.get(booking_id=booking_id)
        self.assertEqual(payment.status, PaymentStatus.FAILED)
        self.assertEqual(payment.external_id, "fp-777")

        # Слот реально свободен — новую бронь на тот же интервал можно создать.
        second = create_booking(client=other_client, venue=venue, start_time=start, end_time=end)
        self.assertEqual(second.booking.status, BookingStatus.PENDING_CONFIRMATION)

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_failed_result_does_not_double_release_already_settled_payment(self):
        """
        Защита в _settle_payment: если платёж уже не HELD (тут — FAILED от
        первого вызова вебхука), повторное срабатывание expire_booking не
        должно пытаться ещё раз звать provider.release().
        """
        client_user = User.objects.create_user(phone="+996700900003", password="x")
        venue = Venue.objects.create(
            name="Арена вебхука 2", address="ул. Тест 2", surface_type=SurfaceType.TURF,
            field_size=FieldSize.SEVEN, price_per_hour=1000,
        )
        start = timezone.now() + timedelta(hours=3)
        end = start + timedelta(hours=1)
        result = create_booking(client=client_user, venue=venue, start_time=start, end_time=end)
        booking_id = result.booking.id

        params = {"pg_order_id": f"booking-{booking_id}", "pg_result": "0"}
        params["pg_sig"] = _sign("result", params)
        self.client.post("/api/payments/freedompay/result/", params)

        from apps.bookings.services import expire_booking

        # Повторный вызов (например поздний Celery-таймер) — не должен падать.
        expire_booking(booking_id)

        payment = Payment.objects.get(booking_id=booking_id)
        self.assertEqual(payment.status, PaymentStatus.FAILED)

    @override_settings(**FREEDOMPAY_SETTINGS)
    def test_failed_result_cancels_tournament_registration_and_frees_slot(self):
        """
        Тот же паттерн, что и для брони (см. тест выше) — перенесён на
        взнос за турнир: асинхронная неудача больше не оставляет
        регистрацию висеть и не держит место под лимитом команд навечно.
        """
        organizer = User.objects.create_user(phone="+996700900010", password="x")
        captain_a = User.objects.create_user(phone="+996700900011", password="x")
        captain_b = User.objects.create_user(phone="+996700900012", password="x")
        team_a = create_football_team(name="Вебхук FC", creator=captain_a)
        team_b = create_football_team(name="Резерв FC", creator=captain_b)

        tournament = create_tournament(
            name="Кубок вебхука", organizer=organizer, entry_fee=200, min_teams=1, max_teams=1,
            registration_deadline=timezone.now() + timedelta(hours=1),
        )
        registration = register_team(tournament=tournament, team=team_a, registrant=captain_a)

        params = {"pg_order_id": f"tournament-entry-{registration.id}", "pg_result": "0"}
        params["pg_sig"] = _sign("result", params)
        response = self.client.post("/api/payments/freedompay/result/", params)

        self.assertIn(b"ok", response.content)
        registration.refresh_from_db()
        self.assertEqual(registration.status, RegistrationStatus.CANCELLED)
        payment = Payment.objects.get(tournament_registration=registration)
        self.assertEqual(payment.status, PaymentStatus.FAILED)

        # max_teams=1 был занят отменённой регистрацией — теперь свободен.
        second = register_team(tournament=tournament, team=team_b, registrant=captain_b)
        self.assertEqual(second.status, RegistrationStatus.REGISTERED)
