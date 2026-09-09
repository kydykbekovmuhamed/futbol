from datetime import timedelta
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.payments.models import Payment, PaymentStatus
from apps.venues.models import FieldSize, SurfaceType, Venue, VenueMembership, VenueRole

from .models import Booking, BookingStatus
from .services import (
    BookingAlreadyResolved,
    BookingWindowInvalid,
    NotBookingOwner,
    NotVenueAdmin,
    SlotUnavailable,
    confirm_booking,
    confirm_extension,
    create_booking,
    decline_booking,
    decline_extension,
    expire_booking,
    offer_extension,
)


class BookingFixturesMixin:
    def setUp(self):
        super().setUp()
        self.client_user = User.objects.create_user(phone="+996700100001", password="x")
        self.other_client = User.objects.create_user(phone="+996700100002", password="x")
        self.admin_user = User.objects.create_user(phone="+996700100003", password="x")
        self.venue = Venue.objects.create(
            name="Тестовая арена",
            address="ул. Тестовая 1",
            surface_type=SurfaceType.TURF,
            field_size=FieldSize.SEVEN,
            price_per_hour=1000,
        )
        VenueMembership.objects.create(venue=self.venue, user=self.admin_user, role=VenueRole.VENUE_ADMIN)
        self.now = timezone.now()

    def make_confirmed_booking(self, start_offset_hours=2, duration_hours=1):
        start = self.now + timedelta(hours=start_offset_hours)
        end = start + timedelta(hours=duration_hours)
        result = create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)
        return confirm_booking(booking_id=result.booking.id, admin_user=self.admin_user)


class CreateBookingTests(BookingFixturesMixin, TestCase):
    def test_creates_pending_booking_with_held_payment(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)

        result = create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)

        self.assertEqual(result.booking.status, BookingStatus.PENDING_CONFIRMATION)
        self.assertEqual(result.booking.price, self.venue.price_per_hour)
        self.assertEqual(result.payment.status, PaymentStatus.HELD)
        self.assertEqual(result.payment.amount, result.booking.deposit_amount)
        self.assertEqual(result.payment_redirect_url, "")  # mock-провайдер редиректа не даёт

    def test_redirect_url_from_provider_reaches_response(self):
        """
        Провайдер с редиректом (FreedomPay) возвращает redirect_url вместо
        мгновенного подтверждения — проверяем, что он доходит и до
        BookingCreationResult, и до тела HTTP-ответа (см. apps/bookings/views.py).
        """
        from unittest.mock import patch

        from apps.payments.providers import PaymentResult

        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)

        fake_result = PaymentResult(success=True, external_id="fp-1", redirect_url="https://pay.example/abc")
        with patch("apps.bookings.services.get_payment_provider") as mock_get_provider:
            mock_get_provider.return_value.hold.return_value = fake_result
            mock_get_provider.return_value.strategy = "hold_capture"
            result = create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)

        self.assertEqual(result.payment_redirect_url, "https://pay.example/abc")

    def test_rejects_start_in_the_past(self):
        start = self.now - timedelta(hours=1)
        end = self.now + timedelta(hours=1)

        with self.assertRaises(BookingWindowInvalid):
            create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)

    def test_rejects_end_before_start(self):
        start = self.now + timedelta(hours=2)
        end = start - timedelta(minutes=30)

        with self.assertRaises(BookingWindowInvalid):
            create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)

    def test_double_booking_same_slot_rejected(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)

        with self.assertRaises(SlotUnavailable):
            create_booking(client=self.other_client, venue=self.venue, start_time=start, end_time=end)

    def test_overlapping_slot_rejected(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)

        with self.assertRaises(SlotUnavailable):
            create_booking(
                client=self.other_client,
                venue=self.venue,
                start_time=start + timedelta(minutes=30),
                end_time=end + timedelta(minutes=30),
            )

    def test_adjacent_non_overlapping_slot_allowed(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)

        result = create_booking(client=self.other_client, venue=self.venue, start_time=end, end_time=end + timedelta(hours=1))
        self.assertEqual(result.booking.status, BookingStatus.PENDING_CONFIRMATION)

    def test_declined_booking_frees_the_slot(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        result = create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)
        decline_booking(booking_id=result.booking.id, admin_user=self.admin_user)

        second = create_booking(client=self.other_client, venue=self.venue, start_time=start, end_time=end)
        self.assertEqual(second.booking.status, BookingStatus.PENDING_CONFIRMATION)


