from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from rest_framework.exceptions import ValidationError


def discount_limit(catalog):
    try:
        limit = Decimal(str(catalog.configuration.get('discount_limit_percent', '20.00'))) if catalog else Decimal('20.00')
        if not limit.is_finite() or limit < 0 or limit > 100 or limit.as_tuple().exponent < -2:
            raise ValueError
        return limit
    except (InvalidOperation, ValueError):
        raise ValidationError('O limite de desconto da tabela financeira é inválido; solicite revisão.') from None


def apply_benefit(terms, benefit, person, group, start, plan):
    if (benefit.scope != 'academic' or benefit.status != 'approved' or benefit.approval_limit_percent is None or benefit.person_id != person.pk or not benefit.starts_on <= start <= benefit.ends_on
            or (benefit.modality_id and benefit.modality_id != group.modality_id) or (benefit.plan and benefit.plan != plan)):
        raise ValidationError({'benefit': 'O benefício não está aprovado ou não se aplica a esta contratação.'})
    gross = terms['amount']
    discount = (gross * benefit.value / Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) if benefit.kind == 'percent' else benefit.value
    if discount > gross:
        raise ValidationError({'benefit': 'O desconto supera o valor do contrato.'})
    catalog = terms.get('financial_catalog')
    current_limit = discount_limit(catalog)
    effective_limit = min(benefit.approval_limit_percent, current_limit)
    if (discount == gross or discount * 100 > gross * effective_limit) and not benefit.institutional_reference:
        raise ValidationError({'benefit': 'O desconto excede o limite aprovado e requer autorização institucional.'})
    total = gross - discount
    schedule = [dict(item) for item in terms['schedule']]
    installments = [item for item in schedule if item['category'] == 'tuition']
    if total == 0:
        schedule = [item for item in schedule if item['category'] != 'tuition']
    else:
        cents, remainder = divmod(int(total * 100), len(installments))
        if cents < 1:
            raise ValidationError({'benefit': 'O valor restante é insuficiente para o parcelamento escolhido.'})
        for index, item in enumerate(installments):
            item['amount'] = str(Decimal(cents + (index < remainder)) / 100)
    if benefit.fee_waiver:
        schedule = [item for item in schedule if item['category'] != 'enrollment_fee']
    terms.update(amount=total, fee_amount=Decimal('0.00') if benefit.fee_waiver else terms['fee_amount'], schedule=schedule,
                 benefit_snapshot={'benefit': benefit.pk, 'gross': str(gross), 'discount': str(discount),
                                   'kind': benefit.kind, 'value': str(benefit.value), 'fee_waiver': benefit.fee_waiver,
                                   'approval_limit_percent': str(effective_limit),
                                   'approved_by': benefit.decided_by_id, 'institutional_reference': benefit.institutional_reference,
                                   'fully_waived': total == 0})
    return terms
