"""Brazilian document validation helpers."""

from __future__ import annotations

from .formatters import only_digits

try:
    from validate_docbr import CNPJ, CPF
except Exception:  # pragma: no cover - runtime fallback before dependencies install
    CNPJ = None
    CPF = None


def validate_cpf(value: str | None) -> bool:
    digits = only_digits(value)
    if not digits:
        return True
    if CPF is None:
        return len(digits) == 11
    return bool(CPF().validate(digits))


def validate_cnpj(value: str | None) -> bool:
    digits = only_digits(value)
    if not digits:
        return True
    if CNPJ is None:
        return len(digits) == 14
    return bool(CNPJ().validate(digits))


def validate_document(document_type: str | None, value: str | None) -> bool:
    if str(document_type or "").upper() == "CPF":
        return validate_cpf(value)
    return validate_cnpj(value)
