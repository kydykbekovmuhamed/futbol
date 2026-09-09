from apps.accounts.models import User
from apps.venues.models import VenueRole

from .models import NotificationChannel, NotificationLog, NotificationStatus
from .providers import get_notification_provider


def _venue_admins(venue):
    return User.objects.filter(
        venue_memberships__venue=venue,
        venue_memberships__role=VenueRole.VENUE_ADMIN,
        venue_memberships__is_active=True,
    ).distinct()


def _dispatch_all_channels(booking, recipient, title, body):
    """
    roadmap 2.2: администратору площадки одновременно приходит push-
    уведомление и автозвонок/SMS — бьём во все три канала сразу, подтвердить
    можно любым (см. apps.bookings.services.confirm_booking).
    """
    provider = get_notification_provider()
    channel_senders = {
        NotificationChannel.PUSH: lambda: provider.send_push(phone=recipient.phone, title=title, body=body),
        NotificationChannel.SMS: lambda: provider.send_sms(phone=recipient.phone, text=f"{title}: {body}"),
        NotificationChannel.CALL: lambda: provider.initiate_call(phone=recipient.phone, text=f"{title}. {body}"),
    }
    for channel, send in channel_senders.items():
        result = send()
        NotificationLog.objects.create(
            booking=booking,
            recipient=recipient,
            channel=channel,
            status=NotificationStatus.SENT if result.success else NotificationStatus.FAILED,
        )


def notify_venue_admins_of_new_booking(booking):
    title = "Новая бронь"
    body = (
        f"{booking.venue.name}, {booking.start_time:%d.%m %H:%M}–{booking.end_time:%H:%M}. "
        "Подтвердите в приложении или ответьте на звонок."
    )
    for admin in _venue_admins(booking.venue):
        _dispatch_all_channels(booking, admin, title, body)


def notify_venue_admins_confirmation_reminder(booking):
    title = "Бронь не подтверждена"
    body = f"{booking.venue.name}, {booking.start_time:%d.%m %H:%M} — осталось 2 минуты, иначе слот освободится."
    for admin in _venue_admins(booking.venue):
        _dispatch_all_channels(booking, admin, title, body)


def notify_client_extension_offer(booking):
    """roadmap 2.3: push клиенту "продлить ещё на час?" за N минут до конца слота."""
    provider = get_notification_provider()
    provider.send_push(
        phone=booking.client.phone,
        title="Продлить игру?",
        body=f"{booking.venue.name}: продлить ещё на час, до {booking.end_time:%H:%M}?",
    )


def notify_client_slot_unavailable(booking):
    """
    Единое сообщение клиенту независимо от причины — отклонил админ или не
    ответил (roadmap, раздел 8, вопрос 1: в UI клиента не различаем, в БД
    статусы declined/expired раздельные для внутренней аналитики).
    """
    provider = get_notification_provider()
    provider.send_push(
        phone=booking.client.phone,
        title="Слот недоступен",
        body="Попробуйте выбрать другое время или площадку.",
    )
