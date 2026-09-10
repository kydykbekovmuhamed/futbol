from django.conf import settings
from django.db import models


class DevicePlatform(models.TextChoices):
    IOS = "ios", "iOS"
    ANDROID = "android", "Android"
    WEB = "web", "Web"


class DeviceToken(models.Model):
    """
    Токен устройства для push (Firebase Cloud Messaging). FCM шлёт push не
    на телефон, а на токен конкретного приложения на конкретном устройстве —
    без регистрации токена реальный push отправить некому, даже с ключами.
    Клиент регистрирует токен после логина и/или при каждом запуске
    приложения (см. apps/notifications/views.py).
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="device_tokens", verbose_name="Пользователь"
    )
    token = models.CharField("Токен", max_length=255, unique=True)
    platform = models.CharField(
        "Платформа", max_length=10, choices=DevicePlatform.choices, default=DevicePlatform.ANDROID
    )
    is_active = models.BooleanField("Активен", default=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    last_seen_at = models.DateTimeField("Последняя активность", auto_now=True)

    class Meta:
        verbose_name = "Токен устройства"
        verbose_name_plural = "Токены устройств"

    def __str__(self):
        return f"{self.user} — {self.platform} ({'активен' if self.is_active else 'неактивен'})"


class NotificationChannel(models.TextChoices):
    PUSH = "push", "Push"
    SMS = "sms", "SMS"
    CALL = "call", "Автозвонок"


class NotificationStatus(models.TextChoices):
    SENT = "sent", "Отправлено"
    DELIVERED = "delivered", "Доставлено"
    FAILED = "failed", "Ошибка отправки"
    CONFIRMED_VIA = "confirmed_via", "Подтверждено через этот канал"


class NotificationLog(models.Model):
    """
    Лог уведомлений по гибридному подтверждению (roadmap 2.2): на одну бронь
    админу площадки может прийти несколько записей (push и SMS/звонок
    одновременно, повторное уведомление за 2 минуты до истечения таймера).
    Канал, которым админ реально подтвердил/отклонил, помечается
    CONFIRMED_VIA — нужно для будущей аналитики "какой канал эффективнее".
    """

    booking = models.ForeignKey(
        "bookings.Booking", on_delete=models.CASCADE, related_name="notifications", verbose_name="Бронь"
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications_received",
        verbose_name="Получатель",
    )
    channel = models.CharField("Канал", max_length=10, choices=NotificationChannel.choices)
    status = models.CharField(
        "Статус", max_length=20, choices=NotificationStatus.choices, default=NotificationStatus.SENT
    )
    sent_at = models.DateTimeField("Отправлено", auto_now_add=True)
    responded_at = models.DateTimeField("Отвечено", null=True, blank=True)

    class Meta:
        verbose_name = "Уведомление"
        verbose_name_plural = "Уведомления"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.get_channel_display()} → {self.recipient} ({self.booking_id})"
