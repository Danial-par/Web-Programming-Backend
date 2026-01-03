import django_filters as filters
from django.contrib.auth import get_user_model

User = get_user_model()


class ContractorFilterSet(filters.FilterSet):
    min_avg_rating = filters.NumberFilter(method="filter_min_avg_rating")
    min_review_count = filters.NumberFilter(method="filter_min_review_count")

    class Meta:
        model = User
        fields = []

    def filter_min_avg_rating(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(avg_rating__gte=value)

    def filter_min_review_count(self, queryset, name, value):
        if value is None:
            return queryset
        return queryset.filter(review_count__gte=value)
