from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("freedompay/check/", views.freedompay_check, name="freedompay-check"),
    path("freedompay/result/", views.freedompay_result, name="freedompay-result"),
]
