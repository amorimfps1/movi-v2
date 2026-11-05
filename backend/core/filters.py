from django.db.models import Exists, OuterRef
from django_filters import rest_framework as filters

from .models import Person


def with_person_links(queryset):
    from billing.models import Enrollment
    from ecowork.models import Order
    return queryset.annotate(
        has_enrollments=Exists(Enrollment.objects.filter(student_id=OuterRef('pk'))),
        has_ecowork=Exists(Order.objects.filter(person_id=OuterRef('pk'))),
    )


class PersonFilter(filters.FilterSet):
    has_enrollments = filters.BooleanFilter()
    has_ecowork = filters.BooleanFilter()

    class Meta:
        model = Person
        fields = ['archived', 'has_enrollments', 'has_ecowork']
