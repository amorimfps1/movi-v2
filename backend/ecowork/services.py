from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.audit import record
from core.models import Condominium, CondominiumAssociation, Person, ResidenceVerification
from core.services import lock_admin
from .catalog import PRODUCTS


@transaction.atomic
def create_association(actor, data):
    lock_admin(actor)
    condominium = Condominium.objects.select_for_update().get(pk=data["condominium"].pk)
    if not condominium.active:
        raise ValidationError("O condomínio está inativo.")
    overlaps = condominium.associations.filter(Q(ends_on__isnull=True) | Q(ends_on__gt=data["starts_on"]))
    if data.get("ends_on"):
        overlaps = overlaps.filter(starts_on__lt=data["ends_on"])
    if overlaps.exists():
        raise ValidationError("Já existe associação neste período.")
    association = CondominiumAssociation.objects.create(**data, actor=actor)
    record(actor, "condominium.association.create", association)
    return association


@transaction.atomic
def end_association(actor, association, ends_on, reason):
    lock_admin(actor)
    Condominium.objects.select_for_update().get(pk=association.condominium_id)
    association = CondominiumAssociation.objects.select_for_update().get(pk=association.pk)
    if association.ends_on is not None:
        raise ValidationError("Este período já possui término registrado.")
    if ends_on <= association.starts_on:
        raise ValidationError("O término deve ser posterior ao início.")
    association.ends_on = ends_on
    association.save(update_fields=["ends_on"])
    record(actor, "condominium.association.end", association, reason=reason, metadata={"ends_on": ends_on.isoformat()})
    return association


@transaction.atomic
def verify_residence(actor, data):
    lock_admin(actor)
    condominium = Condominium.objects.select_for_update().get(pk=data["condominium"].pk)
    person = Person.objects.select_for_update().get(pk=data["person"].pk)
    if person.archived or not condominium.active:
        raise ValidationError("Pessoa ou condomínio inativo.")
    if not data.get("declared") or not data.get("proof_checked"):
        raise ValidationError("Declaração e comprovante conferido são obrigatórios.")
    if person.residence_verifications.filter(revoked_at__isnull=True).exists():
        raise ValidationError("Encerre a validação anterior com justificativa antes de registrar outra residência.")
    verification = ResidenceVerification.objects.create(**data, actor=actor)
    record(actor, "residence.verify", verification)
    return verification


@transaction.atomic
def revoke_residence(actor, verification, reason):
    lock_admin(actor)
    Person.objects.select_for_update().get(pk=verification.person_id)
    verification = ResidenceVerification.objects.select_for_update().get(pk=verification.pk)
    if verification.revoked_at is not None:
        raise ValidationError("Esta validação já foi encerrada.")
    verification.revoked_at = timezone.now()
    verification.revoked_by = actor
    verification.revocation_reason = reason
    verification.save(update_fields=["revoked_at", "revoked_by", "revocation_reason"])
    record(actor, "residence.revoke", verification, reason=reason)
    return verification


def quote(person, product):
    """Read-only estimate. Contract creation must recheck under transaction locks."""
    today = timezone.localdate()
    item = PRODUCTS[product]
    verification = person.residence_verifications.filter(revoked_at__isnull=True, condominium__active=True).first()
    association = None
    if verification:
        association = CondominiumAssociation.objects.filter(
            condominium_id=verification.condominium_id, starts_on__lte=today,
        ).filter(Q(ends_on__isnull=True) | Q(ends_on__gt=today)).first()
    eligible = bool(association and item["months"] and not person.archived)
    percent = 50 if eligible else 0
    return {
        "person": person.pk, "product": product, "base_price": item["price"],
        "discount_percent": percent,
        "total": (item["price"] * (Decimal(100 - percent) / 100)).quantize(Decimal("0.01")),
        "residence_verification": verification.pk if verification else None,
        "association": association.pk if association else None,
        "reason": "Desconto de morador validado." if eligible else (
            "Desconto restrito aos planos." if not item["months"] else "Sem residência validada em condomínio com associação vigente."
        ),
        "quoted_on": today,
    }
