"""Validation for the first academic catalog format, prior to publication."""
from decimal import Decimal, InvalidOperation
import re


def validate_academic_catalog(configuration):
    errors = []
    try:
        limit = Decimal(str(configuration.get('discount_limit_percent', '20.00')))
        if not limit.is_finite() or limit < 0 or limit > 100 or limit.as_tuple().exponent < -2:
            errors.append('Limite de desconto deve estar entre 0 e 100, com até duas casas decimais.')
    except (InvalidOperation, ValueError):
        errors.append('Limite de desconto inválido.')
    due_rule = configuration.get('due_rule', '15_end')
    reference = configuration.get('due_reference', 'start')
    if due_rule not in ('15_end', 'start', 'fixed'):
        errors.append('Regra de primeiro vencimento inválida.')
    if reference not in ('start', 'first_due'):
        errors.append('Referência de vencimento inválida.')
    if due_rule == 'fixed' and (type(configuration.get('due_day')) is not int or not 1 <= configuration['due_day'] <= 31):
        errors.append('Informe o dia fixo de vencimento entre 1 e 31.')
    plans = configuration.get('plans')
    prices = configuration.get('prices')
    fees = configuration.get('fees')
    if not isinstance(plans, dict) or not plans:
        errors.append('Informe ao menos um plano.')
        plans = {}
    for code, plan in plans.items():
        if not isinstance(code, str) or not re.fullmatch(r'[a-z0-9_]{1,40}', code) or not isinstance(plan, dict):
            errors.append('Cada plano deve ter código e configuração válidos.')
            continue
        if 'name' in plan and (not isinstance(plan['name'], str) or not plan['name'].strip() or len(plan['name']) > 120):
            errors.append(f'Plano {code}: informe um nome válido.')
        months, installments = plan.get('months'), plan.get('installments')
        if type(months) is not int or not 1 <= months <= 120 or not isinstance(installments, list) or not installments or any(type(n) is not int or not 1 <= n <= 120 for n in installments) or len(set(installments)) != len(installments):
            errors.append(f'Plano {code}: informe duração e parcelamentos positivos sem repetição.')

    def valid_amount(value):
        try:
            if not isinstance(value, str):
                return False
            amount = Decimal(value)
            return amount.is_finite() and amount >= 0 and amount.as_tuple().exponent >= -2 and amount <= Decimal('9999999999.99')
        except (InvalidOperation, ValueError):
            return False

    if not isinstance(prices, list) or not prices:
        errors.append('Informe ao menos um preço.')
        prices = []
    seen = set()
    for price in prices:
        if not isinstance(price, dict):
            errors.append('Cada preço deve ser um objeto.')
            continue
        category, plan, method, associated = (price.get(k) for k in ('category', 'plan', 'method', 'associated'))
        if type(category) is not int or category < 1 or category > 7 or not isinstance(plan, str) or plan not in plans or method not in ('card', 'boleto') or type(associated) is not bool:
            errors.append('Preço com categoria, plano, meio ou associação inválidos.')
            continue
        key = (category, plan, method, associated)
        if key in seen:
            errors.append('Existem preços repetidos para a mesma combinação.')
        seen.add(key)
        if not valid_amount(price.get('amount')) or Decimal(price['amount']) <= 0:
            errors.append('O preço deve ser um valor positivo em reais com até dois centavos decimais.')
        elif isinstance(plans[plan], dict) and isinstance(plans[plan].get('installments'), list):
            numbers = plans[plan]['installments']
            if all(type(n) is int and n > 0 for n in numbers) and numbers and Decimal(price['amount']) * 100 < max(numbers):
                errors.append('O preço é insuficiente para distribuir ao menos um centavo por parcela.')
    if not isinstance(fees, dict) or not fees:
        errors.append('Informe as taxas aplicáveis.')
    else:
        for kind, values in fees.items():
            if kind not in ('standard', 'rhythmic') or not isinstance(values, dict) or not all(valid_amount(values.get(key)) for key in ('associated', 'non_associated')):
                errors.append(f'Taxa {kind}: informe valores para associado e não associado.')
    return errors
