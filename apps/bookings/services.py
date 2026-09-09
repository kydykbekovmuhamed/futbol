from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.notifications.models import NotificationChannel, NotificationLog, NotificationStatus
from apps.notifications.services import (
    notify_client_extension_offer,
    notify_client_slot_unavailable,
    notify_venue_admins_of_new_booking,
)
from apps.payments.models import Payment, PaymentStatus, PaymentStrategy
from apps.payments.providers import default_provider_name, get_payment_provider
from apps.payments.utils import percentage_of
from apps.venues.models import Venue, VenueMembership, VenueRole

from .models import AWAITING_DECISION_STATUSES, Booking, BookingStatus


class SlotUnavailable(Exception):
    """Слот занят другой бронью — обнаружено на уровне БД (гонка запросов)."""


class BookingWindowInvalid(Exception):
    """Некорректный интервал: начало в прошлом, конец раньше начала и т.п."""


class NotVenueAdmin(Exception):
    """Пользователь не является активным администратором этой площадки."""


class NotBookingOwner(Exception):
    """Пользователь пытается управлять чужой бронью/продлением."""


class BookingAlreadyResolved(Exception):
    """
    Бронь уже подтверждена/отклонена/истекла — повторное подтверждение,
    отклонение или срабатывание таймера истечения на неё не действует.
    Штатная ситуация при гонке между админом/клиентом и Celery-таймером,
    а не баг.
    """


@dataclass
class BookingCreationResult:
    booking: Booking
    payment: Payment
    # Заполняется провайдерами с редиректом (FreedomPay) — клиента нужно
    # отправить на эту страницу, чтобы реально завершить резервирование
    # денег. Пусто для mock/провайдеров без редиректа.
    payment_redirect_url: str = ""


def _calculate_price(venue: Venue, start_time, end_time) -> Decimal:
    hours = Decimal((end_time - start_time).total_seconds()) / Decimal(3600)
    return (venue.price_per_hour * hours).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _calculate_deposit(price: Decimal) -> Decimal:
    return percentage_of(price, settings.BOOKING_DEPOSIT_PERCENT)


def create_booking(*, client, venue: Venue, start_time, end_time) -> BookingCreationResult:
    """
    Создаёт бронь и сразу резервирует задаток (roadmap 2.2: "клиент бронирует
    и резервирует, не списывает"). Двойное бронирование одного слота
    физически исключено ExclusionConstraint в БД (apps/bookings/models.py) —
    здесь просто ловим IntegrityError и превращаем в понятную ошибку домена.

    После коммита транзакции запускает гибридное подтверждение: уведомляет
    администраторов площадки (push+SMS+звонок) и планирует Celery-таймеры
    напоминания и автоотмены (roadmap 2.2).
    """
    now = timezone.now()
    if start_time <= now:
        raise BookingWindowInvalid("Начало брони должно быть в будущем.")
    if end_time <= start_time:
        raise BookingWindowInvalid("Окончание брони должно быть позже начала.")

    price = _calculate_price(venue, start_time, end_time)
    deposit_amount = _calculate_deposit(price)
    confirmation_deadline = now + timezone.timedelta(minutes=settings.BOOKING_CONFIRMATION_TIMEOUT_MINUTES)

    try:
        with transaction.atomic():
            booking = Booking.objects.create(
                venue=venue,
                client=client,
                start_time=start_time,
                end_time=end_time,
                status=BookingStatus.PENDING_CONFIRMATION,
                price=price,
                deposit_amount=deposit_amount,
                confirmation_deadline=confirmation_deadline,
            )

            provider = get_payment_provider()
            result = provider.hold(reference=f"booking-{booking.pk}", amount=deposit_amount)
            if not result.success:
                # Откатываем всю транзакцию — без задатка брони не создаём.
                raise SlotUnavailable(f"Не удалось зарезервировать задаток: {result.error}")

            payment = Payment.objects.create(
                booking=booking,
                provider=default_provider_name(),
                strategy=provider.strategy,
                amount=deposit_amount,
                status=PaymentStatus.HELD,
                external_id=result.external_id,
            )

            transaction.on_commit(lambda: _schedule_confirmation_flow(booking.id))
    except IntegrityError as exc:
        raise SlotUnavailable("Этот слот уже занят другой бронью.") from exc

    return BookingCreationResult(booking=booking, payment=payment, payment_redirect_url=result.redirect_url)


