import re

from django.core.exceptions import ValidationError


def normalize_cpf(value):
    value = str(value or "").strip()
    if not value:
        return ""
    if re.search(r"[^0-9.\-\s]", value):
        raise ValidationError("Informe um CPF válido.")
    digits = re.sub(r"[^0-9]", "", value)
    if len(digits) != 11 or len(set(digits)) == 1:
        raise ValidationError("Informe um CPF válido.")
    for length in (9, 10):
        digit = (sum(int(digits[i]) * (length + 1 - i) for i in range(length)) * 10) % 11
        if int(digits[length]) != (0 if digit == 10 else digit):
            raise ValidationError("Informe um CPF válido.")
    return digits


def validate_weekdays(value):
    if not isinstance(value, list) or not value or any(type(day) is not int or not 0 <= day <= 6 for day in value):
        raise ValidationError("Informe dias da semana entre 0 (segunda) e 6 (domingo).")
    if len(value) != len(set(value)):
        raise ValidationError("Os dias da semana não podem se repetir.")
