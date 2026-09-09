from django.conf import settings
from django.db import models

from apps.payments.utils import percentage_of


class SurfaceType(models.TextChoices):
    HALL = "hall", "Зал (футзал)"
    TURF = "turf", "Искусственный газон"
    STADIUM = "stadium", "Стадион"


class FieldSize(models.TextChoices):
    FIVE = "5x5", "5x5"
    SEVEN = "7x7", "7x7"
    ELEVEN = "11x11", "11x11"


class SubscriptionTier(models.TextChoices):
    BASIC = "basic", "Базовый"
    ADVANCED = "advanced", "Продвинутый"


class VenueRole(models.TextChoices):
    VENUE_ADMIN = "venue_admin", "Администратор площадки"


class Venue(models.Model):
    name = models.CharField(max_length=255)
    district = models.CharField("Район", max_length=255, blank=True)
    address = models.CharField(max_length=255)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    surface_type = models.CharField(max_length=20, choices=SurfaceType.choices)
    field_size = models.CharField(max_length=10, choices=FieldSize.choices)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    subscription_tier = models.CharField(
        max_length=20, choices=SubscriptionTier.choices, default=SubscriptionTier.BASIC
    )
    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=settings.DEFAULT_VENUE_COMMISSION_PERCENT,
        help_text="Комиссия платформы с онлайн-задатка по этой площадке (roadmap, раздел 3).",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Площадка"
        verbose_name_plural = "Площадки"
        ordering = ["name"]

    def commission_on(self, amount):
        return percentage_of(amount, self.commission_percent)

    def __str__(self):
        return self.name


class VenueMembership(models.Model):
    """
    Роль "администратор площадки" — намеренно отдельная сущность-назначение
    (User <-> Venue), а не булево поле на User (roadmap, раздел 2.4 и
    открытый вопрос 3 из раздела 8): один человек может администрировать
    несколько площадок, у площадки может быть несколько админов. Роль
    сделана choices-полем, а не отдельными булевыми флагами — это позволяет
    в Этапе 2 добавить корпоративные роли (HR/офис-менеджер турниров) новым
    значением choices, без переделки структуры таблицы.
    """

    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="venue_memberships"
    )
    role = models.CharField(max_length=30, choices=VenueRole.choices, default=VenueRole.VENUE_ADMIN)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Назначение на площадку"
        verbose_name_plural = "Назначения на площадку"
        constraints = [
            models.UniqueConstraint(fields=["venue", "user", "role"], name="unique_venue_user_role"),
        ]

    def __str__(self):
        return f"{self.user} → {self.venue} ({self.get_role_display()})"
