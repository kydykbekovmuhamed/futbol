from django.urls import path

from . import views

app_name = "notifications"

urlpatterns = [
    path("device-tokens/", views.DeviceTokenRegisterView.as_view(), name="device-token-register"),
    path("device-tokens/unregister/", views.DeviceTokenUnregisterView.as_view(), name="device-token-unregister"),
]
