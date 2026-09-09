from django.urls import path

from . import views

app_name = "community"

urlpatterns = [
    path("feed/", views.ActivityFeedView.as_view(), name="feed"),
    path("feed/<int:pk>/mark-read/", views.ActivityEventMarkReadView.as_view(), name="feed-mark-read"),
    path("challenges/", views.ChallengeListCreateView.as_view(), name="challenges"),
    path("challenges/<int:pk>/accept/", views.ChallengeAcceptView.as_view(), name="challenge-accept"),
    path("challenges/<int:pk>/decline/", views.ChallengeDeclineView.as_view(), name="challenge-decline"),
    path("challenges/<int:pk>/cancel/", views.ChallengeCancelView.as_view(), name="challenge-cancel"),
    path("news/", views.NewsListView.as_view(), name="news"),
    path("local-schedule/", views.LocalScheduleView.as_view(), name="local-schedule"),
    path("teams/<int:pk>/subscribe/", views.TeamSubscribeView.as_view(), name="team-subscribe"),
    path("teams/<int:pk>/extended-stats/", views.TeamExtendedStatsView.as_view(), name="team-extended-stats"),
]
