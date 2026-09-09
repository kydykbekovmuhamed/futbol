import random
import string

from django.conf import settings
from django.utils import timezone

from apps.notifications.providers import get_notification_provider

from .models import OTPCode, User


class OTPCooldown(Exception):
    """Код уже недавно отправлялся на этот номер — просим подождать."""


class OTPInvalid(Exception):
    """Код не запрашивался, уже использован, или введён неверно."""


class OTPExpired(Exception):
    """Код найден, но время его жизни истекло."""


class OTPTooManyAttempts(Exception):
    """Превышено число попыток ввода для последнего запрошенного кода."""


def _generate_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def request_otp(phone: str) -> None:
    """
    Регистрация и вход объединены в один SMS-флоу (roadmap не разделяет
    "нового" и "старого" клиента — оба вводят телефон и получают код).
    Аккаунт создаётся в verify_otp только после успешной проверки кода.
    """
    cooldown_start = timezone.now() - timezone.timedelta(seconds=settings.OTP_REQUEST_COOLDOWN_SECONDS)
    if OTPCode.objects.filter(phone=phone, created_at__gte=cooldown_start).exists():
        raise OTPCooldown(f"Код уже отправлен, повторный запрос — через {settings.OTP_REQUEST_COOLDOWN_SECONDS} сек.")

    code = _generate_code()
    OTPCode.objects.create(
        phone=phone,
        code=code,
        expires_at=timezone.now() + timezone.timedelta(minutes=settings.OTP_TTL_MINUTES),
    )
    provider = get_notification_provider()
    provider.send_sms(phone=phone, text=f"Код для входа: {code}. Никому не сообщайте его.")


def verify_otp(*, phone: str, code: str) -> User:
    try:
        otp = OTPCode.objects.filter(phone=phone, is_used=False).latest("created_at")
    except OTPCode.DoesNotExist:
        raise OTPInvalid("Код не запрашивался или уже использован.")

    if otp.expires_at < timezone.now():
        raise OTPExpired("Код истёк, запросите новый.")
    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise OTPTooManyAttempts("Слишком много попыток, запросите новый код.")

    if otp.code != code:
        otp.attempts += 1
        otp.save(update_fields=["attempts"])
        raise OTPInvalid("Неверный код.")

    otp.is_used = True
    otp.save(update_fields=["is_used"])

    user, created = User.objects.get_or_create(phone=phone)
    if created:
        user.set_unusable_password()
        user.save(update_fields=["password"])
    return user
