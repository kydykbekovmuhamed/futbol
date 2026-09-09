from django.conf import settings
from django.db import models


class ActivityEventType(models.TextChoices):
    RATING_CHANGED = "rating_changed", "Изменение рейтинга команды"
    RANK_UP = "rank_up", "Новое звание команды"
    CHALLENGE_RECEIVED = "challenge_received", "Получен вызов"
    CHALLENGE_ACCEPTED = "challenge_accepted", "Вызов принят"
    CHALLENGE_DECLINED = "challenge_declined", "Вызов отклонён"


class ActivityEvent(models.Model):
    """
    Персонализированная лента активности (roadmap, Этап 3): "твоя команда
    поднялась в рейтинге", "тебе бросили вызов" и т.п. — те же события,
    что уходят push-уведомлением (roadmap: "Push-уведомления на основе
    поведения"), но остаются в ленте, даже если push не увидели/выключили.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="activity_events")
    event_type = models.CharField(max_length=30, choices=ActivityEventType.choices)
    title = models.CharField(max_length=255)
    body = models.CharField(max_length=500, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Событие ленты активности"
        verbose_name_plural = "События ленты активности"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user}: {self.title}"


class ChallengeStatus(models.TextChoices):
    PENDING = "pending", "Ожидает ответа"
    ACCEPTED = "accepted", "Принят"
    DECLINED = "declined", "Отклонён"
    CANCELLED = "cancelled", "Отменён"


class Challenge(models.Model):
    """
    "Тебе бросили вызов" (roadmap, раздел 5) — прямой вызов команды на игру,
    в отличие от открытой заявки OpponentRequest (apps.matchmaking, Этап 2):
    здесь конкретная команда адресует вызов конкретной другой команде, без
    привязки к уже забронированному слоту площадки.
    """

    challenger_team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="sent_challenges")
    opponent_team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="received_challenges")
    message = models.CharField(max_length=500, blank=True)
    proposed_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=ChallengeStatus.choices, default=ChallengeStatus.PENDING)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Вызов"
        verbose_name_plural = "Вызовы"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(challenger_team=models.F("opponent_team")),
                name="challenge_teams_differ",
            ),
        ]

    def __str__(self):
        return f"{self.challenger_team} → {self.opponent_team} ({self.get_status_display()})"


class NewsItem(models.Model):
    """
    Лёгкая агрегация новостей (roadmap, раздел 5): "заголовок + ссылка на
    источник, без копирования полного текста" — осознанно без парсера/RSS,
    наполняется вручную через admin (нет инфраструктуры под скрапинг, и
    это не то, что нужно строить ради Этапа 3).
    """

    title = models.CharField(max_length=255)
    source_name = models.CharField(max_length=255)
    source_url = models.URLField()
    published_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Новость"
        verbose_name_plural = "Новости"
        ordering = ["-published_at"]

    def __str__(self):
        return self.title


class TeamSubscription(models.Model):
    """
    Подписка команды (roadmap, раздел 3: "Подписка игроков/команд" —
    расширенная статистика, Этап 3, когда комьюнити-слой набрал активность).
    Не рекуррентный биллинг — разовая оплата на фиксированный срок
    (SUBSCRIPTION_DURATION_DAYS), продлевается таким же разовым платежом;
    полноценный recurring billing непропорционален тому, что нужно сейчас
    (нет живого платёжного провайдера, который мог бы сам списывать по
    расписанию — см. CLAUDE.md про FreedomPay).
    """

    team = models.OneToOneField("teams.Team", on_delete=models.CASCADE, related_name="subscription")
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Подписка команды"
        verbose_name_plural = "Подписки команд"

    @property
    def is_active(self) -> bool:
        from django.utils import timezone

        return self.expires_at is not None and self.expires_at > timezone.now()

    def __str__(self):
        return f"{self.team}: до {self.expires_at:%d.%m.%Y}" if self.expires_at else f"{self.team}: не активна"
