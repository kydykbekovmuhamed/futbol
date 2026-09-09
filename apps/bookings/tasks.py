from celery import shared_task


@shared_task
def send_confirmation_reminder(booking_id: int) -> None:
    """
    За N минут до истечения таймера — повторное уведомление админам
    (roadmap 2.2). Если бронь уже подтверждена/отклонена/истекла —
    напоминать не о чем, тихо выходим.
    """
    from apps.notifications.services import notify_venue_admins_confirmation_reminder

    from .models import Booking, BookingStatus

    try:
        booking = Booking.objects.select_related("venue").get(pk=booking_id)
    except Booking.DoesNotExist:
        return
    if booking.status != BookingStatus.PENDING_CONFIRMATION:
        return
    notify_venue_admins_confirmation_reminder(booking)


@shared_task
def expire_pending_booking(booking_id: int) -> None:
    """Срабатывает по истечении confirmation_deadline — см. services.expire_booking."""
    from .services import expire_booking

    expire_booking(booking_id)


@shared_task
def prompt_extension(booking_id: int) -> None:
    """
    Срабатывает за BOOKING_EXTENSION_PROMPT_BEFORE_MINUTES до конца
    подтверждённого слота — см. services.offer_extension (roadmap 2.3).
    """
    from .services import offer_extension

    offer_extension(booking_id)