def _schedule_confirmation_flow(booking_id: int) -> None:
    # Импорт внутри функции — избегаем цикла bookings.services <-> bookings.tasks.
    from .tasks import expire_pending_booking, send_confirmation_reminder

    booking = Booking.objects.select_related("venue").get(pk=booking_id)
    notify_venue_admins_of_new_booking(booking)

    timeout_minutes = settings.BOOKING_CONFIRMATION_TIMEOUT_MINUTES
    reminder_before = settings.BOOKING_CONFIRMATION_REMINDER_BEFORE_MINUTES
    reminder_delay = max(timeout_minutes - reminder_before, 0) * 60
    send_confirmation_reminder.apply_async(args=[booking_id], countdown=reminder_delay)
    expire_pending_booking.apply_async(args=[booking_id], countdown=timeout_minutes * 60)


def _ensure_is_venue_admin(user, venue) -> None:
    is_admin = VenueMembership.objects.filter(
        venue=venue, user=user, role=VenueRole.VENUE_ADMIN, is_active=True
    ).exists()
    if not is_admin:
        raise NotVenueAdmin("Пользователь не является администратором этой площадки.")


def _settle_payment(payment: Payment, *, action: str) -> None:
    """
    action: "capture" (бронь подтверждена) или "release" (отклонена/
    истекла/отменена — снятие холда либо автовозврат, в зависимости от
    payment.strategy; вызывающему коду разница не важна).

    Действует только на платёж в статусе HELD — если он уже FAILED
    (например провайдер асинхронно сообщил о неудаче через вебхук раньше,
    чем сработал expire_booking — см. apps.payments.views.freedompay_result),
    вызывать capture/release на нём нечего: резерва, который можно было бы
    снять или списать, у провайдера просто нет.
    """
    if payment.status != PaymentStatus.HELD:
        return

    provider = get_payment_provider(payment.strategy)
    if action == "capture":
        result = provider.capture(payment=payment)
        new_status = PaymentStatus.CAPTURED
    else:
        result = provider.release(payment=payment)
        new_status = (
            PaymentStatus.RELEASED if payment.strategy == PaymentStrategy.HOLD_CAPTURE else PaymentStatus.REFUNDED
        )

    # Заглушки провайдера всегда success=True; реальный провайдер может
    # вернуть ошибку — фиксируем как FAILED и не блокируем смену статуса
    # брони этим (бронь не должна зависнуть из-за сбоя на стороне платёжки),
    # но это место потребует ручного разбора/алертинга после интеграции.
    payment.status = new_status if result.success else PaymentStatus.FAILED
    if result.external_id:
        payment.external_id = result.external_id
    if action == "capture" and result.success:
        # Комиссия платформы (roadmap, раздел 3) — только с реально списанной
        # суммы; со снятого резерва/возврата/неудачного списания комиссии не бывает.
        payment.commission_amount = payment.booking.venue.commission_on(payment.amount)
    payment.settled_at = timezone.now()
    payment.save(update_fields=["status", "external_id", "commission_amount", "settled_at"])


def confirm_booking(*, booking_id: int, admin_user, channel: str = NotificationChannel.PUSH) -> Booking:
    with transaction.atomic():
        # payment не в select_related: Postgres запрещает FOR UPDATE через
        # LEFT OUTER JOIN на nullable-стороне (reverse OneToOne) — блокируем
        # Booking и Payment отдельными запросами в одной транзакции.
        booking = Booking.objects.select_for_update().select_related("venue").get(pk=booking_id)
        _ensure_is_venue_admin(admin_user, booking.venue)
        if booking.status != BookingStatus.PENDING_CONFIRMATION:
            raise BookingAlreadyResolved(f"Бронь уже в статусе «{booking.get_status_display()}».")
        payment = Payment.objects.select_for_update().get(booking_id=booking_id)

        now = timezone.now()
        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_at = now
        booking.save(update_fields=["status", "confirmed_at", "updated_at"])

        _settle_payment(payment, action="capture")

        NotificationLog.objects.filter(
            booking=booking, channel=channel, status=NotificationStatus.SENT
        ).update(status=NotificationStatus.CONFIRMED_VIA, responded_at=now)

        # Игра подтверждена и физически начнётся — планируем предложение
        # продлить ближе к концу слота (roadmap 2.3). Работает и для брони-
        # продления тоже (тем самым продления можно "цеплять" друг за друга).
        transaction.on_commit(lambda: _schedule_extension_prompt(booking.id))

    return booking


