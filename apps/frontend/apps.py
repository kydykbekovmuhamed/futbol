from django.apps import AppConfig


class FrontendConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.frontend"
    verbose_name = "Фронтенд"

    def ready(self):
        # apps.frontend стоит последним в INSTALLED_APPS — все ModelAdmin
        # уже зарегистрированы к этому моменту, безопасно патчить admin.site.
        from . import admin_dashboard

        admin_dashboard.install()
