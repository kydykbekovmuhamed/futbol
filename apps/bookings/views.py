from django.http import Http404
from rest_framework import generics, status
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.notifications.models import NotificationChannel

from .models import Booking
from .serializers import BookingCreateSerializer, BookingSerializer
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
)


class MyBookingsView(generics.ListAPIView):
    serializer_class = BookingSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Booking.objects.filter(client=self.request.user).select_related("venue")


class BookingCreateView(generics.GenericAPIView):
    """
    Создание брони (roadmap 2.1 + 2.2, первая половина): клиент указывает
    площадку и интервал времени, задаток резервируется сразу. Ответ 201 —
    бронь создана и ждёт подтверждения администратора.
    """

    serializer_class = BookingCreateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            result = create_booking(client=request.user, **serializer.validated_data)
        except BookingWindowInvalid as exc:
            raise ValidationError({"non_field_errors": [str(exc)]})
        except SlotUnavailable as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        data = BookingSerializer(result.booking).data
        if result.payment_redirect_url:
            # Провайдер с редиректом (например FreedomPay) — клиента нужно
            # отправить на эту страницу, чтобы реально завершить оплату
            # задатка; без этого поля (mock/провайдеры без редиректа) — пусто.
            data["payment_redirect_url"] = result.payment_redirect_url
        return Response(data, status=status.HTTP_201_CREATED)


class _BookingDecisionView(APIView):
    """Общая часть для подтверждения/отклонения брони администратором площадки."""

    permission_classes = [IsAuthenticated]
    action = None  # переопределяется в наследниках

    VALID_CHANNELS = {NotificationChannel.PUSH, NotificationChannel.SMS, NotificationChannel.CALL}

    def post(self, request, pk, *args, **kwargs):
        channel = request.data.get("channel", NotificationChannel.PUSH)
        if channel not in self.VALID_CHANNELS:
            raise ValidationError({"channel": f"Допустимые значения: {sorted(self.VALID_CHANNELS)}."})

        try:
            booking = self.action(booking_id=pk, admin_user=request.user, channel=channel)
        except Booking.DoesNotExist:
            raise NotFound("Бронь не найдена.")
        except Http404:
            raise NotFound("Бронь не найдена.")
        except NotVenueAdmin as exc:
            raise PermissionDenied(str(exc))
        except BookingAlreadyResolved as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(BookingSerializer(booking).data)


class BookingConfirmView(_BookingDecisionView):
    action = staticmethod(confirm_booking)


class BookingDeclineView(_BookingDecisionView):
    action = staticmethod(decline_booking)


class _ExtensionDecisionView(APIView):
    """
    Продление (roadmap 2.3) подтверждает/отклоняет сам клиент — без участия
    администратора площадки, в отличие от _BookingDecisionView выше.
    """

    permission_classes = [IsAuthenticated]
    action = None  # переопределяется в наследниках

    def post(self, request, pk, *args, **kwargs):
        try:
            booking = self.action(booking_id=pk, client=request.user)
        except Booking.DoesNotExist:
            raise NotFound("Бронь не найдена.")
        except NotBookingOwner as exc:
            raise PermissionDenied(str(exc))
        except BookingAlreadyResolved as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)

        return Response(BookingSerializer(booking).data)


class BookingExtensionConfirmView(_ExtensionDecisionView):
    action = staticmethod(confirm_extension)


class BookingExtensionDeclineView(_ExtensionDecisionView):
    action = staticmethod(decline_extension)
