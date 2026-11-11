"""Administrative drafts for future versioned commercial catalogs."""
import hashlib
import json
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response

from core.audit import record
from core.models import OperationLock, User
from core.permissions import IsInternal, is_internal
from .models import Enrollment, FinancialCatalogVersion
from .catalog_validation import validate_academic_catalog


class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialCatalogVersion
        fields = ['id', 'version', 'status', 'effective_from', 'effective_until', 'configuration',
                  'created_by', 'created_at', 'published_by', 'published_at']
        read_only_fields = ['id', 'version', 'status', 'created_by', 'created_at', 'published_by', 'published_at']

    def validate(self, attrs):
        start = attrs.get('effective_from', getattr(self.instance, 'effective_from', None))
        end = attrs.get('effective_until', getattr(self.instance, 'effective_until', None))
        if start and end and end < start:
            raise serializers.ValidationError({'effective_until': 'O fim deve ser igual ou posterior ao início.'})
        if not isinstance(attrs.get('configuration', getattr(self.instance, 'configuration', {})), dict):
            raise serializers.ValidationError({'configuration': 'A configuração deve ser um objeto.'})
        return attrs


def coordinator(user):
    actor = User.objects.select_for_update().get(pk=user.pk)
    if not is_internal(actor) or 'coordinator' not in actor.roles:
        raise PermissionDenied('A configuração financeira exige Coordenação.')
    return actor


def catalog_digest(catalog):
    payload = {'configuration': catalog.configuration, 'effective_from': catalog.effective_from.isoformat(),
               'effective_until': catalog.effective_until.isoformat() if catalog.effective_until else None}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()


class FinancialCatalogViewSet(viewsets.ModelViewSet):
    permission_classes = [IsInternal]
    serializer_class = CatalogSerializer
    queryset = FinancialCatalogVersion.objects.all()
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        if not self.request.user.is_authenticated or 'coordinator' not in self.request.user.roles:
            raise PermissionDenied('A configuração financeira exige Coordenação.')
        return super().get_queryset()

    @transaction.atomic
    def perform_create(self, serializer):
        actor = coordinator(self.request.user)
        OperationLock.objects.get_or_create(key='financial-catalog-versions')
        OperationLock.objects.select_for_update().get(key='financial-catalog-versions')
        version = (FinancialCatalogVersion.objects.aggregate(value=Max('version'))['value'] or 0) + 1
        catalog = serializer.save(version=version, created_by=actor)
        record(actor, 'financial_catalog.create', catalog, metadata={'version': version, 'after': dict(CatalogSerializer(catalog).data)})

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        actor = coordinator(request.user)
        catalog = FinancialCatalogVersion.objects.select_for_update().get(pk=self.get_object().pk)
        if catalog.status != FinancialCatalogVersion.Status.DRAFT:
            raise ValidationError('Versões publicadas não podem ser alteradas.')
        serializer = self.get_serializer(catalog, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        before = CatalogSerializer(catalog).data
        serializer.save()
        record(actor, 'financial_catalog.update', catalog, metadata={'before': dict(before), 'after': dict(serializer.data)})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        catalog = self.get_object()
        errors = validate_academic_catalog(catalog.configuration)
        overlaps = FinancialCatalogVersion.objects.filter(status=FinancialCatalogVersion.Status.PUBLISHED).exclude(pk=catalog.pk)
        if catalog.effective_until:
            overlaps = overlaps.filter(effective_from__lte=catalog.effective_until)
        overlaps = overlaps.filter(Q(effective_until__isnull=True) | Q(effective_until__gte=catalog.effective_from))
        conflicting_versions = list(overlaps.values_list('version', flat=True))
        if conflicting_versions:
            errors.append('A vigência se sobrepõe a versões publicadas.')
        existing = Enrollment.objects.filter(start_date__gte=catalog.effective_from)
        if catalog.effective_until:
            existing = existing.filter(start_date__lte=catalog.effective_until)
        return Response({'valid': not errors, 'errors': errors, 'effective_from': catalog.effective_from,
                         'effective_until': catalog.effective_until,
                         'revision': catalog_digest(catalog),
                         'conflicting_versions': conflicting_versions,
                         'existing_contracts_preserved': existing.count(),
                         'scope': 'Contratos existentes serão preservados; novas contratações usarão a versão vigente após a publicação.'})

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def publish(self, request, pk=None):
        actor = coordinator(request.user)
        OperationLock.objects.get_or_create(key='financial-catalog-versions')
        OperationLock.objects.select_for_update().get(key='financial-catalog-versions')
        catalog = FinancialCatalogVersion.objects.select_for_update().get(pk=self.get_object().pk)
        if catalog.status != FinancialCatalogVersion.Status.DRAFT:
            raise ValidationError('Esta versão já foi publicada.')
        if request.data.get('revision') != catalog_digest(catalog):
            raise ValidationError({'revision': 'A tabela mudou ou não foi conferida. Faça uma nova prévia antes de publicar.'})
        reason = request.data.get('reason')
        if not isinstance(reason, str) or not reason.strip():
            raise ValidationError({'reason': 'Informe o motivo da publicação.'})
        errors = validate_academic_catalog(catalog.configuration)
        conflicts = FinancialCatalogVersion.objects.filter(status='published').exclude(pk=catalog.pk)
        if catalog.effective_until:
            conflicts = conflicts.filter(effective_from__lte=catalog.effective_until)
        if conflicts.filter(Q(effective_until__isnull=True) | Q(effective_until__gte=catalog.effective_from)).exists():
            errors.append('A vigência se sobrepõe a versões publicadas.')
        if errors:
            raise ValidationError({'configuration': errors})
        catalog.status = 'published'
        catalog.published_by = actor
        catalog.published_at = timezone.now()
        catalog.save(update_fields=['status', 'published_by', 'published_at'])
        record(actor, 'financial_catalog.publish', catalog, reason=reason.strip(), metadata={'version': catalog.version, 'effective_from': catalog.effective_from.isoformat(), 'effective_until': catalog.effective_until.isoformat() if catalog.effective_until else None})
        return Response(self.get_serializer(catalog).data)
