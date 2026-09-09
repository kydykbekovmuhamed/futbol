"""
Реальные SMS и автозвонок через Infobip.

Требует settings.INFOBIP_API_KEY и settings.INFOBIP_BASE_URL (у каждого
аккаунта Infobip свой базовый URL, выдаётся при регистрации). Пока не
заданы — используется MockNotificationProvider.

Проверено по официальной документации Infobip (2026-09-09):
- SMS (`sms/2/text/advanced`): запрос/ответ подтверждены целиком —
  https://www.infobip.com/docs/sms/sms-over-api, формат ответа
  {"messages": [{"messageId": ..., "status": {"groupName": "PENDING", ...}}]}.
- Звонок (`tts/3/advanced`): запрос подтверждён, включая DTMF-параметры
  (`maxDtmf`, `dtmfTimeout`) — Infobip зачитывает текст и умеет принимать
  нажатие клавиши.

НЕ ДО КОНЦА СДЕЛАНО (важно прочитать перед включением в проде — см. также
CLAUDE.md): roadmap 2.2 хочет "подтверждение звонком" (админ отвечает на
звонок = бронь подтверждена). Запрос на звонок с DTMF-параметрами ниже
реализован и должен сработать, но КУДА и В КАКОМ ВИДЕ Infobip присылает
результат нажатия клавиши (webhook `notifyUrl`, точная форма payload) я
не смог подтвердить однозначно по открытой документации — везде, где
описан DTMF, либо не показан payload обратного вызова, либо описание
относится к более сложному продукту Calls API (call flow, отдельная
настройка в консоли Infobip), а не к простому tts/3/advanced. Прежде чем
полагаться на реальное автоподтверждение звонком — обязательно проверить
это в песочнице Infobip с реальным аккаунтом и, если формат не совпадёт,
поправить InfobipCallResultView ниже (сейчас она — заготовка, логирует
входящее тело запроса как есть, но не парсит его под конкретные поля).
Пока это не проверено, продакшен-подтверждение брони работает через
push+SMS (тап в приложении), а не через реальное нажатие клавиши на звонке.
"""

import logging

import requests
from django.conf import settings

from .providers import NotificationProvider, NotificationResult

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "Authorization": f"App {settings.INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


class InfobipNotificationProvider(NotificationProvider):
    def send_push(self, *, phone: str, title: str, body: str) -> NotificationResult:
        raise NotImplementedError("Infobip здесь не отправляет push — см. apps.notifications.firebase.")

    def send_sms(self, *, phone: str, text: str) -> NotificationResult:
        url = f"{settings.INFOBIP_BASE_URL.rstrip('/')}/sms/2/text/advanced"
        payload = {
            "messages": [
                {
                    "from": settings.INFOBIP_SENDER,
                    "destinations": [{"to": phone.lstrip("+")}],
                    "text": text,
                }
            ]
        }
        try:
            response = requests.post(url, json=payload, headers=_headers(), timeout=15)
            response.raise_for_status()
            data = response.json()
            message = data["messages"][0]
        except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
            logger.error("Infobip SMS error для %s: %s", phone, exc)
            return NotificationResult(success=False, error=str(exc))

        group_name = message.get("status", {}).get("groupName", "")
        return NotificationResult(
            success=group_name in ("PENDING", "DELIVERED"),
            external_id=message.get("messageId", ""),
            error="" if group_name in ("PENDING", "DELIVERED") else f"Infobip status: {group_name}",
        )

    def initiate_call(self, *, phone: str, text: str) -> NotificationResult:
        url = f"{settings.INFOBIP_BASE_URL.rstrip('/')}/tts/3/advanced"
        payload = {
            "messages": [
                {
                    "from": settings.INFOBIP_SENDER,
                    "destinations": [{"to": phone.lstrip("+")}],
                    "text": text,
                    "language": "ru",
                    # Запрашиваем нажатие клавиши — см. предупреждение в
                    # docstring модуля про неподтверждённый формат webhook-результата.
                    "maxDtmf": 1,
                    "dtmfTimeout": 10,
                }
            ]
        }
        try:
            response = requests.post(url, json=payload, headers=_headers(), timeout=15)
            response.raise_for_status()
            data = response.json()
            message = data["messages"][0]
        except (requests.RequestException, KeyError, IndexError, ValueError) as exc:
            logger.error("Infobip TTS-звонок error для %s: %s", phone, exc)
            return NotificationResult(success=False, error=str(exc))

        return NotificationResult(success=True, external_id=message.get("messageId", data.get("bulkId", "")))
