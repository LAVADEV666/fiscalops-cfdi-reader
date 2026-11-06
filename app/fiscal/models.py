"""Typed, lossless-at-source contracts. Monetary JSON values are strings, never floats."""
from dataclasses import dataclass, fields, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any


class Nature(str, Enum):
    TRANSFER = 'transfer'
    RETENTION = 'retention'


@dataclass(frozen=True)
class Number:
    raw: str | None
    value: Decimal | None
    state: str  # missing / invalid / valid
    scale: int | None
    path: str


@dataclass(frozen=True)
class Tax:
    scope: str  # concept / global / local
    nature: Nature
    code: str | None
    factor: str | None
    base: Number
    rate: Number
    amount: Number
    path: str
    concept_index: int | None = None
    local_name: str | None = None


@dataclass(frozen=True)
class Concept:
    index: int
    path: str
    attributes: dict[str, str]
    numbers: dict[str, Number]
    taxes: tuple[Tax, ...]


@dataclass(frozen=True)
class PreservedNode:
    path: str
    namespace: str
    local_name: str
    version: str | None
    status: str
    xml: str  # structural XML, not a byte-identical extraction; original contains exact bytes


@dataclass(frozen=True)
class LocalTaxes:
    path: str
    version: str | None
    transfers: Number
    retentions: Number
    taxes: tuple[Tax, ...]


@dataclass(frozen=True)
class Invoice:
    parser_version: str
    sha256: str
    original: bytes
    encoding: str
    namespace: str
    version: str
    attributes: dict[str, str]
    issuer: dict[str, str]
    receiver: dict[str, str]
    numbers: dict[str, Number]
    concepts: tuple[Concept, ...]
    global_taxes_present: bool
    global_taxes: tuple[Tax, ...]
    global_totals: dict[str, Number]
    locals: tuple[LocalTaxes, ...]
    complements: tuple[PreservedNode, ...]
    uuid: str | None
    structural_issues: tuple[dict[str, str], ...]


def to_data(value: Any, *, include_original: bool = False) -> Any:
    if isinstance(value, Decimal):
        return format(value, 'f')
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bytes):
        if include_original:
            import base64
            return {'base64': base64.b64encode(value).decode('ascii')}
        return {'preserved_bytes': len(value), 'exported': False}
    if is_dataclass(value):
        return {f.name: to_data(getattr(value, f.name), include_original=include_original) for f in fields(value)}
    if isinstance(value, dict):
        return {str(k): to_data(v, include_original=include_original) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_data(v, include_original=include_original) for v in value]
    if isinstance(value, float):
        raise TypeError('Binary floating-point is forbidden in fiscal contracts')
    return value
