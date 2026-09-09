from django.urls import path

from . import views

app_name = "bookings"

urlpatterns = [
    path("", views.MyBookingsView.as_view(), name="my-list"),
    path("create/", views.BookingCreateView.as_view(), name="create"),
    path("<int:pk>/confirm/", views.BookingConfirmView.as_view(), name="confirm"),
    path("<int:pk>/decline/", views.BookingDeclineView.as_view(), name="decline"),
    path("<int:pk>/extension/confirm/", views.BookingExtensionConfirmView.as_view(), name="extension-confirm"),
    path("<int:pk>/extension/decline/", views.BookingExtensionDeclineView.as_view(), name="extension-decline"),
]