class ConfirmDeclineBookingTests(BookingFixturesMixin, TestCase):
    def _create(self, offset_hours=2):
        start = self.now + timedelta(hours=offset_hours)
        end = start + timedelta(hours=1)
        return create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end).booking

    def test_admin_confirm_captures_payment(self):
        booking = self._create()

        confirmed = confirm_booking(booking_id=booking.id, admin_user=self.admin_user)

        self.assertEqual(confirmed.status, BookingStatus.CONFIRMED)
        self.assertIsNotNone(confirmed.confirmed_at)
        payment = Payment.objects.get(booking=confirmed)
        self.assertEqual(payment.status, PaymentStatus.CAPTURED)

    def test_non_admin_cannot_confirm(self):
        booking = self._create()

        with self.assertRaises(NotVenueAdmin):
            confirm_booking(booking_id=booking.id, admin_user=self.client_user)

    def test_confirming_twice_raises_already_resolved(self):
        booking = self._create()
        confirm_booking(booking_id=booking.id, admin_user=self.admin_user)

        with self.assertRaises(BookingAlreadyResolved):
            confirm_booking(booking_id=booking.id, admin_user=self.admin_user)

    def test_decline_releases_payment(self):
        booking = self._create()

        declined = decline_booking(booking_id=booking.id, admin_user=self.admin_user)

        self.assertEqual(declined.status, BookingStatus.DECLINED)
        payment = Payment.objects.get(booking=declined)
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)  # charge_auto_refund по умолчанию

    def test_expire_releases_payment_and_frees_slot(self):
        booking = self._create()

        expired = expire_booking(booking.id)

        self.assertEqual(expired.status, BookingStatus.EXPIRED)
        payment = Payment.objects.get(booking=expired)
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)

    def test_expire_is_noop_if_already_confirmed(self):
        """Гонка: таймер сработал уже после того, как админ подтвердил бронь вручную."""
        booking = self._create()
        confirm_booking(booking_id=booking.id, admin_user=self.admin_user)

        result = expire_booking(booking.id)

        self.assertEqual(result.status, BookingStatus.CONFIRMED)
        payment = Payment.objects.get(booking_id=booking.id)
        self.assertEqual(payment.status, PaymentStatus.CAPTURED)  # не тронут повторным release

    def test_confirm_computes_platform_commission(self):
        # venue.price_per_hour=1000, час, задаток 30% = 300.00, комиссия 10% с него = 30.00
        self.venue.commission_percent = 10
        self.venue.save(update_fields=["commission_percent"])
        booking = self._create()

        confirm_booking(booking_id=booking.id, admin_user=self.admin_user)

        payment = Payment.objects.get(booking_id=booking.id)
        self.assertEqual(payment.amount, Decimal("300.00"))
        self.assertEqual(payment.commission_amount, Decimal("30.00"))

    def test_decline_does_not_record_commission(self):
        booking = self._create()

        decline_booking(booking_id=booking.id, admin_user=self.admin_user)

        payment = Payment.objects.get(booking_id=booking.id)
        self.assertIsNone(payment.commission_amount)

    def test_expire_does_not_record_commission(self):
        booking = self._create()

        expire_booking(booking.id)

        payment = Payment.objects.get(booking_id=booking.id)
        self.assertIsNone(payment.commission_amount)


