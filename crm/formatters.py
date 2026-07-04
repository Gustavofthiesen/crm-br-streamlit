"""Brazilian presentation and parsing helpers."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import Any


def only_digits(value: Any) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def mask_cpf(value: Any) -> str:
    digits = only_digits(value)
    if len(digits) != 11:
        return str(value or "")
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def mask_cnpj(value: Any) -> str:
    digits = only_digits(value)
    if len(digits) != 14:
        return str(value or "")
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def mask_document(document_type: str | None, value: Any) -> str:
    if str(document_type or "").upper() == "CPF":
        return mask_cpf(value)
    return mask_cnpj(value)


def mask_phone(value: Any) -> str:
    digits = only_digits(value)
    if len(digits) == 10:
        return f"({digits[:2]}) {digits[2:6]}-{digits[6:]}"
    if len(digits) == 11:
        return f"({digits[:2]}) {digits[2:7]}-{digits[7:]}"
    return str(value or "")


def mask_cep(value: Any) -> str:
    digits = only_digits(value)
    if len(digits) != 8:
        return str(value or "")
    return f"{digits[:5]}-{digits[5:]}"


def format_currency(value: Any) -> str:
    if value in (None, ""):
        value = Decimal("0")
    amount = Decimal(str(value))
    text = f"{amount:,.2f}"
    text = text.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {text}"


def format_date_br(value: date | datetime | None) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        value = value.date()
    return value.strftime("%d/%m/%Y")


def format_datetime_br(value: datetime | None) -> str:
    if not value:
        return ""
    return value.strftime("%d/%m/%Y %H:%M")


def parse_date_br(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    if not text:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError("Use uma data no formato DD/MM/AAAA.")


def parse_datetime_br(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    parsed_date = parse_date_br(value)
    if not parsed_date:
        return None
    return datetime.combine(parsed_date, time(hour=9))


def parse_decimal_br(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    text = str(value or "0").strip().replace("R$", "").replace(" ", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Informe um valor monetário válido.") from exc


def format_bool(value: Any) -> str:
    return "Sim" if bool(value) else "Não"
