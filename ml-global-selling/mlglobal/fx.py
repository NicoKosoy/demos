"""Actualiza los tipos de cambio USD -> moneda local (fuente gratuita, sin clave)."""
from __future__ import annotations

import requests

from . import config

FUENTE = "https://open.er-api.com/v6/latest/USD"


def actualizar_tipos_de_cambio() -> dict[str, float]:
    r = requests.get(FUENTE, timeout=20)
    r.raise_for_status()
    tasas = r.json()["rates"]
    cambios = {}
    for codigo, cfg in config.paises().items():
        if cfg["moneda"] in tasas:
            cambios[codigo] = round(float(tasas[cfg["moneda"]]), 4)
    config.guardar_cambios("paises", {c: {"usd_a_local": v} for c, v in cambios.items()})
    return cambios
