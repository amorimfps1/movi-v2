from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from billing.models import BenefitAuthorization
from drf_spectacular.utils import extend_schema, extend_schema_serializer

from core.models import Person
from core.permissions import IsAdministrative, IsInternal
from core.views import ListConfiguration
from .finance import create_order, receive, cancel_order, void_payment, refund_payment
from .models import Order, Charge, Payment, Refund
from .filters import OrderFilter
from django.db.models import Count, Q, Sum, Exists, OuterRef, Subquery, DecimalField
from django.db.models.functions import Coalesce
from django.utils import timezone
from decimal import Decimal


class RefundSerializer(serializers.ModelSerializer):
    class Meta:
        model = Refund
        fields = ['id', 'payment', 'amount', 'refunded_on', 'method', 'reference', 'reason', 'actor', 'created_at']
        read_only_fields = fields


@extend_schema_serializer(component_name='EcoWorkPayment')
class PaymentSerializer(serializers.ModelSerializer):
    refunds = RefundSerializer(many=True, read_only=True)
    class Meta:
        model = Payment
        fields = ['id', 'charge', 'amount', 'paid_on', 'method', 'reference', 'actor', 'created_at', 'voided_at', 'voided_by', 'void_reason', 'refunds']
        read_only_fields = fields


@extend_schema_serializer(component_name='EcoWorkCharge')
class ChargeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    payment = PaymentSerializer(read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Charge
        fields = ['id', 'order', 'number', 'amount', 'due_date', 'status', 'payment', 'payments', 'cancelled_at']
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.name', read_only=True)
    charges = ChargeSerializer(many=True, read_only=True)
    coverage_status = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'person', 'person_name', 'product', 'product_name', 'months', 'quantity', 'base_price', 'discount_percent', 'total', 'residence', 'association', 'billing_mode', 'installments', 'first_due', 'starts_on', 'ends_on', 'coverage_status', 'actor', 'created_at', 'charges', 'cancelled_at', 'cancelled_by', 'cancellation_reason', 'cancellation_mode', 'catalog', 'benefit', 'benefit_snapshot']
        read_only_fields = fields


class OrderRequestSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.filter(archived=False))
    product = serializers.CharField(max_length=20)
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)
    billing_mode = serializers.ChoiceField(choices=['cash', 'office', 'card'])
    installments = serializers.IntegerField(min_value=1, max_value=12, default=1)
    first_due = serializers.DateField()
    expected_total = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    request_key = serializers.UUIDField()
    benefit = serializers.PrimaryKeyRelatedField(queryset=BenefitAuthorization.objects.all(), required=False, allow_null=True)


class ReceiveSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    paid_on = serializers.DateField()
    method = serializers.ChoiceField(choices=Payment._meta.get_field('method').choices)
    reference = serializers.CharField(max_length=160, allow_blank=True, default='')
    request_key = serializers.UUIDField()


class PersonSummaryRequest(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.all())


class FinancialReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, allow_blank=False)


class CancelOrderSerializer(FinancialReasonSerializer):
    mode = serializers.ChoiceField(choices=['keep_unpaid', 'cancel_unpaid'])


class RefundRequestSerializer(FinancialReasonSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal('0.01'))
    refunded_on = serializers.DateField()
    method = serializers.ChoiceField(choices=Payment._meta.get_field('method').choices)
    reference = serializers.CharField(max_length=160, allow_blank=True, default='')
    request_key = serializers.UUIDField()


class PersonSummarySerializer(serializers.Serializer):
    total = serializers.DecimalField(max_digits=16, decimal_places=2)
    paid = serializers.DecimalField(max_digits=16, decimal_places=2)
    balance = serializers.DecimalField(max_digits=16, decimal_places=2)
    overdue = serializers.DecimalField(max_digits=16, decimal_places=2)
    orders = serializers.IntegerField()
    refunded = serializers.DecimalField(max_digits=16, decimal_places=2)
    net_paid = serializers.DecimalField(max_digits=16, decimal_places=2)


