"""Contract snapshots authorized by promptimpmodalidades.md (2026).

Dates and monetary rounding are deterministic; no mapping from modality names
to price categories is inferred. Historical enrollments are never converted.
"""
from calendar import monthrange
from datetime import timedelta
from decimal import Decimal

from rest_framework.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from core.audit import record
from .models import Charge, FinancialCatalogVersion


PRICES = {
    1: ('1123.75', '998.89', '998.89', '899.00'),
    2: ('1373.75', '1221.11', '1221.11', '1099.00'),
    3: ('1448.75', '1287.78', '1287.78', '1159.00'),
    4: ('1686.25', '1498.89', '1498.89', '1349.00'),
    5: ('2080.50', '1849.38', '1849.38', '1664.44'),
    6: ('2311.67', '2054.87', '2054.87', '1849.38'),
}


def add_months(day, months):
    year, month = divmod(day.year * 12 + day.month - 1 + months, 12)
    return day.replace(year=year, month=month + 1, day=min(day.day, monthrange(year, month + 1)[1]))


def terms(group, start, plan, associated, method, installments):
    modality = group.modality
    catalogs = list(FinancialCatalogVersion.objects.filter(status='published', effective_from__lte=start)
                    .filter(Q(effective_until__isnull=True) | Q(effective_until__gte=start))[:2])
    if len(catalogs) > 1:
        raise ValidationError('Há tabelas financeiras publicadas sobrepostas; solicite revisão.')
    catalog = catalogs[0] if catalogs else None
    if catalog:
        config = catalog.configuration
        selected_plan = config['plans'].get(plan)
        if not selected_plan or installments not in selected_plan['installments']:
            raise ValidationError({'installments': 'Plano ou parcelamento indisponível na tabela vigente.'})
        price = next((p for p in config['prices'] if p['category'] == modality.price_category and p['plan'] == plan and p['method'] == method and p['associated'] == associated), None)
        fees = config['fees'].get(modality.enrollment_fee_kind)
        if not price or not fees:
            raise ValidationError('Preço ou taxa não configurados na tabela vigente.')
        total = Decimal(price['amount'])
        fee = Decimal(fees['associated' if associated else 'non_associated'])
        months = selected_plan['months']
        due_rule = config.get('due_rule', '15_end')
        due_reference = config.get('due_reference', 'start')
    else:
        if FinancialCatalogVersion.objects.filter(status='published').exists():
            raise ValidationError('Não há tabela financeira publicada para a data de início informada.')
        if start.year != 2026 or method != 'card' or modality.price_category not in PRICES:
            raise ValidationError('Preço não configurado para este ano, modalidade ou meio de pagamento. Karatê e boleto aguardam tabela validada.')
        allowed = {'quarterly': (1, 2, 3), 'yearly': (3, 6, 10, 12)}
        if plan not in allowed or installments not in allowed[plan]:
            raise ValidationError({'installments': 'Selecione 1/2/3 no trimestral ou 3/6/10/12 no anual.'})
        if modality.enrollment_fee_kind not in ('standard', 'rhythmic'):
            raise ValidationError('Configure o tipo de taxa de matrícula da modalidade.')
        total = Decimal(PRICES[modality.price_category][(2 if associated else 0) + (1 if plan == 'yearly' else 0)])
        fee = Decimal(('35.00' if associated else '70.00') if modality.enrollment_fee_kind == 'rhythmic' else ('25.00' if associated else '35.00'))
        months = 3 if plan == 'quarterly' else 12
        due_rule, due_reference = '15_end', 'start'
    if due_rule == 'start':
        first_due = start
    elif due_rule == 'fixed':
        reference_day = config['due_day']
        first_due = start.replace(day=min(reference_day, monthrange(start.year, start.month)[1]))
        if first_due < start:
            next_month = add_months(start.replace(day=1), 1)
            first_due = next_month.replace(day=min(reference_day, monthrange(next_month.year, next_month.month)[1]))
    else:
        first_due = start.replace(day=15 if start.day <= 15 else monthrange(start.year, start.month)[1])
    cents, remainder = divmod(int(total * 100), installments)
    schedule = []
    for index in range(installments):
        if index == 0:
            due = first_due
        elif due_rule == 'fixed' and due_reference == 'first_due':
            target = add_months(first_due.replace(day=1), index)
            due = target.replace(day=min(reference_day, monthrange(target.year, target.month)[1]))
        else:
            due = add_months(first_due if due_reference == 'first_due' else start, index)
        schedule.append({'key': f'installment:{index+1}', 'category': 'tuition',
                         'amount': str(Decimal(cents + (1 if index < remainder else 0)) / 100),
                         'due_date': due.isoformat(), 'competence': due.replace(day=1).isoformat(),
                         'description': f'Parcela {index+1}/{installments} — total contratado {total}'})
    if fee:
        schedule.append({'key': 'fee', 'category': 'enrollment_fee', 'amount': str(fee),
                         'due_date': first_due.isoformat(), 'competence': None, 'description': 'Taxa de matrícula'})
    return dict(contract_version=1, amount=total, fee_amount=fee,
                end_date=add_months(start, months) - timedelta(days=1), schedule=schedule, financial_catalog=catalog)


