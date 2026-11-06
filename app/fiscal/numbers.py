"""Bounded decimal lexical conversion; absence and invalid input never become zero."""
from decimal import Context, Decimal, ROUND_HALF_UP, localcontext
import re
from .models import Number

DECIMAL_CONTEXT = Context(prec=80, rounding=ROUND_HALF_UP)
LEXICAL = re.compile(r'[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)\Z', re.ASCII)
ZERO = Decimal('0')


def number(raw: str | None, path: str) -> Number:
    if raw is None:
        return Number(None, None, 'missing', None, path)
    lexical = raw.strip(' \t\r\n')  # XML Schema decimal whitespace collapse
    if len(lexical) > 64 or not LEXICAL.fullmatch(lexical):
        return Number(raw, None, 'invalid', None, path)
    value = Decimal(lexical)
    scale = max(0, -value.as_tuple().exponent)
    if len(value.as_tuple().digits) > 36 or scale > 18:
        return Number(raw, None, 'invalid', scale, path)
    return Number(raw, value, 'valid', scale, path)


def quantize(value: Decimal, digits: int) -> Decimal:
    with localcontext(DECIMAL_CONTEXT):
        return value.quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP)


def complete_sum(values) -> Decimal | None:
    values = tuple(values)
    if any(value is None for value in values):
        return None
    with localcontext(DECIMAL_CONTEXT):
        return sum(values, ZERO)
