from .models import DeviceToken


def register_device_token(*, user, token: str, platform: str) -> DeviceToken:
    """
    upsert по токену: если тот же токен раньше принадлежал другому
    пользователю (переустановка приложения на устройстве под другим
    аккаунтом) — переназначаем на текущего, а не плодим дубликаты.
    """
    obj, _created = DeviceToken.objects.update_or_create(
        token=token, defaults={"user": user, "platform": platform, "is_active": True}
    )
    return obj


def unregister_device_token(*, user, token: str) -> None:
    DeviceToken.objects.filter(token=token, user=user).update(is_active=False)
