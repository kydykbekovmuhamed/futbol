from django.conf import settings
from django.db import models


class TeamRole(models.TextChoices):
    CAPTAIN = "captain", "Капитан"
    MEMBER = "member", "Игрок"


class Team(models.Model):
    """
    roadmap, Этап 2: "Профили команд, статистика игр". Рейтинг — простая
    очковая система (3/1/0 за победу/ничью/поражение), а не ELO — ELO явно
    отнесён в roadmap (раздел 7) к банку идей на будущее, не к Этапу 2.
    """

    name = models.CharField("Название", max_length=255, unique=True)
    district = models.CharField("Район", max_length=255, blank=True)
    description = models.TextField("Описание", blank=True)

    rating_points = models.IntegerField("Рейтинговые очки", default=0)
    wins = models.PositiveIntegerField("Победы", default=0)
    draws = models.PositiveIntegerField("Ничьи", default=0)
    losses = models.PositiveIntegerField("Поражения", default=0)

    created_at = models.DateTimeField("Создана", auto_now_add=True)

    class Meta:
        verbose_name = "Команда"
        verbose_name_plural = "Команды"
        ordering = ["-rating_points", "name"]

    def __str__(self):
        return self.name

    @property
    def games_played(self) -> int:
        return self.wins + self.draws + self.losses

    @property
    def rank_title(self) -> str:
        """
        "Звание" по очкам рейтинга (roadmap, Этап 3: "прогресс до следующего
        звания") — settings.TEAM_RANK_THRESHOLDS, отсортирован по возрастанию.
        """
        from django.conf import settings

        title = settings.TEAM_RANK_THRESHOLDS[0][1]
        for threshold, name in settings.TEAM_RANK_THRESHOLDS:
            if self.rating_points >= threshold:
                title = name
        return title

    @property
    def points_to_next_rank(self) -> int | None:
        from django.conf import settings

        for threshold, _name in settings.TEAM_RANK_THRESHOLDS:
            if self.rating_points < threshold:
                return threshold - self.rating_points
        return None  # уже высшее звание


class TeamMembership(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships", verbose_name="Команда")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="team_memberships",
        verbose_name="Пользователь",
    )
    role = models.CharField("Роль", max_length=20, choices=TeamRole.choices, default=TeamRole.MEMBER)
    joined_at = models.DateTimeField("Вступил", auto_now_add=True)

    class Meta:
        verbose_name = "Участник команды"
        verbose_name_plural = "Участники команды"
        constraints = [
            models.UniqueConstraint(fields=["team", "user"], name="unique_team_member"),
        ]

    def __str__(self):
        return f"{self.user} в «{self.team}» ({self.get_role_display()})"


class MatchStatus(models.TextChoices):
    SCHEDULED = "scheduled", "Запланирован"
    PLAYED = "played", "Сыгран"
    CANCELLED = "cancelled", "Отменён"


class Match(models.Model):
    """
    Результат игры между двумя командами — источник статистики и рейтинга.
    booking опционален: матч можно завести и без привязки к конкретной
    брони площадки (например, историческая запись или площадка вне системы).

    Упрощение для MVP Этапа 2: результат фиксирует один участник любой из
    команд, без подтверждения second-hand и без разбора споров — это
    сознательный компромисс по объёму, а не то, как это должно быть
    в перспективе (см. CLAUDE.md).
    """

    booking = models.OneToOneField(
        "bookings.Booking",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="match",
        verbose_name="Бронь",
    )
    home_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="home_matches", verbose_name="Хозяева")
    away_team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="away_matches", verbose_name="Гости")
    status = models.CharField("Статус", max_length=20, choices=MatchStatus.choices, default=MatchStatus.SCHEDULED)
    home_score = models.PositiveSmallIntegerField("Счёт хозяев", null=True, blank=True)
    away_score = models.PositiveSmallIntegerField("Счёт гостей", null=True, blank=True)
    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        verbose_name="Внёс результат",
    )
    played_at = models.DateTimeField("Сыгран", null=True, blank=True)
    created_at = models.DateTimeField("Создан", auto_now_add=True)

    class Meta:
        verbose_name = "Матч"
        verbose_name_plural = "Матчи"
        ordering = ["-created_at"]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(home_team=models.F("away_team")),
                name="match_teams_differ",
            ),
        ]

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"
