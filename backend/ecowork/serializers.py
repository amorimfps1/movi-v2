from rest_framework import serializers

from core.models import Condominium, CondominiumAssociation, Person, ResidenceVerification
from .catalog import PRODUCTS


class CondominiumSerializer(serializers.ModelSerializer):
    class Meta:
        model = Condominium
        fields = ["id", "name", "active", "created_at"]
        read_only_fields = ["id", "created_at"]


class AssociationSerializer(serializers.ModelSerializer):
    condominium_name = serializers.CharField(source='condominium.name', read_only=True)
    class Meta:
        model = CondominiumAssociation
        fields = ["id", "condominium", "condominium_name", "starts_on", "ends_on", "actor", "created_at"]
        read_only_fields = ["id", "actor", "created_at"]

    def validate(self, attrs):
        if attrs.get("ends_on") and attrs["ends_on"] <= attrs["starts_on"]:
            raise serializers.ValidationError({"ends_on": "O fim deve ser posterior ao início; a data final não está incluída."})
        return attrs


class EndAssociationSerializer(serializers.Serializer):
    ends_on = serializers.DateField()
    reason = serializers.CharField(max_length=2000)


class ResidenceSerializer(serializers.ModelSerializer):
    person_name = serializers.CharField(source='person.name', read_only=True)
    condominium_name = serializers.CharField(source='condominium.name', read_only=True)
    class Meta:
        model = ResidenceVerification
        fields = ["id", "person", "person_name", "condominium", "condominium_name", "declared", "proof_checked", "verified_at", "actor", "revoked_at", "revoked_by", "revocation_reason"]
        read_only_fields = ["id", "verified_at", "actor", "revoked_at", "revoked_by", "revocation_reason"]

    def validate(self, attrs):
        if not attrs.get("declared") or not attrs.get("proof_checked"):
            raise serializers.ValidationError("Registre a declaração e a conferência do comprovante de residência.")
        return attrs


class QuoteRequestSerializer(serializers.Serializer):
    person = serializers.PrimaryKeyRelatedField(queryset=Person.objects.filter(archived=False))
    product = serializers.ChoiceField(choices=list(PRODUCTS))


class ProductSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    hours = serializers.IntegerField(allow_null=True)
    months = serializers.IntegerField()
    max_installments = serializers.IntegerField()


class QuoteSerializer(serializers.Serializer):
    person = serializers.IntegerField()
    product = serializers.CharField()
    base_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    residence_verification = serializers.IntegerField(allow_null=True)
    association = serializers.IntegerField(allow_null=True)
    reason = serializers.CharField()
    quoted_on = serializers.DateField()
