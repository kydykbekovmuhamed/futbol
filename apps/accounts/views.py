from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import Throttled, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import (
    OTPCooldown,
    OTPExpired,
    OTPInvalid,
    OTPTooManyAttempts,
    request_otp,
    verify_otp,
)


class RequestOTPView(APIView):
    """POST {"phone": "+996..."} — отправляет SMS-код (вход и регистрация не различаются)."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        phone = request.data.get("phone")
        if not phone:
            raise ValidationError({"phone": "Обязательное поле."})

        try:
            request_otp(phone)
        except OTPCooldown as exc:
            raise Throttled(detail=str(exc))

        return Response({"detail": "Код отправлен."})


class VerifyOTPView(APIView):
    """POST {"phone": "...", "code": "123456"} — возвращает auth-токен."""

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        phone = request.data.get("phone")
        code = request.data.get("code")
        if not phone or not code:
            raise ValidationError({"non_field_errors": ["Обязательные поля: phone, code."]})

        try:
            user = verify_otp(phone=phone, code=code)
        except (OTPInvalid, OTPExpired, OTPTooManyAttempts) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key})
