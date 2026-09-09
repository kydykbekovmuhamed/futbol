"""
Реальный push через Firebase Cloud Messaging.

Требует пакет firebase-admin (добавлен в requirements.txt) и
settings.FIREBASE_CREDENTIALS_PATH — путь к service account JSON,
скачиваемому в консоли Firebase (Project settings → Service accounts →
Generate new private key). Пока файл не задан — используется
MockNotificationProvider (см. apps/notifications/providers.get_notification_provider).

НЕ ПРОТЕСТИРОВАНО ВЖИВУЮ: реальных Firebase-credentials ещё нет. Метод
`send_each_for_multicast` — актуальный, не deprecated (проверено на
2026-09-09; более старый `send_multicast` в новых версиях SDK убран).

Push отправляется не на телефон, а на зарегистрированные device token
пользователя (apps.notifications.models.DeviceToken) — если у клиента нет
ни одного активного токена (не открывал приложение/не выдал разрешение на
push), send_push() возвращает success=False, ошибка "no_device_tokens".
"""

import logging

from django.conf import settings

from .providers import NotificationProvider, NotificationResult

logger = logging.getLogger(__name__)

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        import firebase_admin
        from firebase_admin import credentials

        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


class FirebaseNotificationProvider(NotificationProvider):
    def send_push(self, *, phone: str, title: str, body: str) -> NotificationResult:
        from .models import DeviceToken

        tokens = list(DeviceToken.objects.filter(user__phone=phone, is_active=True).values_list("token", flat=True))
        if not tokens:
            logger.info("Нет активных device token для %s — push не отправлен", phone)
            return NotificationResult(success=False, error="no_device_tokens")

        # firebase_admin импортируется только когда реально есть, кому
        # слать — так send_push() не падает без установленного пакета,
        # пока нет ни одного зарегистрированного устройства.
        from firebase_admin import messaging

        _get_firebase_app()
        message = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=tokens,
        )
        response = messaging.send_each_for_multicast(message)

        # FCM явно говорит, какие токены больше не валидны (приложение
        # удалено/токен истёк) — деактивируем их, чтобы не слать в пустоту.
        for token, individual_response in zip(tokens, response.responses):
            if not individual_response.success and _is_unregistered(individual_response.exception):
                DeviceToken.objects.filter(token=token).update(is_active=False)

        return NotificationResult(
            success=response.success_count > 0,
            external_id=f"{response.success_count}/{len(tokens)} доставлено",
            error="" if response.success_count > 0 else "Ни один токен не принял push",
        )

    def send_sms(self, *, phone: str, text: str) -> NotificationResult:
        raise NotImplementedError("Firebase не отправляет SMS — см. apps.notifications.infobip.")

    def initiate_call(self, *, phone: str, text: str) -> NotificationResult:
        raise NotImplementedError("Firebase не совершает звонки — см. apps.notifications.infobip.")


def _is_unregistered(exception) -> bool:
    return exception is not None and getattr(exception, "code", "") == "UNREGISTERED"
