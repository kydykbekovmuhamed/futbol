import os
import sys

import django

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from apps.accounts.models import User

user = User.objects.filter(is_superuser=True).first()
if not user:
    print("NO SUPERUSER FOUND")
    sys.exit(1)

client = Client(SERVER_NAME="127.0.0.1")
client.force_login(user)

urls = [
    "/admin/",
    "/admin/bookings/booking/",
    "/admin/venues/venue/",
]
if True:
    from apps.venues.models import Venue

    v = Venue.objects.first()
    if v:
        urls.append(f"/admin/venues/venue/{v.pk}/change/")

for url in urls:
    resp = client.get(url)
    print(url, "->", resp.status_code)
    if resp.status_code >= 500:
        content = resp.content.decode("utf-8", errors="replace")
        print(content[:3000])
