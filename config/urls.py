from django.contrib import admin
from django.urls import include, path
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", obtain_auth_token, name="api-token-auth"),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/venues/", include("apps.venues.urls")),
    path("api/bookings/", include("apps.bookings.urls")),
    path("api/teams/", include("apps.teams.urls")),
    path("api/matchmaking/", include("apps.matchmaking.urls")),
    path("api/tournaments/", include("apps.tournaments.urls")),
    path("api/payments/", include("apps.payments.urls")),
    path("api/notifications/", include("apps.notifications.urls")),
    path("api/community/", include("apps.community.urls")),
    path("", include("apps.frontend.urls")),
]
