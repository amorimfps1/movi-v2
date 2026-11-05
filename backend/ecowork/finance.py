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
from .models import Charge, Order, Payment, Refund
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
    if charge.cancelled_at:
        raise ValidationError('Esta cobrança foi cancelada.')
    if Payment.objects.filter(charge=charge, voided_at__isnull=True).exists():
        raise ValidationError('Esta cobrança já foi quitada.')
    if data['amount'] != charge.amount:
        raise ValidationError({'amount': 'Informe exatamente o valor integral da cobrança.'})
    if data['paid_on'] > timezone.localdate():
        raise ValidationError({'paid_on': 'Não é possível confirmar pagamento futuro.'})
    if data['paid_on'] < timezone.localtime(order.created_at).date():
        raise ValidationError({'paid_on': 'Pagamento anterior à contratação requer importação histórica específica.'})
    first_payment = Payment.objects.filter(charge__order=order, charge__number=1, voided_at__isnull=True).first()
    if charge.number != 1 and not first_payment:
        raise ValidationError('Confirme a primeira parcela antes das seguintes.')
    if first_payment and data['paid_on'] < first_payment.paid_on:
        raise ValidationError('Pagamento não pode anteceder a primeira parcela.')
    if order.billing_mode == 'card' and (data['method'] != 'card' or not data['reference'].strip()):
        raise ValidationError('Confirme a compra no cartão e informe a referência da transação aprovada.')
    payment = Payment.objects.create(charge=charge, actor=actor, **data)
    if charge.number == 1 and not order.cancelled_at:
        order.starts_on = payment.paid_on
        order.ends_on = add_months(payment.paid_on, order.months) if order.months else None
        order.save(update_fields=['starts_on', 'ends_on'])
    record(actor, 'ecowork.payment.create', payment, metadata={'order': order.pk, 'amount': str(payment.amount)})
    return payment


def _reason(reason):
    if not reason or not reason.strip():
        raise ValidationError({'reason': 'Informe o motivo.'})
    return reason.strip()


@transaction.atomic
def cancel_order(actor, order_id, mode, reason):
    lock_admin(actor)
    reason = _reason(reason)
    if mode not in ['keep_unpaid', 'cancel_unpaid']:
        raise ValidationError('Escolha o tratamento das parcelas não pagas.')
    order = Order.objects.select_for_update().get(pk=order_id)
    if order.cancelled_at:
        if order.cancellation_mode != mode or order.cancellation_reason != reason:
            raise ValidationError('Contratação já cancelada com outra decisão. Consulte o histórico.')
        return order
    order.cancelled_at = timezone.now()
    order.cancelled_by = actor
    order.cancellation_reason = reason
    order.cancellation_mode = mode
    order.save(update_fields=['cancelled_at', 'cancelled_by', 'cancellation_reason', 'cancellation_mode'])
    cancelled = []
    for charge in order.charges.select_for_update():
        if mode == 'cancel_unpaid' and not charge.payment:
            charge.cancelled_at = order.cancelled_at
            charge.save(update_fields=['cancelled_at'])
            cancelled.append(charge.pk)
    record(actor, 'ecowork.order.cancel', order, reason=reason, metadata={'mode': mode, 'cancelled_charges': cancelled})
    return order


@transaction.atomic
def void_payment(actor, payment_id, reason):
    lock_admin(actor)
    reason = _reason(reason)
    original = Payment.objects.select_related('charge').get(pk=payment_id)
    order = Order.objects.select_for_update().get(pk=original.charge.order_id)
    charge = Charge.objects.select_for_update().get(pk=original.charge_id)
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    if payment.voided_at:
        if payment.void_reason != reason:
            raise ValidationError('Lançamento já invalidado com outro motivo.')
        return payment
    if payment.refunds.exists():
        raise ValidationError('Há devoluções vinculadas. Este recebimento não pode ser invalidado.')
    if charge.number == 1 and Payment.objects.filter(charge__order=order, voided_at__isnull=True).exclude(pk=payment.pk).exists():
        raise ValidationError('Corrija primeiro os pagamentos das demais parcelas para rever o início da vigência.')
    payment.voided_at, payment.voided_by, payment.void_reason = timezone.now(), actor, reason
    payment.save(update_fields=['voided_at', 'voided_by', 'void_reason'])
    if charge.number == 1:
        order.starts_on = order.ends_on = None
        order.save(update_fields=['starts_on', 'ends_on'])
    if order.cancelled_at and order.cancellation_mode == 'cancel_unpaid':
        charge.cancelled_at = timezone.now()
        charge.save(update_fields=['cancelled_at'])
    record(actor, 'ecowork.payment.void', payment, reason=reason, metadata={'order': order.pk, 'amount': str(payment.amount)})
    return payment


@transaction.atomic
def refund_payment(actor, payment_id, data):
    lock_admin(actor)
    data = {**data, 'reason': _reason(data['reason'])}
    key = f'ecowork-refund:{data["request_key"]}'
    OperationLock.objects.get_or_create(key=key)
    OperationLock.objects.select_for_update().get(key=key)
    original = Payment.objects.select_related('charge').get(pk=payment_id)
    order = Order.objects.select_for_update().get(pk=original.charge.order_id)
    payment = Payment.objects.select_for_update().get(pk=payment_id)
    previous = Refund.objects.filter(request_key=data['request_key']).first()
    if previous:
        if previous.payment_id != payment.pk or any(getattr(previous, field) != value for field, value in data.items()):
            raise ValidationError('Esta tentativa de devolução já foi utilizada com outros dados.')
        return previous
    if payment.voided_at:
        raise ValidationError('Recebimento invalidado não permite devolução.')
    refunded = sum((item.amount for item in payment.refunds.all()), Decimal('0.00'))
    if data['amount'] <= 0 or data['amount'] > payment.amount - refunded:
        raise ValidationError({'amount': 'Informe um valor positivo limitado ao saldo disponível para devolução.'})
    if not payment.paid_on <= data['refunded_on'] <= timezone.localdate():
        raise ValidationError({'refunded_on': 'Informe uma data entre o pagamento e hoje.'})
    refund = Refund.objects.create(payment=payment, actor=actor, **data)
    record(actor, 'ecowork.payment.refund', refund, reason=data['reason'], metadata={'order': order.pk, 'payment': payment.pk, 'amount': str(refund.amount)})
    return refund
