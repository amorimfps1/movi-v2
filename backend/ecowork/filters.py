from django.db.models import Exists, OuterRef
from django.utils import timezone
from django_filters import rest_framework as filters
from rest_framework.exceptions import ValidationError

from .models import Charge, Order, Payment


class OrderFilter(filters.FilterSet):
    status = filters.ChoiceFilter(choices=[(v, v) for v in ['paid', 'open', 'overdue', 'cancelled']], method='defer_charge_filter')
    due_from = filters.DateFilter(method='defer_charge_filter')
    due_to = filters.DateFilter(method='defer_charge_filter')
    coverage = filters.ChoiceFilter(choices=[(v, v) for v in ['awaiting_payment', 'active', 'expired', 'paid_use', 'cancelled']], method='filter_coverage')

    class Meta:
        model = Order
        fields = ['person', 'product', 'billing_mode']

    def defer_charge_filter(self, queryset, name, value):
        # Apply all charge criteria to the SAME installment below.
        return queryset

    def filter_coverage(self, queryset, name, value):
        if value == 'cancelled':
            return queryset.filter(cancelled_at__isnull=False)
        queryset = queryset.filter(cancelled_at__isnull=True)
        today = timezone.localdate()
        criteria = {
            'awaiting_payment': dict(starts_on__isnull=True),
            'active': dict(starts_on__isnull=False, months__gt=0, ends_on__gt=today),
            'expired': dict(starts_on__isnull=False, ends_on__lte=today),
            'paid_use': dict(starts_on__isnull=False, months=0),
        }
        return queryset.filter(**criteria[value])

    def filter_queryset(self, queryset):
        queryset = super().filter_queryset(queryset)
        values = self.form.cleaned_data
        start, end, status = values.get('due_from'), values.get('due_to'), values.get('status')
        if start and end and start > end:
            raise ValidationError({'due_to': 'O fim deve ser igual ou posterior ao início.'})
        charges = Charge.objects.filter(order_id=OuterRef('pk'))
        if start:
            charges = charges.filter(due_date__gte=start)
        if end:
            charges = charges.filter(due_date__lte=end)
        if status:
            if status == 'cancelled':
                charges = charges.filter(cancelled_at__isnull=False)
            else:
                charges = charges.filter(cancelled_at__isnull=True).annotate(
                    has_payment=Exists(Payment.objects.filter(charge_id=OuterRef('pk'), voided_at__isnull=True)),
                ).filter(has_payment=status == 'paid')
            if status == 'overdue':
                charges = charges.filter(due_date__lt=timezone.localdate())
            elif status == 'open':
                charges = charges.filter(due_date__gte=timezone.localdate())
        return queryset.filter(Exists(charges)) if start or end or status else queryset
