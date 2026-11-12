from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.audit import record
from core.models import OperationLock, Person
from core.permissions import IsAdministrative, IsInternal
from core.services import lock_admin, lock_student_identities
from .models import BenefitAuthorization, FinancialCatalogVersion
from .benefits import discount_limit


class BenefitSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.name', read_only=True)
    modality_name = serializers.CharField(source='modality.name', read_only=True, allow_null=True)

    class Meta:
        model = BenefitAuthorization
        fields = ['id', 'scope', 'person', 'person_name', 'modality', 'modality_name', 'plan', 'starts_on', 'ends_on',
                  'kind', 'value', 'fee_waiver', 'reason', 'status', 'requested_by', 'decided_by', 'decided_at',
                  'decision_reason', 'institutional_reference', 'approval_limit_percent', 'created_at']
        read_only_fields = ['id', 'person_name', 'modality_name', 'status', 'requested_by', 'decided_by', 'decided_at',
                            'decision_reason', 'institutional_reference', 'approval_limit_percent', 'created_at']

    def validate(self, attrs):
        if attrs.get('scope', 'academic') == 'ecowork' and (attrs.get('modality') or attrs.get('fee_waiver')):
            raise serializers.ValidationError('Benefício EcoWork não usa modalidade acadêmica nem isenção de taxa de matrícula.')
        if attrs['ends_on'] < attrs['starts_on'] or attrs['value'] < 0 or (attrs['value'] == 0 and not attrs.get('fee_waiver')) or (attrs['kind'] == 'percent' and attrs['value'] > 100):
            raise serializers.ValidationError('Informe vigência e valor de benefício válidos.')
        return attrs


class BenefitDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)
    institutional_reference = serializers.CharField(max_length=250, required=False, allow_blank=True, default='')


class BenefitViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInternal, IsAdministrative]
    serializer_class = BenefitSerializer
    queryset = BenefitAuthorization.objects.select_related('person', 'modality').all()
    filterset_fields = ['person', 'modality', 'status', 'scope']

    @transaction.atomic
    def perform_create(self, serializer):
        actor = lock_admin(self.request.user)
        lock_student_identities()
        person = Person.objects.select_for_update().get(pk=serializer.validated_data['person'].pk)
        if person.archived:
            raise ValidationError('Pessoa arquivada não pode receber nova solicitação.')
        benefit = serializer.save(person=person, requested_by=actor)
        record(actor, 'benefit.requested', benefit, reason=benefit.reason, metadata={'person': person.pk, 'kind': benefit.kind, 'value': str(benefit.value)})

    def _decide(self, request, pk, decision):
        original = self.get_object()
        data = BenefitDecisionSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        with transaction.atomic():
            actor = lock_admin(request.user)
            if 'coordinator' not in actor.roles:
                raise PermissionDenied('Somente a Coordenação pode decidir benefícios.')
            lock_key = 'ecowork-catalog' if original.scope == 'ecowork' else 'financial-catalog-versions'
            OperationLock.objects.get_or_create(key=lock_key)
            OperationLock.objects.select_for_update().get(key=lock_key)
            benefit = BenefitAuthorization.objects.select_for_update().get(pk=pk)
            if benefit.status != 'pending':
                raise ValidationError('Esta solicitação já foi decidida.')
            if benefit.scope == 'ecowork':
                from ecowork.models import CatalogVersion
                catalog = CatalogVersion.objects.filter(status='published', effective_from__lte=benefit.starts_on).filter(Q(effective_until__isnull=True) | Q(effective_until__gte=benefit.starts_on)).first()
            else:
                catalog = FinancialCatalogVersion.objects.filter(status='published', effective_from__lte=benefit.starts_on).filter(Q(effective_until__isnull=True) | Q(effective_until__gte=benefit.starts_on)).first()
            limit = discount_limit(catalog)
            reference = data.validated_data['institutional_reference'].strip()
            if decision == 'approved' and benefit.kind == 'percent' and (benefit.value > limit or benefit.value == 100) and not reference:
                raise ValidationError({'institutional_reference': 'Informe a autorização institucional para o benefício acima do limite.'})
            benefit.status, benefit.decided_by, benefit.decided_at = decision, actor, timezone.now()
            benefit.decision_reason, benefit.institutional_reference = data.validated_data['reason'], reference
            benefit.approval_limit_percent = limit if decision == 'approved' else None
            benefit.save(update_fields=['status', 'decided_by', 'decided_at', 'decision_reason', 'institutional_reference', 'approval_limit_percent'])
            record(actor, f'benefit.{decision}', benefit, reason=benefit.decision_reason, metadata={'limit': str(limit), 'institutional_reference': reference})
        return Response(self.get_serializer(benefit).data)

    @extend_schema(request=BenefitDecisionSerializer, responses=BenefitSerializer)
    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        return self._decide(request, pk, 'approved')

    @extend_schema(request=BenefitDecisionSerializer, responses=BenefitSerializer)
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        return self._decide(request, pk, 'rejected')
