from django.urls import path

from . import views

app_name = "tournaments"

urlpatterns = [
    path("", views.TournamentListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", views.TournamentDetailView.as_view(), name="detail"),
    path("<int:pk>/registrations/", views.TournamentRegistrationsView.as_view(), name="registrations"),
    path("<int:pk>/standings/", views.TournamentStandingsView.as_view(), name="standings"),
    path("<int:pk>/matches/", views.TournamentMatchListCreateView.as_view(), name="matches"),
    path(
        "registrations/<int:pk>/cancel/",
        views.TournamentRegistrationCancelView.as_view(),
        name="registration-cancel",
    ),
    path(
        "registrations/<int:pk>/disqualify/",
        views.TournamentRegistrationDisqualifyView.as_view(),
        name="registration-disqualify",
    ),
    path(
        "matches/<int:pk>/report-result/",
        views.TournamentMatchReportResultView.as_view(),
        name="match-report-result",
    ),
]
