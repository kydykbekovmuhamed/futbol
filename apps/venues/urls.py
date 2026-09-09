from django.urls import path

from . import views

app_name = "venues"

urlpatterns = [
    path("", views.VenueListView.as_view(), name="list"),
    path("available/", views.VenueAvailabilityView.as_view(), name="available"),
]