class ExtensionTests(BookingFixturesMixin, TestCase):
    def test_offer_extension_blocks_slot_from_other_clients(self):
        original = self.make_confirmed_booking()

        extension = offer_extension(original.id)

        self.assertEqual(extension.status, BookingStatus.EXTENSION_PENDING)
        self.assertEqual(extension.extended_from_id, original.id)
        self.assertEqual(extension.start_time, original.end_time)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Booking.objects.create(
                    venue=self.venue,
                    client=self.other_client,
                    start_time=extension.start_time,
                    end_time=extension.end_time,
                    status=BookingStatus.PENDING_CONFIRMATION,
                    price=1000,
                    deposit_amount=300,
                    confirmation_deadline=self.now + timedelta(minutes=10),
                )

    def test_offer_extension_is_idempotent(self):
        original = self.make_confirmed_booking()
        offer_extension(original.id)

        duplicate = offer_extension(original.id)

        self.assertIsNone(duplicate)
        self.assertEqual(Booking.objects.filter(extended_from=original).count(), 1)

    def test_offer_extension_noop_if_not_confirmed(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        pending = create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end).booking

        result = offer_extension(pending.id)

        self.assertIsNone(result)

    def test_client_confirms_extension(self):
        original = self.make_confirmed_booking()
        extension = offer_extension(original.id)

        confirmed = confirm_extension(booking_id=extension.id, client=self.client_user)

        self.assertEqual(confirmed.status, BookingStatus.CONFIRMED)
        payment = Payment.objects.get(booking=confirmed)
        self.assertEqual(payment.status, PaymentStatus.CAPTURED)

    def test_other_user_cannot_confirm_extension(self):
        original = self.make_confirmed_booking()
        extension = offer_extension(original.id)

        with self.assertRaises(NotBookingOwner):
            confirm_extension(booking_id=extension.id, client=self.other_client)

    def test_client_can_explicitly_decline_extension(self):
        original = self.make_confirmed_booking()
        extension = offer_extension(original.id)

        declined = decline_extension(booking_id=extension.id, client=self.client_user)

        self.assertEqual(declined.status, BookingStatus.CANCELLED)
        payment = Payment.objects.get(booking=declined)
        self.assertEqual(payment.status, PaymentStatus.REFUNDED)

    def test_extension_timeout_expires_and_frees_slot(self):
        original = self.make_confirmed_booking()
        extension = offer_extension(original.id)

        expired = expire_booking(extension.id)

        self.assertEqual(expired.status, BookingStatus.EXPIRED)
        # Слот на следующий час теперь свободен для кого угодно.
        new_booking = create_booking(
            client=self.other_client, venue=self.venue, start_time=extension.start_time, end_time=extension.end_time
        )
        self.assertEqual(new_booking.booking.status, BookingStatus.PENDING_CONFIRMATION)


class BookingViewsTests(BookingFixturesMixin, APITestCase):
    def setUp(self):
        super().setUp()
        self.client = APIClient()

    def _auth(self, user):
        self.client.force_authenticate(user=user)

    def test_availability_excludes_booked_venue(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)

        self._auth(self.other_client)
        response = self.client.get(
            "/api/venues/available/",
            {"start": start.isoformat(), "end": end.isoformat()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(self.venue.id, [v["id"] for v in response.data])

    def test_create_booking_then_confirm_via_api(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)

        self._auth(self.client_user)
        create_response = self.client.post(
            "/api/bookings/create/",
            {"venue": self.venue.id, "start_time": start.isoformat(), "end_time": end.isoformat()},
        )
        self.assertEqual(create_response.status_code, 201)
        booking_id = create_response.data["id"]

        self._auth(self.admin_user)
        confirm_response = self.client.post(f"/api/bookings/{booking_id}/confirm/")
        self.assertEqual(confirm_response.status_code, 200)
        self.assertEqual(confirm_response.data["status"], BookingStatus.CONFIRMED)

    def test_confirm_by_non_admin_returns_403(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        booking = create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end).booking

        self._auth(self.client_user)
        response = self.client.post(f"/api/bookings/{booking.id}/confirm/")

        self.assertEqual(response.status_code, 403)

    def test_double_booking_via_api_returns_409(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        create_booking(client=self.client_user, venue=self.venue, start_time=start, end_time=end)

        self._auth(self.other_client)
        response = self.client.post(
            "/api/bookings/create/",
            {"venue": self.venue.id, "start_time": start.isoformat(), "end_time": end.isoformat()},
        )

        self.assertEqual(response.status_code, 409)

    def test_create_response_includes_redirect_url_when_provider_gives_one(self):
        from unittest.mock import patch

        from apps.payments.providers import PaymentResult

        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        self._auth(self.client_user)

        fake_result = PaymentResult(success=True, external_id="fp-2", redirect_url="https://pay.example/xyz")
        with patch("apps.bookings.services.get_payment_provider") as mock_get_provider:
            mock_get_provider.return_value.hold.return_value = fake_result
            mock_get_provider.return_value.strategy = "hold_capture"
            response = self.client.post(
                "/api/bookings/create/",
                {"venue": self.venue.id, "start_time": start.isoformat(), "end_time": end.isoformat()},
            )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["payment_redirect_url"], "https://pay.example/xyz")

    def test_create_response_has_no_redirect_field_for_mock_provider(self):
        start = self.now + timedelta(hours=2)
        end = start + timedelta(hours=1)
        self._auth(self.client_user)

        response = self.client.post(
            "/api/bookings/create/",
            {"venue": self.venue.id, "start_time": start.isoformat(), "end_time": end.isoformat()},
        )

        self.assertEqual(response.status_code, 201)
        self.assertNotIn("payment_redirect_url", response.data)
