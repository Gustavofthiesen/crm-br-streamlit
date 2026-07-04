"""ViaCEP integration."""

from __future__ import annotations

from typing import Any

import requests

from crm.formatters import only_digits

VIACEP_URL = "https://viacep.com.br/ws/{cep}/json/"


def lookup_cep(cep: str, timeout: int = 5) -> dict[str, Any] | None:
    digits = only_digits(cep)
    if len(digits) != 8:
        return None

    response = requests.get(VIACEP_URL.format(cep=digits), timeout=timeout)
    response.raise_for_status()
    data = response.json()
    if data.get("erro"):
        return None
    return {
        "cep": digits,
        "address": data.get("logradouro") or "",
        "neighborhood": data.get("bairro") or "",
        "city": data.get("localidade") or "",
        "state": data.get("uf") or "",
    }
