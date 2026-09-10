from django.db import models
from django.db.models import Q


class PaymentStrategy(models.TextChoices):
    """
    См. roadmap, раздел 8, вопрос 2. Пока не подтверждён провайдер с
    поддержкой hold (резервирование без списания) в Кыргызстане, платёжный
    слой абстрагирован от конкретной схемы: бизнес-логика брони работает
    одинаково для обеих стратегий, отличается только реализация в apps.payments.providers.
    """

    HOLD_CAPTURE = "hold_capture", "Hold + списание после подтверждения"
    CHARGE_AUTO_REFUND = "charge_auto_refund", "Списание сразу + автовозврат при отказе"


class PaymentProviderName(models.TextChoices):
    MOCK = "mock", "Заглушка (на время разработки)"
    FREEDOMPAY = "freedompay", "FreedomPay (Кыргызстан)"


class PaymentStatus(models.TextChoices):
    HELD = "held", "Зарезервировано"
    CAPTURED = "captured", "Списано"
    RELEASED = "released", "Резерв снят"
    REFUNDED = "refunded", "Возвращено клиенту"
    FAILED = "failed", "Ошибка"


class Payment(models.Model):
    """
    Универсальный платёж поверх hold/capture/release-абстракции — не привязан
    жёстко к брони площадки: взнос за участие в турнире (roadmap 4.1) и
    подписка команды (Этап 3) сделаны раздельными платежами, не бронью,
    поэтому у Payment ровно одна из трёх целей (см. CheckConstraint).

    booking/tournament_registration — OneToOne (одна бронь = один платёж).
    team_subscription — обычный ForeignKey, не OneToOne: у подписки за её
    время жизни несколько платежей (первая покупка + продления), у брони
    и турнирного взноса — всегда ровно один.
    """

    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.CASCADE,
        related_name="payment",
        null=True,
        blank=True,
        verbose_name="Бронь",
    )
    tournament_registration = models.OneToOneField(
        "tournaments.TournamentRegistration",
        on_delete=models.CASCADE,
        related_name="payment",
        null=True,
        blank=True,
        verbose_name="Регистрация на турнир",
    )
    team_subscription = models.ForeignKey(
        "community.TeamSubscription",
        on_delete=models.CASCADE,
        related_name="payments",
        null=True,
        blank=True,
        verbose_name="Подписка команды",
    )
    provider = models.CharField(
        "Провайдер", max_length=30, choices=PaymentProviderName.choices, default=PaymentProviderName.MOCK
    )
    strategy = models.CharField("Стратегия", max_length=30, choices=PaymentStrategy.choices)
    amount = models.DecimalField("Сумма", max_digits=10, decimal_places=2)
    status = models.CharField("Статус", max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.HELD)
    external_id = models.CharField("Внешний ID", max_length=255, blank=True)
    commission_amount = models.DecimalField(
        "Комиссия платформы",
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text=(
            "Комиссия платформы/организатора с этого платежа (roadmap, раздел 3 и 4.1). "
            "Заполняется только при списании (CAPTURED) — со снятого резерва/возврата "
            "комиссии не бывает. Это учётное поле, а не реальный перевод денег: "
            "фактического payout площадкам/организаторам ещё нет, провайдер не подключён."
        ),
    )
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    settled_at = models.DateTimeField(
        "Момент расчёта", null=True, blank=True, help_text="Момент списания/возврата/снятия резерва."
    )

    class Meta:
        verbose_name = "Платёж"
        verbose_name_plural = "Платежи"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(booking__isnull=False, tournament_registration__isnull=True, team_subscription__isnull=True)
                    | Q(booking__isnull=True, tournament_registration__isnull=False, team_subscription__isnull=True)
                    | Q(booking__isnull=True, tournament_registration__isnull=True, team_subscription__isnull=False)
                ),
                name="payment_exactly_one_target",
            ),
        ]

    def __str__(self):
        target = self.booking_id or self.tournament_registration_id or self.team_subscription_id
        return f"{self.get_status_display()} — {self.amount} ({target})"
