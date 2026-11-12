"""Confirmed initial catalog; no persistence or unapproved financial automation."""
from decimal import Decimal
from decimal import InvalidOperation
import re
from django.db.models import Q
from rest_framework.exceptions import ValidationError

PRODUCTS = {
    "hour": {"name": "Hora avulsa", "price": Decimal("5.00"), "hours": 1, "months": 0, "max_installments": 1},
    "half_day": {"name": "Meia diária", "price": Decimal("15.00"), "hours": 4, "months": 0, "max_installments": 1},
    "day": {"name": "Diária", "price": Decimal("25.00"), "hours": 8, "months": 0, "max_installments": 1},
    "monthly": {"name": "Mensal", "price": Decimal("169.00"), "hours": None, "months": 1, "max_installments": 1},
    "semiannual": {"name": "Semestral", "price": Decimal("699.00"), "hours": None, "months": 6, "max_installments": 6},
    "annual": {"name": "Anual", "price": Decimal("969.00"), "hours": None, "months": 12, "max_installments": 12},
}


def validate_catalog(configuration):
    errors = []
    products = configuration.get('products') if isinstance(configuration, dict) else None
    discount = configuration.get('resident_discount_percent', 50) if isinstance(configuration, dict) else None
    limit = configuration.get('discount_limit_percent', 20) if isinstance(configuration, dict) else None
    if type(limit) is not int or not 0 <= limit <= 100:
        errors.append('O limite de benefício individual deve ser inteiro entre 0 e 100%.')
    if type(discount) is not int or not 0 <= discount <= 100:
        errors.append('O desconto de morador deve ser inteiro entre 0 e 100%.')
    if not isinstance(products, list) or not products:
        return errors + ['Informe ao menos um produto.']
    seen = set()
    for item in products:
        if not isinstance(item, dict):
            errors.append('Produto inválido.'); continue
        code, name = item.get('code'), item.get('name')
        if not isinstance(code, str) or not re.fullmatch(r'[a-z0-9_]{1,20}', code) or code in seen:
            errors.append('Código de produto inválido ou duplicado.'); continue
        seen.add(code)
        if not isinstance(name, str) or not name.strip() or len(name) > 100:
            errors.append(f'{code}: nome inválido.')
        months, hours, installments = item.get('months'), item.get('hours'), item.get('max_installments')
        if type(months) is not int or not 0 <= months <= 120 or type(installments) is not int or not 1 <= installments <= 12:
            errors.append(f'{code}: duração ou parcelamento inválido.')
        elif months == 0 and (type(hours) is not int or hours < 1 or installments != 1):
            errors.append(f'{code}: avulso exige horas positivas e parcela única.')
        elif months > 0 and hours is not None:
            errors.append(f'{code}: plano mensal não deve informar horas.')
        try:
            value = Decimal(item.get('price')) if isinstance(item.get('price'), str) else Decimal('NaN')
            if not value.is_finite() or value <= 0 or value > Decimal('9999999999.99') or value.as_tuple().exponent < -2:
                errors.append(f'{code}: preço inválido.')
            elif type(months) is int and months > 0 and type(discount) is int and 0 <= discount <= 99 and (value * Decimal(100 - discount) / 100).quantize(Decimal('0.01')) <= 0:
                errors.append(f'{code}: preço após desconto deve ser de ao menos um centavo.')
        except (InvalidOperation, ValueError):
            errors.append(f'{code}: preço inválido.')
    return errors


def current_catalog(on):
    from .models import CatalogVersion
    published = CatalogVersion.objects.filter(status='published')
    matches = list(published.filter(effective_from__lte=on).filter(Q(effective_until__isnull=True) | Q(effective_until__gte=on))[:2])
    if len(matches) > 1:
        raise ValidationError('Há catálogos EcoWork sobrepostos para esta data.')
    if not matches:
        if published.exists():
            raise ValidationError('Não há catálogo EcoWork publicado para esta data.')
        return None, PRODUCTS, 50
    catalog = matches[0]
    errors = validate_catalog(catalog.configuration)
    if errors:
        raise ValidationError({'catalog': errors})
    items = {item['code']: {'hours': None, **{key: value for key, value in item.items() if key != 'code'}, 'price': Decimal(item['price'])} for item in catalog.configuration['products']}
    return catalog, items, catalog.configuration.get('resident_discount_percent', 50)
