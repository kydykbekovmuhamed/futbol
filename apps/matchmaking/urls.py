from django.urls import path

from . import views

app_name = "matchmaking"

urlpatterns = [
    path("opponent-requests/", views.OpponentRequestListCreateView.as_view(), name="opponent-list-create"),
    path("opponent-requests/<int:pk>/match/", views.OpponentRequestMatchView.as_view(), name="opponent-match"),
    path("opponent-requests/<int:pk>/cancel/", views.OpponentRequestCancelView.as_view(), name="opponent-cancel"),
    path("player-requests/", views.PlayerRequestListCreateView.as_view(), name="player-list-create"),
    path("player-requests/<int:pk>/apply/", views.PlayerRequestApplyView.as_view(), name="player-apply"),
    path(
        "player-requests/<int:pk>/applications/",
        views.PlayerRequestApplicationsView.as_view(),
        name="player-applications",
    ),
    path(
        "applications/<int:pk>/accept/",
        views.PlayerApplicationAcceptView.as_view(),
        name="application-accept",
    ),
    path(
        "applications/<int:pk>/decline/",
        views.PlayerApplicationDeclineView.as_view(),
        name="application-decline",
    ),
]
