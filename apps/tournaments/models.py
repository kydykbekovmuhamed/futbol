from django.conf import settings
from django.db import models

from apps.payments.utils import percentage_of


class TournamentStatus(models.TextChoices):
    REGISTRATION_OPEN = "registration_open", "Регистрация открыта"
    REGISTRATION_CLOSED = "registration_closed", "Регистрация закрыта, идут игры"
    CANCELLED = "cancelled", "Отменён (не набралось команд)"
    COMPLETED = "completed", "Завершён"


class Tournament(models.Model):
    """
    roadmap, раздел 4 и 4.1: корпоративный/self-service турнир. Точка входа —
    раздел внутри основного приложения (не отдельный HR-лендинг, решение
    подтверждено пользователем). Взнос за участие — раздельный платёж от
    оплаты газона (см. apps.payments.Payment.tournament_registration).
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    sponsor_name = models.CharField(
        max_length=255, blank=True, help_text='"Турнир при поддержке [бренд]" — roadmap 4.1'
    )
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="organized_tournaments"
    )
    entry_fee = models.DecimalField(max_digits=10, decimal_places=2)
    organizer_commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=settings.DEFAULT_TOURNAMENT_ORGANIZER_COMMISSION_PERCENT,
        help_text="Комиссия организатора со взноса каждой команды (roadmap 4.1).",
    )
    min_teams = models.PositiveSmallIntegerField(default=4)
    max_teams = models.PositiveSmallIntegerField(null=True, blank=True)
    registration_deadline = models.DateTimeField()
    status = models.CharField(max_length=30, choices=TournamentStatus.choices, default=TournamentStatus.REGISTRATION_OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Турнир"
        verbose_name_plural = "Турниры"
        ordering = ["-created_at"]

    def commission_on(self, amount):
        return percentage_of(amount, self.organizer_commission_percent)

    def __str__(self):
        return self.name


class RegistrationStatus(models.TextChoices):
    REGISTERED = "registered", "Зарегистрирована (взнос зарезервирован)"
    CANCELLED = "cancelled", "Отменена (взнос возвращён)"
    DISQUALIFIED = "disqualified", "Дисквалифицирована — неявка (взнос не возвращается)"


class TournamentRegistration(models.Model):
    """
    Взнос резервируется (hold) сразу при регистрации — той же схемой, что и
    задаток за площадку (roadmap 2.2), только без администратора площадки:
    списывается при закрытии регистрации (турнир набрался), возвращается при
    отмене турнира/самой команды, сгорает при дисквалификации за неявку
    (roadmap 4.1: "техническое поражение с потерей взноса").
    """

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="registrations")
    team = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="tournament_registrations")
    status = models.CharField(max_length=20, choices=RegistrationStatus.choices, default=RegistrationStatus.REGISTERED)
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Регистрация на турнир"
        verbose_name_plural = "Регистрации на турнир"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(fields=["tournament", "team"], name="unique_team_per_tournament"),
        ]

    def __str__(self):
        return f"{self.team} → {self.tournament} ({self.get_status_display()})"


class TournamentMatch(models.Model):
    """
    Один матч турнирной сетки. roadmap описывает сетку как "блок бронирования
    на нескольких площадках под несколько команд" и "турнирную таблицу
    поверх обычных броней" — организатор вручную сопоставляет пары команд
    и (опционально) конкретную бронь площадки под матч; сам результат и
    статистика идут через уже готовый apps.teams.Match (не дублируем логику).

    Сознательное упрощение MVP: сетка не генерируется автоматически
    (без алгоритма плей-офф/раундов с авто-продвижением победителей) —
    организатор создаёт матчи сам, раунд за раундом. Если нужен полноценный
    automatic bracket — это следующий шаг поверх этой структуры, не то, что
    нужно было ломать ради MVP Этапа 2.
    """

    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, related_name="bracket_matches")
    round_number = models.PositiveSmallIntegerField(default=1)
    home_registration = models.ForeignKey(
        TournamentRegistration, on_delete=models.CASCADE, related_name="home_bracket_matches"
    )
    away_registration = models.ForeignKey(
        TournamentRegistration, on_delete=models.CASCADE, related_name="away_bracket_matches"
    )
    match = models.OneToOneField(
        "teams.Match", on_delete=models.CASCADE, related_name="tournament_match"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Матч турнирной сетки"
        verbose_name_plural = "Матчи турнирной сетки"
        ordering = ["round_number", "created_at"]

    def __str__(self):
        return f"{self.tournament} — раунд {self.round_number}: {self.home_registration} vs {self.away_registration}"
