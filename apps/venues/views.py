from django.db.models import Prefetch
from django.utils.dateparse import parse_datetime
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from apps.bookings.models import OCCUPYING_BOOKING_STATUSES, Booking

from .filters import VenueFilter
from .models import Venue
from .serializers import VenueAvailabilitySerializer, VenueSerializer


class VenueListView(generics.ListAPIView):
    """
    Общий список площадок (раздел "сейчас"/каталог) — не поиск по времени.
    Для занятых прямо сейчас площадок отдаёт occupied_until (roadmap 2.1:
    "освободится через 23 мин") вместо простого "занято".
    """

    serializer_class = VenueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VenueFilter

    def get_queryset(self):
        occupying_qs = Booking.objects.filter(status__in=OCCUPYING_BOOKING_STATUSES).order_by("start_time")
        return (
            Venue.objects.filter(is_active=True)
            .prefetch_related(Prefetch("bookings", queryset=occupying_qs, to_attr="occupying_bookings"))
            .order_by("name")
        )


class VenueAvailabilityView(generics.ListAPIView):
    """
    Ядро сценария 2.1 roadmap: клиент выбирает интервал времени, а не
    площадку — отдаём все площадки, свободные на этот интервал (плюс
    обычные фильтры: район, тип покрытия, размер поля, цена).
    """

    serializer_class = VenueAvailabilitySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = VenueFilter

    def get_queryset(self):
        start, end = self._parse_interval()
        return (
            Venue.objects.filter(is_active=True)
            .exclude(
                bookings__status__in=OCCUPYING_BOOKING_STATUSES,
                bookings__start_time__lt=end,
                bookings__end_time__gt=start,
            )
            .order_by("price_per_hour")
        )

    def _parse_interval(self):
        raw_start = self.request.query_params.get("start")
        raw_end = self.request.query_params.get("end")
        if not raw_start or not raw_end:
            raise ValidationError({"start": "Обязательные параметры: start, end (ISO 8601)."})

        start = parse_datetime(raw_start)
        end = parse_datetime(raw_end)
        if start is None or end is None:
            raise ValidationError({"start": "Не удалось разобрать дату/время, формат ISO 8601."})
        if end <= start:
            raise ValidationError({"end": "end должен быть позже start."})

        return start, end
