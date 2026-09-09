"""
Абстракция над платёжным провайдером задатка (roadmap, раздел 8, вопрос 2).

Провайдер в Кыргызстане с поддержкой hold (резервирование без списания) ещё
не подтверждён. Бизнес-логика брони (apps.bookings) работает только через
интерфейс PaymentProvider и не знает, какая на самом деле схема у площадки —
настоящий hold (authorize/capture) или списание с автовозвратом. Как только
провайдер определится, здесь появится его реализация — вызывающий код
менять не придётся.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings

from .models import PaymentProviderName, PaymentStrategy


@dataclass
class PaymentResult:
    success: bool
    external_id: str = ""
    error: str = ""
    # Заполняется провайдерами с редиректом на их платёжную страницу
    # (например FreedomPay — см. apps.payments.freedompay) — success=True
    # в этом случае означает "платёж инициирован", а не "деньги реально
    # захолжены": окончательное подтверждение приходит асинхронно через
    # вебхук. Для провайдеров без редиректа (моки) всегда пустая строка.
    redirect_url: str = ""


class PaymentProvider(ABC):
    """
    reference — произвольная строка для логов/сверки у провайдера (номер
    брони, номер регистрации на турнир и т.п.). Провайдер и этот интерфейс
    ничего не знают о Booking/TournamentRegistration — под чем именно
    резервируются деньги, решает вызывающий код (apps.bookings,
    apps.tournaments), а не платёжный слой.
    """

    strategy: str

    @abstractmethod
    def hold(self, *, reference: str, amount) -> PaymentResult:
        """Зарезервировать деньги клиента (не списывая)."""

    @abstractmethod
    def capture(self, *, payment) -> PaymentResult:
        """Резерв подтверждён — зафиксировать платёж."""

    @abstractmethod
    def release(self, *, payment) -> PaymentResult:
        """Резерв отклонён/просрочен/отменён — вернуть деньги клиенту."""


class MockHoldCaptureProvider(PaymentProvider):
    """
    Заглушка на время разработки — эмулирует провайдера с настоящим
    two-phase hold (authorize/capture), например карточный эквайринг.
    """

    strategy = PaymentStrategy.HOLD_CAPTURE

    def hold(self, *, reference, amount):
        return PaymentResult(success=True, external_id=f"mock-hold-{reference}")

    def capture(self, *, payment):
        return PaymentResult(success=True, external_id=payment.external_id)

    def release(self, *, payment):
        return PaymentResult(success=True, external_id=payment.external_id)


class MockChargeAutoRefundProvider(PaymentProvider):
    """
    Заглушка — эмулирует провайдера без hold (например мобильный кошелёк):
    списание сразу в момент резервирования, автовозврат вместо снятия резерва.
    """

    strategy = PaymentStrategy.CHARGE_AUTO_REFUND

    def hold(self, *, reference, amount):
        return PaymentResult(success=True, external_id=f"mock-charge-{reference}")

    def capture(self, *, payment):
        return PaymentResult(success=True, external_id=payment.external_id)

    def release(self, *, payment):
        return PaymentResult(success=True, external_id=payment.external_id)


_MOCK_PROVIDERS_BY_STRATEGY = {
    PaymentStrategy.HOLD_CAPTURE: MockHoldCaptureProvider,
    PaymentStrategy.CHARGE_AUTO_REFUND: MockChargeAutoRefundProvider,
}


def _freedompay_configured() -> bool:
    return bool(settings.FREEDOMPAY_MERCHANT_ID and settings.FREEDOMPAY_SECRET_KEY)


def get_payment_provider(strategy: str | None = None) -> PaymentProvider:
    """
    HOLD_CAPTURE использует FreedomPay, если заданы реальные credentials
    (см. settings.FREEDOMPAY_*, apps.payments.freedompay) — иначе mock.
    CHARGE_AUTO_REFUND провайдера в КР пока не выбрано, всегда mock.
    """
    strategy = strategy or settings.DEFAULT_PAYMENT_STRATEGY
    if strategy == PaymentStrategy.HOLD_CAPTURE and _freedompay_configured():
        from .freedompay import FreedomPayProvider

        return FreedomPayProvider()
    return _MOCK_PROVIDERS_BY_STRATEGY[strategy]()


def default_provider_name() -> str:
    if _freedompay_configured() and settings.DEFAULT_PAYMENT_STRATEGY == PaymentStrategy.HOLD_CAPTURE:
        return PaymentProviderName.FREEDOMPAY
    return PaymentProviderName.MOCK
