import hashlib
import json
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_serializer
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from core.audit import record
from core.models import OperationLock
from core.permissions import IsCoordinator, IsInternal
from core.serializers import ReasonSerializer
from core.services import lock_admin
from .catalog import validate_catalog
from .models import CatalogVersion, Order


def digest(catalog):
    value = {'configuration': catalog.configuration, 'effective_from': catalog.effective_from.isoformat(), 'effective_until': catalog.effective_until.isoformat() if catalog.effective_until else None}
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':')).encode()).hexdigest()


@extend_schema_serializer(component_name='EcoWorkCatalog')
class CatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogVersion
        fields = ['id', 'version', 'status', 'effective_from', 'effective_until', 'configuration', 'actor', 'created_at', 'published_by', 'published_at']
        read_only_fields = ['id', 'version', 'status', 'actor', 'created_at', 'published_by', 'published_at']

    def validate(self, attrs):
        start = attrs.get('effective_from', getattr(self.instance, 'effective_from', None))
        end = attrs.get('effective_until', getattr(self.instance, 'effective_until', None))
        if end and start and end < start:
            raise serializers.ValidationError({'effective_until': 'O fim não pode anteceder o início.'})
        if not isinstance(attrs.get('configuration', getattr(self.instance, 'configuration', {})), dict):
            raise serializers.ValidationError({'configuration': 'Informe uma configuração válida.'})
        return attrs


@extend_schema_serializer(component_name='EcoWorkEndCatalog')
class EndCatalogSerializer(serializers.Serializer):
    effective_until = serializers.DateField()
    reason = serializers.CharField(max_length=2000)


def conflicts(catalog):
    qs = CatalogVersion.objects.filter(status='published').exclude(pk=catalog.pk)
    if catalog.effective_until:
        qs = qs.filter(effective_from__lte=catalog.effective_until)
    return qs.filter(Q(effective_until__isnull=True) | Q(effective_until__gte=catalog.effective_from))


class EcoCatalogViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, mixins.CreateModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsInternal, IsCoordinator]
    serializer_class = CatalogSerializer
    queryset = CatalogVersion.objects.all()
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def _lock(self):
        actor = lock_admin(self.request.user)
        if 'coordinator' not in actor.roles:
            raise ValidationError('Somente a Coordenação pode publicar catálogos.')
        OperationLock.objects.get_or_create(key='ecowork-catalog')
        OperationLock.objects.select_for_update().get(key='ecowork-catalog')
        return actor

    @transaction.atomic
    def perform_create(self, serializer):
        actor = self._lock()
        version = (CatalogVersion.objects.aggregate(last=Max('version'))['last'] or 0) + 1
        catalog = serializer.save(version=version, actor=actor)
        record(actor, 'ecowork.catalog.created', catalog, metadata={'version': version, 'after': dict(self.get_serializer(catalog).data)})

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        actor = self._lock()
        catalog = CatalogVersion.objects.select_for_update().get(pk=self.get_object().pk)
        if catalog.status != 'draft':
            raise ValidationError('Catálogo publicado não pode ser alterado.')
        before = dict(self.get_serializer(catalog).data)
        serializer = self.get_serializer(catalog, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        record(actor, 'ecowork.catalog.updated', catalog, metadata={'before': before, 'after': dict(serializer.data)})
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def preview(self, request, pk=None):
        catalog = self.get_object()
        errors = validate_catalog(catalog.configuration)
        versions = list(conflicts(catalog).values_list('version', flat=True))
        if versions:
            errors.append('A vigência se sobrepõe a outro catálogo publicado.')
        return Response({'valid': not errors, 'errors': errors, 'revision': digest(catalog), 'conflicting_versions': versions,
                         'existing_orders_preserved': Order.objects.count()})

    @extend_schema(request=ReasonSerializer, responses=CatalogSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def publish(self, request, pk=None):
        actor = self._lock()
        catalog = CatalogVersion.objects.select_for_update().get(pk=self.get_object().pk)
        reason = ReasonSerializer(data=request.data)
        reason.is_valid(raise_exception=True)
        if catalog.status != 'draft' or request.data.get('revision') != digest(catalog):
            raise ValidationError('O rascunho mudou ou já foi publicado. Faça nova prévia.')
        errors = validate_catalog(catalog.configuration)
        if conflicts(catalog).exists():
            errors.append('A vigência se sobrepõe a outro catálogo publicado.')
        if errors:
            raise ValidationError({'configuration': errors})
        catalog.status, catalog.published_by, catalog.published_at = 'published', actor, timezone.now()
        catalog.save(update_fields=['status', 'published_by', 'published_at'])
        record(actor, 'ecowork.catalog.published', catalog, reason=reason.validated_data['reason'], metadata={'version': catalog.version})
        return Response(self.get_serializer(catalog).data)

    @extend_schema(request=EndCatalogSerializer, responses=CatalogSerializer)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def end(self, request, pk=None):
        actor = self._lock()
        catalog = CatalogVersion.objects.select_for_update().get(pk=self.get_object().pk)
        data = EndCatalogSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        end = data.validated_data['effective_until']
        if catalog.status != 'published' or end < timezone.localdate() or end < catalog.effective_from:
            raise ValidationError('Informe um fim atual ou futuro, após o início do catálogo publicado.')
        if catalog.effective_until and end >= catalog.effective_until:
            raise ValidationError('O novo fim deve antecipar o fim vigente.')
        previous = catalog.effective_until
        catalog.effective_until = end
        catalog.save(update_fields=['effective_until'])
        record(actor, 'ecowork.catalog.ended', catalog, reason=data.validated_data['reason'],
               metadata={'before': previous.isoformat() if previous else None, 'after': end.isoformat()})
        return Response(self.get_serializer(catalog).data)
