import django_filters

from .models import Venue


class VenueFilter(django_filters.FilterSet):
    district = django_filters.CharFilter(field_name="district", lookup_expr="icontains")
    price_min = django_filters.NumberFilter(field_name="price_per_hour", lookup_expr="gte")
    price_max = django_filters.NumberFilter(field_name="price_per_hour", lookup_expr="lte")

    class Meta:
        model = Venue
        fields = ["district", "surface_type", "field_size", "price_min", "price_max"]
