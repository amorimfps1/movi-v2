from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_serializer

from core.models import Person
from core.permissions import IsAdministrative, IsInternal
from core.views import ListConfiguration
from .catalog import PRODUCTS
from .finance import create_order, receive
from .models import Order, Charge, Payment


@extend_schema_serializer(component_name='EcoWorkPayment')
class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ['id', 'charge', 'amount', 'paid_on', 'method', 'reference', 'actor', 'created_at']
        read_only_fields = fields


@extend_schema_serializer(component_name='EcoWorkCharge')
class ChargeSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    payment = PaymentSerializer(read_only=True)

    class Meta:
        model = Charge
        fields = ['id', 'order', 'number', 'amount', 'due_date', 'status', 'payment']
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.name', read_only=True)
    charges = ChargeSerializer(many=True, read_only=True)
    coverage_status = serializers.CharField(read_only=True)

    class Meta:
        model = Order
        fields = ['id', 'person', 'person_name', 'product', 'product_name', 'months', 'quantity', 'base_price', 'discount_percent', 'total', 'residence', 'association', 'billing_mode', 'installments', 'first_due', 'starts_on', 'ends_on', 'coverage_status', 'actor', 'created_at', 'charges']
        read_only_fields = fields


class OrderRequestSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.filter(archived=False))
    product = serializers.ChoiceField(choices=list(PRODUCTS))
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)
    billing_mode = serializers.ChoiceField(choices=['cash', 'office', 'card'])
    installments = serializers.IntegerField(min_value=1, max_value=12, default=1)
    first_due = serializers.DateField()
    expected_total = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    request_key = serializers.UUIDField()


class ReceiveSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    paid_on = serializers.DateField()
    method = serializers.ChoiceField(choices=Payment._meta.get_field('method').choices)
    reference = serializers.CharField(max_length=160, allow_blank=True, default='')
    request_key = serializers.UUIDField()


class OrderViewSet(ListConfiguration, viewsets.ReadOnlyModelViewSet):
    queryset = Order.objects.select_related('person').prefetch_related('charges__payment')
    serializer_class = OrderSerializer
    permission_classes = [IsInternal, IsAdministrative]
    filterset_fields = ['person', 'product', 'billing_mode']
    search_fields = ['person__name', 'product_name']
    ordering_fields = ['id', 'created_at']

    @extend_schema(request=OrderRequestSerializer, responses={201: OrderSerializer})
    def create(self, request):
        serializer = OrderRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(OrderSerializer(create_order(request.user, serializer.validated_data)).data, status=201)


class ChargeViewSet(ListConfiguration, viewsets.ReadOnlyModelViewSet):
    queryset = Charge.objects.select_related('payment', 'order')
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