def decline_booking(*, booking_id: int, admin_user, channel: str = NotificationChannel.PUSH) -> Booking:
    with transaction.atomic():
        booking = Booking.objects.select_for_update().select_related("venue", "client").get(pk=booking_id)
        _ensure_is_venue_admin(admin_user, booking.venue)
        if booking.status != BookingStatus.PENDING_CONFIRMATION:
            raise BookingAlreadyResolved(f"Бронь уже в статусе «{booking.get_status_display()}».")
        payment = Payment.objects.select_for_update().get(booking_id=booking_id)

        now = timezone.now()
        booking.status = BookingStatus.DECLINED
        booking.declined_at = now
        booking.save(update_fields=["status", "declined_at", "updated_at"])

        _settle_payment(payment, action="release")

        NotificationLog.objects.filter(
            booking=booking, channel=channel, status=NotificationStatus.SENT
        ).update(status=NotificationStatus.CONFIRMED_VIA, responded_at=now)

    notify_client_slot_unavailable(booking)
    return booking


def expire_booking(booking_id: int) -> Booking | None:
    """
    Вызывается Celery-таймером по истечении окна ожидания решения — как для
    обычной брони (ждём админа), так и для продления (ждём клиента, roadmap
    2.3: "если он не ответил и не продлил — слот открывается для новых
    броней"). Если решение уже принято вручную — select_for_update()
    гарантирует, что мы увидим актуальный статус (гонка с confirm/decline
    разрешается блокировкой строки в БД), и здесь просто ничего не делаем.
    """
    with transaction.atomic():
        try:
            booking = Booking.objects.select_for_update().select_related("client", "venue").get(pk=booking_id)
        except Booking.DoesNotExist:
            return None
        if booking.status not in AWAITING_DECISION_STATUSES:
            return booking
        payment = Payment.objects.select_for_update().get(booking_id=booking_id)

        booking.status = BookingStatus.EXPIRED
        booking.save(update_fields=["status", "updated_at"])
        _settle_payment(payment, action="release")

    if booking.extended_from_id is None:
        # "Слот недоступен, попробуйте другое время" осмысленно только для
        # новой брони — для непродлённого продления это не ошибка, а обычный
        # исход (человек просто доиграл и ушёл), отдельного уведомления не шлём.
        notify_client_slot_unavailable(booking)
    return booking


