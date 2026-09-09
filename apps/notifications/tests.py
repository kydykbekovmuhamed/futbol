"""
Реальных ключей Firebase/Infobip нет — тесты проверяют то, что можно
проверить без них: выбор провайдера по наличию credentials (без реального
обращения к SDK/API), регистрацию device token, и форму HTTP-запроса к
Infobip через мок requests.post (аналогично apps/payments/tests.py).
"""

from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User

from .device_tokens import register_device_token, unregister_device_token
from .firebase import FirebaseNotificationProvider
from .infobip import InfobipNotificationProvider
from .models import DevicePlatform, DeviceToken
from .providers import MockNotificationProvider, get_notification_provider

INFOBIP_SETTINGS = dict(INFOBIP_API_KEY="test-key", INFOBIP_BASE_URL="https://xxxxx.api.infobip.com")


class DeviceTokenServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(phone="+996700600001", password="x")
        self.other_user = User.objects.create_user(phone="+996700600002", password="x")

    def test_register_creates_token(self):
        register_device_token(user=self.user, token="tok-1", platform=DevicePlatform.ANDROID)

        token = DeviceToken.objects.get(token="tok-1")
        self.assertEqual(token.user, self.user)
        self.assertTrue(token.is_active)

    def test_register_reassigns_token_to_new_user(self):
        """Переустановка приложения на другой аккаунт на том же устройстве — токен переезжает, не дублируется."""
        register_device_token(user=self.user, token="tok-1", platform=DevicePlatform.ANDROID)

        register_device_token(user=self.other_user, token="tok-1", platform=DevicePlatform.ANDROID)

        self.assertEqual(DeviceToken.objects.filter(token="tok-1").count(), 1)
        self.assertEqual(DeviceToken.objects.get(token="tok-1").user, self.other_user)

    def test_unregister_deactivates(self):
        register_device_token(user=self.user, token="tok-1", platform=DevicePlatform.IOS)

        unregister_device_token(user=self.user, token="tok-1")

        self.assertFalse(DeviceToken.objects.get(token="tok-1").is_active)

    def test_unregister_by_wrong_user_is_noop(self):
        register_device_token(user=self.user, token="tok-1", platform=DevicePlatform.IOS)

        unregister_device_token(user=self.other_user, token="tok-1")

        self.assertTrue(DeviceToken.objects.get(token="tok-1").is_active)


class DeviceTokenViewsTests(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(phone="+996700600003", password="x")
        self.client.force_authenticate(user=self.user)

    def test_register_via_api(self):
        response = self.client.post(
            "/api/notifications/device-tokens/", {"token": "tok-api-1", "platform": "android"}
        )
        self.assertEqual(response.status_code, 201)
        self.assertTrue(DeviceToken.objects.filter(token="tok-api-1", user=self.user).exists())

    def test_unregister_via_api(self):
        register_device_token(user=self.user, token="tok-api-2", platform=DevicePlatform.WEB)

        response = self.client.post("/api/notifications/device-tokens/unregister/", {"token": "tok-api-2"})

        self.assertEqual(response.status_code, 204)
        self.assertFalse(DeviceToken.objects.get(token="tok-api-2").is_active)


class ProviderSelectionTests(TestCase):
    def test_defaults_to_mock_for_both_channels(self):
        with override_settings(FIREBASE_CREDENTIALS_PATH="", INFOBIP_API_KEY="", INFOBIP_BASE_URL=""):
            provider = get_notification_provider()
        self.assertIsInstance(provider._push, MockNotificationProvider)
        self.assertIsInstance(provider._sms_call, MockNotificationProvider)

    @override_settings(FIREBASE_CREDENTIALS_PATH="/fake/path/service-account.json")
    def test_uses_firebase_for_push_when_configured(self):
        provider = get_notification_provider()
        self.assertIsInstance(provider._push, FirebaseNotificationProvider)

    @override_settings(**INFOBIP_SETTINGS)
    def test_uses_infobip_for_sms_and_call_when_configured(self):
        provider = get_notification_provider()
        self.assertIsInstance(provider._sms_call, InfobipNotificationProvider)

    def test_firebase_push_without_device_tokens_fails_gracefully(self):
        """Даже без реальных Firebase-креденшлов: нет токена устройства -> явная ошибка, не исключение."""
        result = FirebaseNotificationProvider().send_push(phone="+996700699999", title="t", body="b")
        self.assertFalse(result.success)
        self.assertEqual(result.error, "no_device_tokens")


class InfobipProviderTests(TestCase):
    """Мокаем requests.post — проверяем форму запроса и разбор ответа, не сеть."""

    @override_settings(**INFOBIP_SETTINGS, INFOBIP_SENDER="FutbolApp")
    @patch("apps.notifications.infobip.requests.post")
    def test_send_sms_success(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.raise_for_status = Mock()
        mock_post.return_value.json.return_value = {
            "messages": [{"messageId": "abc123", "status": {"groupName": "PENDING"}}]
        }

        result = InfobipNotificationProvider().send_sms(phone="+996700700001", text="Код: 123456")

        self.assertTrue(result.success)
        self.assertEqual(result.external_id, "abc123")
        sent_json = mock_post.call_args[1]["json"]
        self.assertEqual(sent_json["messages"][0]["destinations"][0]["to"], "996700700001")
        self.assertEqual(sent_json["messages"][0]["text"], "Код: 123456")

    @override_settings(**INFOBIP_SETTINGS)
    @patch("apps.notifications.infobip.requests.post")
    def test_send_sms_rejected_status(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.raise_for_status = Mock()
        mock_post.return_value.json.return_value = {
            "messages": [{"messageId": "abc123", "status": {"groupName": "REJECTED"}}]
        }

        result = InfobipNotificationProvider().send_sms(phone="+996700700001", text="Код: 123456")

        self.assertFalse(result.success)

    @override_settings(**INFOBIP_SETTINGS)
    @patch("apps.notifications.infobip.requests.post")
    def test_initiate_call_requests_dtmf(self, mock_post):
        mock_post.return_value = Mock(status_code=200)
        mock_post.return_value.raise_for_status = Mock()
        mock_post.return_value.json.return_value = {"bulkId": "bulk-1", "messages": [{"messageId": "call-1"}]}

        result = InfobipNotificationProvider().initiate_call(phone="+996700700002", text="Подтвердите бронь")

        self.assertTrue(result.success)
        sent_json = mock_post.call_args[1]["json"]
        self.assertEqual(sent_json["messages"][0]["maxDtmf"], 1)
        called_url = mock_post.call_args[0][0]
        self.assertTrue(called_url.endswith("/tts/3/advanced"))

    @override_settings(**INFOBIP_SETTINGS)
    @patch("apps.notifications.infobip.requests.post")
    def test_network_error_reported_not_raised(self, mock_post):
        import requests

        mock_post.side_effect = requests.ConnectionError("timeout")

        result = InfobipNotificationProvider().send_sms(phone="+996700700003", text="x")

        self.assertFalse(result.success)
