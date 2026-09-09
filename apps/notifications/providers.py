"""
Абстракция над каналами уведомлений: push / SMS / автозвонок.

Провайдер принимает телефон строкой, а не объект User: SMS/звонок реально
адресуются номеру, а не аккаунту в нашей системе — это верно и когда
аккаунта ещё не существует (например, при запросе OTP на регистрации).

get_notification_provider() выбирает реализацию НЕЗАВИСИМО по каналам:
push — Firebase, если задан FIREBASE_CREDENTIALS_PATH, иначе mock; SMS/
звонок — Infobip, если заданы INFOBIP_API_KEY/INFOBIP_BASE_URL, иначе mock.
Реальные реализации — apps.notifications.firebase, apps.notifications.infobip
(про их ограничения и что не протестировано вживую — см. docstring там же).
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass
class NotificationResult:
    success: bool
    error: str = ""
    external_id: str = ""


class NotificationProvider(ABC):
    @abstractmethod
    def send_push(self, *, phone: str, title: str, body: str) -> NotificationResult: ...

    @abstractmethod
    def send_sms(self, *, phone: str, text: str) -> NotificationResult: ...

    @abstractmethod
    def initiate_call(self, *, phone: str, text: str) -> NotificationResult: ...


class MockNotificationProvider(NotificationProvider):
    def send_push(self, *, phone, title, body):
        logger.info("[MOCK PUSH] -> %s: %s / %s", phone, title, body)
        return NotificationResult(success=True)

    def send_sms(self, *, phone, text):
        logger.info("[MOCK SMS] -> %s: %s", phone, text)
        return NotificationResult(success=True)

    def initiate_call(self, *, phone, text):
        logger.info("[MOCK CALL] -> %s: %s", phone, text)
        return NotificationResult(success=True)


class CompositeNotificationProvider(NotificationProvider):
    """Роутит push на один провайдер, sms/call — на другой (см. get_notification_provider)."""

    def __init__(self, push_provider: NotificationProvider, sms_call_provider: NotificationProvider):
        self._push = push_provider
        self._sms_call = sms_call_provider

    def send_push(self, *, phone, title, body):
        return self._push.send_push(phone=phone, title=title, body=body)

    def send_sms(self, *, phone, text):
        return self._sms_call.send_sms(phone=phone, text=text)

    def initiate_call(self, *, phone, text):
        return self._sms_call.initiate_call(phone=phone, text=text)


def _push_provider() -> NotificationProvider:
    if settings.FIREBASE_CREDENTIALS_PATH:
        from .firebase import FirebaseNotificationProvider

        return FirebaseNotificationProvider()
    return MockNotificationProvider()


def _sms_call_provider() -> NotificationProvider:
    if settings.INFOBIP_API_KEY and settings.INFOBIP_BASE_URL:
        from .infobip import InfobipNotificationProvider

        return InfobipNotificationProvider()
    return MockNotificationProvider()


def get_notification_provider() -> NotificationProvider:
    return CompositeNotificationProvider(push_provider=_push_provider(), sms_call_provider=_sms_call_provider())
