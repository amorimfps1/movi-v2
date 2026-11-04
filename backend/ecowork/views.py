from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from core.models import Condominium, CondominiumAssociation, ResidenceVerification
from core.permissions import IsAdministrative, IsInternal
from core.serializers import ReasonSerializer
from core.views import AdministrativeModelViewSet, ListConfiguration
from .catalog import PRODUCTS
from .serializers import (
    AssociationSerializer, CondominiumSerializer, EndAssociationSerializer,
    ProductSerializer, QuoteRequestSerializer, QuoteSerializer, ResidenceSerializer,
)
from .services import create_association, end_association, quote, revoke_residence, verify_residence


class CondominiumViewSet(AdministrativeModelViewSet):
    queryset = Condominium.objects.all()
    serializer_class = CondominiumSerializer
    filterset_fields = ["active"]
    search_fields = ["name"]
    ordering_fields = ["name", "id"]


class RecordedViewSet(ListConfiguration, mixins.CreateModelMixin, viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsInternal, IsAdministrative]


class AssociationViewSet(RecordedViewSet):
    queryset = CondominiumAssociation.objects.select_related('condominium')
    serializer_class = AssociationSerializer
    filterset_fields = ["condominium"]

    def perform_create(self, serializer):
        serializer.instance = create_association(self.request.user, serializer.validated_data)

    @extend_schema(request=EndAssociationSerializer, responses=AssociationSerializer)
    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        association = self.get_object()
        data = EndAssociationSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        result = end_association(request.user, association, **data.validated_data)
        return Response(self.get_serializer(result).data)


class ResidenceViewSet(RecordedViewSet):
    queryset = ResidenceVerification.objects.select_related('person', 'condominium')
    serializer_class = ResidenceSerializer
    filterset_fields = ["person", "condominium"]

    def perform_create(self, serializer):
        serializer.instance = verify_residence(self.request.user, serializer.validated_data)

    @extend_schema(request=ReasonSerializer, responses=ResidenceSerializer)
    @action(detail=True, methods=["post"])
    def revoke(self, request, pk=None):
        verification = self.get_object()
        data = ReasonSerializer(data=request.data)
        data.is_valid(raise_exception=True)
        result = revoke_residence(request.user, verification, **data.validated_data)
        return Response(self.get_serializer(result).data)


class ProductView(APIView):
    permission_classes = [IsInternal, IsAdministrative]

    @extend_schema(responses=ProductSerializer(many=True))
    def get(self, request):
        return Response(ProductSerializer([dict(code=code, **item) for code, item in PRODUCTS.items()], many=True).data)


class QuoteView(APIView):
    permission_classes = [IsInternal, IsAdministrative]

    @extend_schema(request=QuoteRequestSerializer, responses=QuoteSerializer)
    def post(self, request):
        serializer = QuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(QuoteSerializer(quote(**serializer.validated_data)).data)
