from django.conf import settings
from django.contrib.postgres.constraints import ExclusionConstraint
from django.contrib.postgres.fields import RangeOperators
from django.db import models
from django.db.models import F, Func, Q


class BookingStatus(models.TextChoices):
    PENDING_CONFIRMATION = "pending_confirmation", "Ждёт подтверждения администратора"
    EXTENSION_PENDING = "extension_pending", "Ждёт решения клиента о продлении"
    CONFIRMED = "confirmed", "Подтверждена"
    DECLINED = "declined", "Отклонена администратором"
    EXPIRED = "expired", "Истекло время ответа"
    CANCELLED = "cancelled", "Отменена клиентом"
    COMPLETED = "completed", "Завершена"


# Статусы, при которых бронь занимает слот и блокирует пересечение по времени
# на этой площадке (см. ExclusionConstraint ниже). Клиент "резервирует" слот
# уже в момент создания брони (roadmap 2.2), поэтому PENDING_CONFIRMATION
# занимает слот наравне с CONFIRMED — до отклонения/истечения/отмены.
# EXTENSION_PENDING (roadmap 2.3) — та же логика для продления: "придержка"
# следующего часа реализована как обычная бронь в этом статусе, поэтому её
# физически не может перехватить другой клиент, пока текущий игрок решает.
OCCUPYING_BOOKING_STATUSES = [
    BookingStatus.PENDING_CONFIRMATION,
    BookingStatus.EXTENSION_PENDING,
    BookingStatus.CONFIRMED,
]

# Статусы, ожидающие решения (админа или клиента) с таймаутом — именно они
# автоматически переводятся в EXPIRED по истечении confirmation_deadline.
AWAITING_DECISION_STATUSES = [BookingStatus.PENDING_CONFIRMATION, BookingStatus.EXTENSION_PENDING]


class Booking(models.Model):
    venue = models.ForeignKey("venues.Venue", on_delete=models.PROTECT, related_name="bookings")
    client = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(
        max_length=30, choices=BookingStatus.choices, default=BookingStatus.PENDING_CONFIRMATION
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=10, decimal_places=2)

    # Гибридное подтверждение (roadmap 2.2): таймер 5-10 минут с момента брони.
    confirmation_deadline = models.DateTimeField(
        help_text="Если ни один канал (push/звонок/SMS) не сработал к этому моменту — автоотмена."
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)

    # Продление игры (roadmap 2.3): бронь-продление ссылается на исходную,
    # чтобы отличать "новую игру" от "продолжения" в статистике и в UI.
    extended_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="extensions"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Бронь"
        verbose_name_plural = "Брони"
        ordering = ["-start_time"]
        constraints = [
            # Не даёт двум "занимающим слот" броням пересечься по времени на
            # одной площадке — проверяется в БД, а не только в Python, чтобы
            # исключить гонку при параллельных запросах на один и тот же слот.
            ExclusionConstraint(
                name="exclude_overlapping_venue_bookings",
                expressions=[
                    (F("venue"), RangeOperators.EQUAL),
                    (Func("start_time", "end_time", function="tstzrange"), RangeOperators.OVERLAPS),
                ],
                condition=Q(status__in=OCCUPYING_BOOKING_STATUSES),
            ),
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")),
                name="booking_end_after_start",
            ),
        ]

    def __str__(self):
        return f"{self.venue} {self.start_time:%d.%m %H:%M}–{self.end_time:%H:%M} ({self.get_status_display()})"

    @property
    def is_occupying(self) -> bool:
        return self.status in OCCUPYING_BOOKING_STATUSES
