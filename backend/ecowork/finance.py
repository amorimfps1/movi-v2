import hashlib
import json
from calendar import monthrange
from decimal import Decimal

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from core.audit import record
from core.models import Condominium, Person, OperationLock
from core.services import lock_admin
from .catalog import PRODUCTS
from .models import Charge, Order, Payment
from .services import quote


def add_months(day, months):
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return day.replace(year=year, month=month + 1, day=min(day.day, monthrange(year, month + 1)[1]))


@transaction.atomic
def create_order(actor, data):
    lock_admin(actor)
    person_id = data['person'].pk
    # Same lock order as residence verification: condominium before person.
    residence = data['person'].residence_verifications.filter(revoked_at__isnull=True).first()
    if residence:
        Condominium.objects.select_for_update().get(pk=residence.condominium_id)
    person = Person.objects.select_for_update().get(pk=person_id)
    fingerprint = hashlib.sha256(json.dumps({k: (v.pk if k == 'person' else str(v)) for k, v in data.items()}, sort_keys=True).encode()).hexdigest()
    previous = Order.objects.filter(person=person, request_key=data['request_key']).first()
    if previous:
        if previous.request_hash != fingerprint:
            raise ValidationError('Esta tentativa já foi utilizada com outros dados.')
        return previous
    if person.archived:
        raise ValidationError('Cadastro arquivado.')
    current_residence = person.residence_verifications.filter(revoked_at__isnull=True).first()
    if (residence.pk if residence else None) != (current_residence.pk if current_residence else None):
        raise ValidationError('A residência mudou durante a operação. Consulte novamente.')
    product = PRODUCTS[data['product']]
    installments, mode, quantity = data['installments'], data['billing_mode'], data['quantity']
    if installments > product['max_installments']:
        raise ValidationError({'installments': 'Quantidade de parcelas acima do limite do produto.'})
    if mode == 'cash' and installments != 1:
        raise ValidationError('Pagamento à vista exige uma única cobrança.')
    if not product['months'] and (installments != 1 or mode != 'cash'):
        raise ValidationError('Avulsos exigem pagamento integral antes do uso.')
    if product['months'] and quantity != 1:
        raise ValidationError('Contrate um plano por operação.')
    pricing = quote(person, data['product'])
    if data['expected_total'] != pricing['total'] * quantity:
        raise ValidationError('Preço ou elegibilidade mudou. Confira a simulação e confirme novamente.')
    order = Order.objects.create(
        person=person, product=data['product'], product_name=product['name'], months=product['months'],
        quantity=quantity, base_price=pricing['base_price'], discount_percent=pricing['discount_percent'],
        total=pricing['total'] * quantity, residence_id=pricing['residence_verification'],
        association_id=pricing['association'] if pricing['discount_percent'] else None,
        billing_mode=mode, installments=installments, first_due=data['first_due'],
        actor=actor, request_key=data['request_key'], request_hash=fingerprint,
    )
    # Card installments belong to the card agreement, not monthly customer debts.
    count = installments if mode == 'office' else 1
    cents, remainder = divmod(int(order.total * 100), count)
    for index in range(count):
        Charge.objects.create(order=order, number=index + 1,
            amount=Decimal(cents + (index < remainder)) / 100,
            due_date=add_months(order.first_due, index))
    record(actor, 'ecowork.order.create', order, metadata={'total': str(order.total), 'discount_percent': order.discount_percent})
    return order


@transaction.atomic
def receive(actor, charge_id, data):
    lock_admin(actor)
    key = f'ecowork-payment:{data["request_key"]}'
    OperationLock.objects.get_or_create(key=key)
    OperationLock.objects.select_for_update().get(key=key)
    charge = Charge.objects.get(pk=charge_id)
    order = Order.objects.select_for_update().get(pk=charge.order_id)
    charge = Charge.objects.select_for_update().get(pk=charge.pk)
    previous = Payment.objects.filter(request_key=data['request_key']).first()
    if previous:
        if previous.charge_id != charge.pk or any(getattr(previous, key) != data[key] for key in ['amount', 'paid_on', 'method', 'reference']):
            raise ValidationError('Esta tentativa de pagamento já foi utilizada com outros dados.')
        return previous
    if Payment.objects.filter(charge=charge).exists():
        raise ValidationError('Esta cobrança já foi quitada.')
    if data['amount'] != charge.amount:
        raise ValidationError({'amount': 'Informe exatamente o valor integral da cobrança.'})
    if data['paid_on'] > timezone.localdate():
        raise ValidationError({'paid_on': 'Não é possível confirmar pagamento futuro.'})
    if data['paid_on'] < timezone.localtime(order.created_at).date():
        raise ValidationError({'paid_on': 'Pagamento anterior à contratação requer importação histórica específica.'})
    if charge.number != 1 and not order.starts_on:
        raise ValidationError('Confirme a primeira parcela antes das seguintes.')
    if order.starts_on and data['paid_on'] < order.starts_on:
        raise ValidationError('Pagamento não pode anteceder a primeira parcela.')
    if order.billing_mode == 'card' and (data['method'] != 'card' or not data['reference'].strip()):
        raise ValidationError('Confirme a compra no cartão e informe a referência da transação aprovada.')
    payment = Payment.objects.create(charge=charge, actor=actor, **data)
    if charge.number == 1:
        order.starts_on = payment.paid_on
        order.ends_on = add_months(payment.paid_on, order.months) if order.months else None
        order.save(update_fields=['starts_on', 'ends_on'])
    record(actor, 'ecowork.payment.create', payment, metadata={'order': order.pk, 'amount': str(payment.amount)})
    return payment