def offer_extension(booking_id: int) -> Booking | None:
    """
    roadmap 2.3: за BOOKING_EXTENSION_PROMPT_BEFORE_MINUTES до конца
    подтверждённого слота — предлагаем клиенту продлить. Технически это
    создание обычной брони на следующий час в статусе EXTENSION_PENDING:
    она занимает слот наравне с CONFIRMED (см. OCCUPYING_BOOKING_STATUSES),
    поэтому другой клиент физически не может перехватить время, пока
    текущий игрок решает — тот же ExclusionConstraint, что и для 2.2.
    """
    with transaction.atomic():
        try:
            booking = Booking.objects.select_for_update().select_related("venue", "client").get(pk=booking_id)
        except Booking.DoesNotExist:
            return None
        if booking.status != BookingStatus.CONFIRMED:
            return None  # игра уже не подтверждена/отменена — продлевать нечего
        if Booking.objects.filter(extended_from_id=booking.id).exists():
            return None  # предложение уже отправлено (защита от повторного запуска таска)

        extension_start = booking.end_time
        extension_end = booking.end_time + timezone.timedelta(minutes=settings.BOOKING_EXTENSION_DURATION_MINUTES)
        price = _calculate_price(booking.venue, extension_start, extension_end)
        deposit_amount = _calculate_deposit(price)

        try:
            extension = Booking.objects.create(
                venue=booking.venue,
                client=booking.client,
                start_time=extension_start,
                end_time=extension_end,
                status=BookingStatus.EXTENSION_PENDING,
                price=price,
                deposit_amount=deposit_amount,
                confirmation_deadline=booking.end_time,
                extended_from=booking,
            )
            provider = get_payment_provider()
            result = provider.hold(reference=f"booking-{extension.pk}", amount=deposit_amount)
            if not result.success:
                raise SlotUnavailable(f"Не удалось зарезервировать задаток продления: {result.error}")
            Payment.objects.create(
                booking=extension,
                provider=default_provider_name(),
                strategy=provider.strategy,
                amount=deposit_amount,
                status=PaymentStatus.HELD,
                external_id=result.external_id,
            )
        except IntegrityError:
            # Следующий час уже занят другой бронью (редкий случай — площадка
            # заблокирована организатором и т.п.) — продлить нельзя, тихо выходим.
            return None

        transaction.on_commit(lambda: _finalize_extension_offer(extension.id))

    return extension


def _finalize_extension_offer(extension_id: int) -> None:
    from .tasks import expire_pending_booking

    extension = Booking.objects.select_related("client", "venue").get(pk=extension_id)
    notify_client_extension_offer(extension)

    delay = max((extension.confirmation_deadline - timezone.now()).total_seconds(), 0)
    expire_pending_booking.apply_async(args=[extension_id], countdown=delay)


def _schedule_extension_prompt(booking_id: int) -> None:
    from .tasks import prompt_extension

    booking = Booking.objects.get(pk=booking_id)
    prompt_time = booking.end_time - timezone.timedelta(minutes=settings.BOOKING_EXTENSION_PROMPT_BEFORE_MINUTES)
    delay = max((prompt_time - timezone.now()).total_seconds(), 0)
    prompt_extension.apply_async(args=[booking_id], countdown=delay)


def confirm_extension(*, booking_id: int, client) -> Booking:
    """
    В отличие от обычной брони, продление подтверждает сам клиент — без
    участия администратора площадки (roadmap 2.3 не упоминает подтверждение
    админом для продления: игрок уже физически на площадке).
    """
    with transaction.atomic():
        booking = Booking.objects.select_for_update().select_related("venue").get(pk=booking_id)
        if booking.client_id != client.id:
            raise NotBookingOwner("Это не ваша бронь.")
        if booking.status != BookingStatus.EXTENSION_PENDING:
            raise BookingAlreadyResolved(f"Бронь уже в статусе «{booking.get_status_display()}».")
        payment = Payment.objects.select_for_update().get(booking_id=booking_id)

        now = timezone.now()
        booking.status = BookingStatus.CONFIRMED
        booking.confirmed_at = now
        booking.save(update_fields=["status", "confirmed_at", "updated_at"])

        _settle_payment(payment, action="capture")

        # Продление можно продлить ещё раз — планируем следующее предложение.
        transaction.on_commit(lambda: _schedule_extension_prompt(booking.id))

    return booking


def decline_extension(*, booking_id: int, client) -> Booking:
    """Клиент явно отказался продлевать — освобождаем слот сразу, не дожидаясь таймаута."""
    with transaction.atomic():
        booking = Booking.objects.select_for_update().get(pk=booking_id)
        if booking.client_id != client.id:
            raise NotBookingOwner("Это не ваша бронь.")
        if booking.status != BookingStatus.EXTENSION_PENDING:
            raise BookingAlreadyResolved(f"Бронь уже в статусе «{booking.get_status_display()}».")
        payment = Payment.objects.select_for_update().get(booking_id=booking_id)

        booking.status = BookingStatus.CANCELLED
        booking.save(update_fields=["status", "updated_at"])

        _settle_payment(payment, action="release")

    return booking
