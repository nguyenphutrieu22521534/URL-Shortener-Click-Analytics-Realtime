from django.utils import timezone
from django_filters import rest_framework as filters
from .models import Link

class LinkFilter(filters.FilterSet):
    expired = filters.BooleanFilter(method='filter_expired')

    class Meta:
        model = Link
        fields = ['is_active', 'expired']

    def filter_expired(self, queryset, name, value):
        if value:
            return queryset.expired()
        return queryset.active()
