from django.urls import path

from . import views

app_name = "teams"

urlpatterns = [
    path("", views.TeamListCreateView.as_view(), name="list-create"),
    path("<int:pk>/", views.TeamDetailView.as_view(), name="detail"),
    path("<int:pk>/members/", views.TeamMembersView.as_view(), name="members"),
    path("<int:pk>/join/", views.TeamJoinView.as_view(), name="join"),
    path("<int:pk>/leave/", views.TeamLeaveView.as_view(), name="leave"),
    path("matches/", views.MatchListCreateView.as_view(), name="matches"),
    path("matches/<int:pk>/report-result/", views.MatchReportResultView.as_view(), name="match-report-result"),
]
