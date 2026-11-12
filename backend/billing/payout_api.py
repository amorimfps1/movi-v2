from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.audit import record
from core.models import OperationLock, User
from core.permissions import IsCoordinator, IsInternal, is_internal
from core.serializers import ReasonSerializer
from .models import InstructorPayoutAgreement


class PayoutAgreementSerializer(serializers.ModelSerializer):
    instructor_name = serializers.CharField(source='instructor.name', read_only=True)
    modality_name = serializers.CharField(source='modality.name', read_only=True)

    class Meta:
        model = InstructorPayoutAgreement
        fields = ['id', 'instructor', 'instructor_name', 'modality', 'modality_name', 'effective_from',
                  'effective_until', 'percentage', 'allocation_method', 'reason', 'actor', 'created_at', 'voided_at', 'voided_by', 'void_reason']
        read_only_fields = ['id', 'instructor_name', 'modality_name', 'actor', 'created_at', 'voided_at', 'voided_by', 'void_reason']

    def validate_percentage(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError('Informe um percentual entre 0 e 100.')
        return value

    def validate(self, attrs):
        if attrs['effective_until'] < attrs['effective_from']:
            raise serializers.ValidationError({'effective_until': 'A vigência final deve ser igual ou posterior ao início.'})
        return attrs


class PayoutAgreementViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInternal, IsCoordinator]
    serializer_class = PayoutAgreementSerializer
    queryset = InstructorPayoutAgreement.objects.select_related('instructor', 'modality').all()
    filterset_fields = ['instructor', 'modality']

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return self.queryset.none()
        if 'coordinator' not in self.request.user.roles:
            raise PermissionDenied('Somente a Coordenação pode consultar acordos de repasse.')
        return super().get_queryset()

    @transaction.atomic
    def perform_create(self, serializer):
        actor = User.objects.select_for_update().get(pk=self.request.user.pk)
        if not is_internal(actor) or 'coordinator' not in actor.roles:
            raise PermissionDenied('Somente a Coordenação pode registrar acordos de repasse.')
        OperationLock.objects.get_or_create(key='payout-agreements')
        OperationLock.objects.select_for_update().get(key='payout-agreements')
        data = serializer.validated_data
        if InstructorPayoutAgreement.objects.filter(instructor=data['instructor'], modality=data['modality'], voided_at__isnull=True,
            effective_from__lte=data['effective_until'], effective_until__gte=data['effective_from']).exists():
            raise ValidationError('Já existe acordo de repasse nesta vigência para o instrutor e modalidade.')
        agreement = serializer.save(actor=actor)
        record(actor, 'payout.agreement.created', agreement, reason=agreement.reason,
               metadata={'instructor': agreement.instructor_id, 'modality': agreement.modality_id,
                         'effective_from': agreement.effective_from.isoformat(), 'effective_until': agreement.effective_until.isoformat(),
                         'percentage': str(agreement.percentage), 'allocation_method': agreement.allocation_method})

    @extend_schema(request=ReasonSerializer, responses=PayoutAgreementSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def void(self, request, pk=None):
        self.get_object()
        data = ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        actor = User.objects.select_for_update().get(pk=request.user.pk)
        if not is_internal(actor) or 'coordinator' not in actor.roles:
            raise PermissionDenied('Somente a Coordenação pode invalidar acordos de repasse.')
        OperationLock.objects.get_or_create(key='payout-agreements')
        OperationLock.objects.select_for_update().get(key='payout-agreements')
        agreement = InstructorPayoutAgreement.objects.select_for_update().get(pk=pk)
        if agreement.voided_at:
            raise ValidationError('Este acordo já foi invalidado.')
        agreement.voided_at, agreement.voided_by, agreement.void_reason = timezone.now(), actor, data.validated_data['reason']
        agreement.save(update_fields=['voided_at', 'voided_by', 'void_reason'])
        record(actor, 'payout.agreement.voided', agreement, reason=agreement.void_reason)
        return Response(self.get_serializer(agreement).data)
