"""Cuántos días de 'disponibilidad de stock' declarar en la publicación y cuándo le llega al comprador."""
from __future__ import annotations

import math


def _num(valor):
    try:
        return None if valor in (None, "") else float(valor)
    except (TypeError, ValueError):
        return None


def calcular_demora(proveedor: dict | None, producto: dict, general: dict, cfg_pais: dict) -> dict:
    """Días hábiles.

    - ruta 'directo': el proveedor despacha con la etiqueta de Mercado Libre. Cuenta solo su preparación:
      el primer escaneo del correo ya es "despachado".
    - ruta '3pl': el proveedor (o Amazon/eBay/Walmart) manda a tu prep center, que reetiqueta y despacha.
      Suma el tránsito hasta el 3PL y el día de proceso.
    - ruta 'full': stock enviado antes al depósito de Mercado Libre en Texas. No hay demora que declarar.
    """
    proveedor = proveedor or {}
    ruta = (producto.get("ruta") or "directo").lower()
    if ruta == "full":
        # El stock ya está en el depósito de Mercado Libre en Texas: no se declara demora.
        tmin, tmax = cfg_pais.get("transito_full_dias") or cfg_pais.get("transito_internacional_dias", [5, 10])
        return {"ruta": ruta, "dias_necesarios": 0.0, "dias_a_declarar": 0, "demora_confirmada": True,
                "entrega_min": int(math.ceil(tmin)), "entrega_max": int(math.ceil(tmax)), "alerta_exposicion": False}
    prep = _num(proveedor.get("dias_preparacion"))
    confirmada = prep is not None
    if prep is None:
        prep = float(general["dias_proveedor_por_defecto"])
    transito = extra = 0.0
    if ruta == "3pl":
        transito = _num(proveedor.get("dias_transito_local"))
        if transito is None:
            transito = float(general["dias_transito_local_por_defecto"])
        extra = float(general["dias_3pl"])
    necesarios = prep + transito + extra + float(general["colchon_dias"])
    estandar = float(general["dias_despacho_estandar"])
    declarar = math.ceil(necesarios) if necesarios > estandar else 0
    despacho = declarar or estandar
    tmin, tmax = cfg_pais.get("transito_internacional_dias", [5, 10])
    return {
        "ruta": ruta,
        "dias_necesarios": round(necesarios, 1),
        "dias_a_declarar": int(declarar),
        "demora_confirmada": confirmada,
        "entrega_min": int(math.ceil(despacho + tmin)),
        "entrega_max": int(math.ceil(despacho + tmax)),
        "alerta_exposicion": declarar > float(general["max_dias_recomendado"]),
    }