def generate(enrollment, actor):
    """Caller holds ClassGroup and Enrollment locks inside a transaction."""
    if enrollment.contract_version != 1 or not enrollment.schedule:
        raise ValidationError('Matrícula legada sem cronograma contratual. Não é possível inferir obrigações.')
    if enrollment.administrative_status != 'regular' and (not enrollment.cancelled_on or enrollment.cancelled_on <= timezone.localdate()):
        raise ValidationError('Matrícula cancelada; geração indisponível.')
    for item in enrollment.schedule:
        values = {key: value for key, value in item.items() if key != 'key'}
        charge, created = Charge.objects.get_or_create(
            idempotency_key=f'contract:{enrollment.pk}:{item["key"]}',
            defaults={'enrollment': enrollment, **values})
        if created:
            record(actor, 'charge.generated', charge, metadata=values)
        elif (charge.enrollment_id != enrollment.pk or charge.amount != Decimal(item['amount'])
              or charge.due_date.isoformat() != item['due_date'] or charge.category != item['category']):
            raise ValidationError(f'Obrigação divergente: {item["key"]}. Revisão administrativa necessária; nenhum vencimento foi alterado.')


def contract_eligibility(enrollment, on):
    result = {'eligible': False, 'status': 'blocked', 'reason': '', 'decisions': []}
    if on > enrollment.end_date:
        return {**result, 'status': 'expired', 'reason': 'Contrato encerrado. É necessária renovação.'}
    charges = {c.idempotency_key: c for c in enrollment.charges.prefetch_related('payments')}
    required = []
    for item in enrollment.schedule:
        charge = charges.get(f'contract:{enrollment.pk}:{item["key"]}')
        if not charge or charge.amount != Decimal(item['amount']) or charge.due_date.isoformat() != item['due_date']:
            return {**result, 'reason': f'Cobrança obrigatória ausente ou divergente: {item["key"]}. Solicite regularização.'}
        required.append(charge)
    def paid(charge):
        return sum((p.amount for p in charge.payments.all() if p.paid_on <= on), Decimal('0')) >= charge.amount
    if any(c.due_date < on and not paid(c) for c in charges.values()):
        return {**result, 'reason': 'Cobrança vencida sem quitação integral.'}
    activation = [c for c in required if c.category == 'enrollment_fee' or c.idempotency_key.endswith(':installment:1')]
    if not activation or not all(paid(c) for c in activation):
        return {**result, 'status': 'pending', 'reason': 'Aguardando pagamento da primeira parcela e da taxa de matrícula, quando aplicável.'}
    return {**result, 'eligible': True, 'status': 'regular', 'reason': 'Contrato vigente e pagamentos regulares.'}
