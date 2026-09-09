from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient, APITestCase

from .models import OTPCode, User
from .services import (
    OTPCooldown,
    OTPExpired,
    OTPInvalid,
    OTPTooManyAttempts,
    request_otp,
    verify_otp,
)

PHONE = "+996700200001"


class OTPServiceTests(TestCase):
    def test_request_otp_creates_code(self):
        request_otp(PHONE)

        self.assertEqual(OTPCode.objects.filter(phone=PHONE).count(), 1)

    def test_request_otp_cooldown(self):
        request_otp(PHONE)

        with self.assertRaises(OTPCooldown):
            request_otp(PHONE)

    def test_verify_wrong_code_rejected_and_counts_attempt(self):
        request_otp(PHONE)
        otp = OTPCode.objects.get(phone=PHONE)

        with self.assertRaises(OTPInvalid):
            verify_otp(phone=PHONE, code="000000")

        otp.refresh_from_db()
        self.assertEqual(otp.attempts, 1)

    def test_verify_correct_code_creates_user_without_usable_password(self):
        request_otp(PHONE)
        otp = OTPCode.objects.get(phone=PHONE)

        user = verify_otp(phone=PHONE, code=otp.code)

        self.assertEqual(user.phone, PHONE)
        self.assertFalse(user.has_usable_password())

    def test_verify_reuses_existing_user_on_second_login(self):
        request_otp(PHONE)
        first_login_user = verify_otp(phone=PHONE, code=OTPCode.objects.get(phone=PHONE).code)

        OTPCode.objects.filter(phone=PHONE).update(created_at=timezone.now() - timezone.timedelta(minutes=10))
        request_otp(PHONE)
        second_login_user = verify_otp(
            phone=PHONE, code=OTPCode.objects.filter(phone=PHONE, is_used=False).latest("created_at").code
        )

        self.assertEqual(first_login_user.id, second_login_user.id)

    def test_code_cannot_be_used_twice(self):
        request_otp(PHONE)
        otp = OTPCode.objects.get(phone=PHONE)
        verify_otp(phone=PHONE, code=otp.code)

        with self.assertRaises(OTPInvalid):
            verify_otp(phone=PHONE, code=otp.code)

    def test_expired_code_rejected(self):
        request_otp(PHONE)
        OTPCode.objects.filter(phone=PHONE).update(expires_at=timezone.now() - timezone.timedelta(seconds=1))
        otp = OTPCode.objects.get(phone=PHONE)

        with self.assertRaises(OTPExpired):
            verify_otp(phone=PHONE, code=otp.code)

    def test_too_many_attempts_rejected(self):
        request_otp(PHONE)
        OTPCode.objects.filter(phone=PHONE).update(attempts=5)

        with self.assertRaises(OTPTooManyAttempts):
            verify_otp(phone=PHONE, code="000000")


class OTPViewsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()

    def test_full_flow_via_http(self):
        response = self.client.post("/api/auth/otp/request/", {"phone": PHONE})
        self.assertEqual(response.status_code, 200)

        code = OTPCode.objects.get(phone=PHONE).code
        verify_response = self.client.post("/api/auth/otp/verify/", {"phone": PHONE, "code": code})

        self.assertEqual(verify_response.status_code, 200)
        token = verify_response.data["token"]
        user = User.objects.get(phone=PHONE)
        self.assertEqual(Token.objects.get(user=user).key, token)

        me_response = self.client.get("/api/bookings/", HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(me_response.status_code, 200)

    def test_repeat_request_returns_429(self):
        self.client.post("/api/auth/otp/request/", {"phone": PHONE})

        response = self.client.post("/api/auth/otp/request/", {"phone": PHONE})

        self.assertEqual(response.status_code, 429)

    def test_wrong_code_returns_400(self):
        self.client.post("/api/auth/otp/request/", {"phone": PHONE})

        response = self.client.post("/api/auth/otp/verify/", {"phone": PHONE, "code": "000000"})

        self.assertEqual(response.status_code, 400)