class OrderViewSet(ListConfiguration, viewsets.ReadOnlyModelViewSet):
    queryset = Order.objects.select_related('person').prefetch_related('charges__payments__refunds')
    serializer_class = OrderSerializer
    permission_classes = [IsInternal, IsAdministrative]
    filterset_class = OrderFilter
    search_fields = ['person__name', 'product_name']
    ordering_fields = ['id', 'created_at']

    @extend_schema(parameters=[PersonSummaryRequest], responses=PersonSummarySerializer)
    @action(detail=False, methods=['get'], filter_backends=[])
    def summary(self, request):
        params = PersonSummaryRequest(data=request.query_params)
        params.is_valid(raise_exception=True)
        person = params.validated_data['person']
        summary = Charge.objects.filter(order__person=person).annotate(
            has_payment=Exists(Payment.objects.filter(charge_id=OuterRef('pk'), voided_at__isnull=True)),
            refunded_amount=Coalesce(Subquery(
                Refund.objects.filter(payment__charge_id=OuterRef('pk')).order_by().values('payment__charge_id').annotate(value=Sum('amount')).values('value'),
                output_field=DecimalField(max_digits=16, decimal_places=2),
            ), Decimal('0.00')),
        ).aggregate(
            total=Sum('amount', filter=Q(cancelled_at__isnull=True), default=Decimal('0.00')),
            paid=Sum('amount', filter=Q(has_payment=True), default=Decimal('0.00')),
            balance=Sum('amount', filter=Q(has_payment=False, cancelled_at__isnull=True), default=Decimal('0.00')),
            overdue=Sum('amount', filter=Q(has_payment=False, cancelled_at__isnull=True, due_date__lt=timezone.localdate()), default=Decimal('0.00')),
            orders=Count('order', distinct=True),
            refunded=Sum('refunded_amount', default=Decimal('0.00')),
        )
        summary['orders'] = Order.objects.filter(person=person).count()
        summary['net_paid'] = summary['paid'] - summary['refunded']
        return Response(PersonSummarySerializer(summary).data)

    @extend_schema(request=CancelOrderSerializer, responses=OrderSerializer)
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        order = self.get_object()
        serializer = CancelOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(OrderSerializer(cancel_order(request.user, order.pk, **serializer.validated_data)).data)

    @extend_schema(request=OrderRequestSerializer, responses={201: OrderSerializer})
    def create(self, request):
        serializer = OrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(OrderSerializer(create_order(request.user, serializer.validated_data)).data, status=201)


class ChargeViewSet(ListConfiguration, viewsets.ReadOnlyModelViewSet):
    queryset = Charge.objects.select_related('order').prefetch_related('payments__refunds')
    serializer_class = ChargeSerializer
    permission_classes = [IsInternal, IsAdministrative]
    filterset_fields = ['order', 'order__person']

    @extend_schema(request=ReceiveSerializer, responses=PaymentSerializer)
    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        charge = self.get_object()
        serializer = ReceiveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(PaymentSerializer(receive(request.user, charge.pk, serializer.validated_data)).data)


class PaymentViewSet(ListConfiguration, viewsets.ReadOnlyModelViewSet):
    queryset = Payment.objects.prefetch_related('refunds')
    serializer_class = PaymentSerializer
    permission_classes = [IsInternal, IsAdministrative]
    filterset_fields = ['charge', 'charge__order']

    @extend_schema(request=FinancialReasonSerializer, responses=PaymentSerializer)
    @action(detail=True, methods=['post'])
    def void(self, request, pk=None):
        payment = self.get_object()
        serializer = FinancialReasonSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(PaymentSerializer(void_payment(request.user, payment.pk, **serializer.validated_data)).data)

    @extend_schema(request=RefundRequestSerializer, responses=RefundSerializer)
    @action(detail=True, methods=['post'])
    def refund(self, request, pk=None):
        payment = self.get_object()
        serializer = RefundRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(RefundSerializer(refund_payment(request.user, payment.pk, serializer.validated_data)).data)
