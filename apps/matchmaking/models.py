from django.conf import settings
from django.db import models


class OpponentRequestStatus(models.TextChoices):
    OPEN = "open", "Открыт"
    MATCHED = "matched", "Соперник найден"
    CANCELLED = "cancelled", "Отменён"


class OpponentRequest(models.Model):
    """roadmap, Этап 2: "Поиск соперника" — команда уже забронировала слот и ищет, с кем сыграть."""

    team = models.ForeignKey(
        "teams.Team", on_delete=models.CASCADE, related_name="opponent_requests", verbose_name="Команда"
    )
    booking = models.OneToOneField(
        "bookings.Booking", on_delete=models.CASCADE, related_name="opponent_request", verbose_name="Бронь"
    )
    message = models.CharField("Сообщение", max_length=500, blank=True)
    status = models.CharField(
        "Статус", max_length=20, choices=OpponentRequestStatus.choices, default=OpponentRequestStatus.OPEN
    )
    matched_team = models.ForeignKey(
        "teams.Team",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="matched_opponent_requests",
        verbose_name="Команда-соперник",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="Создал"
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    matched_at = models.DateTimeField("Найден соперник", null=True, blank=True)

    class Meta:
        verbose_name = "Заявка на поиск соперника"
        verbose_name_plural = "Заявки на поиск соперника"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.team} ищет соперника на бронь #{self.booking_id}"


class PlayerRequestStatus(models.TextChoices):
    OPEN = "open", "Открыт"
    CLOSED = "closed", "Закрыт"


class PlayerRequest(models.Model):
    """roadmap, Этап 2: "Поиск игрока в состав" — команде не хватает игроков на конкретную игру."""

    team = models.ForeignKey(
        "teams.Team", on_delete=models.CASCADE, related_name="player_requests", verbose_name="Команда"
    )
    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.CASCADE, related_name="player_requests", verbose_name="Бронь"
    )
    spots_needed = models.PositiveSmallIntegerField("Нужно игроков", default=1)
    message = models.CharField("Сообщение", max_length=500, blank=True)
    status = models.CharField(
        "Статус", max_length=20, choices=PlayerRequestStatus.choices, default=PlayerRequestStatus.OPEN
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+", verbose_name="Создал"
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Заявка на поиск игрока"
        verbose_name_plural = "Заявки на поиск игрока"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.team}: нужно {self.spots_needed} игрок(ов) на бронь #{self.booking_id}"


class ApplicationStatus(models.TextChoices):
    PENDING = "pending", "Рассматривается"
    ACCEPTED = "accepted", "Принята"
    DECLINED = "declined", "Отклонена"


class PlayerApplication(models.Model):
    request = models.ForeignKey(
        PlayerRequest, on_delete=models.CASCADE, related_name="applications", verbose_name="Заявка"
    )
    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="player_applications",
        verbose_name="Соискатель",
    )
    status = models.CharField(
        "Статус", max_length=20, choices=ApplicationStatus.choices, default=ApplicationStatus.PENDING
    )
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    decided_at = models.DateTimeField("Решение принято", null=True, blank=True)

    class Meta:
        verbose_name = "Заявка игрока"
        verbose_name_plural = "Заявки игроков"
        constraints = [
            models.UniqueConstraint(fields=["request", "applicant"], name="unique_application_per_request"),
        ]

    def __str__(self):
        return f"{self.applicant} -> заявка #{self.request_id} ({self.get_status_display()})"
