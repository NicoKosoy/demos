"""Cuentas de margen por país: comisión, cargos, envío internacional e impuestos del comprador.

Todos los montos en USD (Global Selling publica en dólares y Mercado Libre convierte a moneda local).
"""
from __future__ import annotations

import math
from dataclasses import dataclass


def _num(valor, defecto: float = 0.0) -> float:
    if valor is None or valor == "":
        return defecto
    try:
        resultado = float(valor)
    except (TypeError, ValueError):
        return defecto
    return defecto if math.isnan(resultado) else resultado


@dataclass
class Producto:
    costo_usd: float
    envio_local_usd: float = 0.0   # proveedor -> 3PL o punto de entrega de ML
    prep_usd: float = 0.0          # etiquetado / 3PL por unidad
    peso_kg: float = 0.0
    largo_cm: float = 0.0
    ancho_cm: float = 0.0
    alto_cm: float = 0.0

    @classmethod
    def desde_dict(cls, d: dict) -> "Producto":
        return cls(**{campo: _num(d.get(campo)) for campo in cls.__dataclass_fields__})

    @property
    def costo_total(self) -> float:
        return self.costo_usd + self.envio_local_usd + self.prep_usd


def peso_volumetrico(p: Producto, divisor: float = 5000) -> float:
    if p.largo_cm and p.ancho_cm and p.alto_cm and divisor:
        return p.largo_cm * p.ancho_cm * p.alto_cm / divisor
    return 0.0


def peso_facturable(p: Producto, divisor: float = 5000) -> float:
    return max(p.peso_kg or 0.0, peso_volumetrico(p, divisor))


def costo_envio_internacional(cfg_pais: dict, peso_kg: float) -> float:
    tabla = sorted(cfg_pais["envio"]["tabla_usd_por_kg"])
    peso = peso_kg if peso_kg > 0 else tabla[0][0]
    for hasta, costo in tabla:
        if peso <= hasta + 1e-9:
            return float(costo)
    if len(tabla) == 1:
        return float(tabla[0][1]) * peso / tabla[0][0]
    (k1, c1), (k2, c2) = tabla[-2], tabla[-1]
    return float(c2) + (peso - k2) * (c2 - c1) / (k2 - k1)


def comision_pct(cfg_pais: dict, rubro_cfg: dict | None = None, pais: str | None = None) -> float:
    por_rubro = (rubro_cfg or {}).get("comision_pct") or {}
    if pais and por_rubro.get(pais) not in (None, ""):
        return float(por_rubro[pais])
    return float(cfg_pais["comision_pct"])


def cargo_fijo(cfg_pais: dict, precio: float) -> float:
    if precio < _num(cfg_pais.get("cargo_fijo_hasta_usd")):
        return _num(cfg_pais.get("cargo_fijo_usd"))
    return 0.0


def envio_a_cargo_vendedor(cfg_pais: dict, precio: float, costo_envio: float) -> float:
    modo = cfg_pais["envio"].get("a_cargo_vendedor", "siempre")
    if modo == "siempre":
        return costo_envio
    if modo == "nunca":
        return 0.0
    umbral = _num(cfg_pais["envio"].get("umbral_envio_gratis_usd"))
    return costo_envio if precio >= umbral else 0.0


def impuesto_comprador(cfg_pais: dict, valor_usd: float) -> float:
    """Impuestos de importación que paga el comprador (no salen de tu margen, pero encarecen tu precio)."""
    imp = cfg_pais.get("impuestos_comprador") or {}
    tramo = next(
        (t for t in imp.get("tramos", []) if t.get("hasta_usd") in (None, "") or valor_usd <= float(t["hasta_usd"])),
        None,
    )
    derecho = 0.0
    if tramo:
        derecho = max(0.0, valor_usd * _num(tramo.get("pct")) / 100 - _num(tramo.get("deduccion_usd")))
    por_dentro = _num(imp.get("iva_por_dentro_pct")) / 100
    if por_dentro:
        return (valor_usd + derecho) / (1 - por_dentro) - valor_usd
    return derecho


def calcular(p: Producto, cfg_pais: dict, general: dict, precio_usd: float,
             rubro_cfg: dict | None = None, pais: str | None = None) -> dict:
    precio = float(precio_usd)
    pf = peso_facturable(p, general.get("divisor_volumetrico", 5000))
    envio_total = costo_envio_internacional(cfg_pais, pf)
    envio_vendedor = envio_a_cargo_vendedor(cfg_pais, precio, envio_total)
    envio_comprador = envio_total - envio_vendedor
    com_pct = comision_pct(cfg_pais, rubro_cfg, pais)
    comision = precio * com_pct / 100
    fijo = cargo_fijo(cfg_pais, precio)
    payout = precio * _num(general.get("payout_pct")) / 100
    reserva = precio * _num(general.get("reserva_reclamos_pct")) / 100
    costo = p.costo_total
    ganancia = precio - comision - fijo - envio_vendedor - payout - reserva - costo
    impuesto = impuesto_comprador(cfg_pais, precio + envio_comprador)
    final_usd = precio + envio_comprador + impuesto
    tc = float(cfg_pais["usd_a_local"])
    return {
        "precio_usd": round(precio, 2),
        "precio_local": round(precio * tc, 2),
        "costo_producto_usd": round(costo, 2),
        "comision_pct": com_pct,
        "comision_usd": round(comision, 2),
        "cargo_fijo_usd": round(fijo, 2),
        "peso_facturable_kg": round(pf, 3),
        "envio_internacional_usd": round(envio_total, 2),
        "envio_vendedor_usd": round(envio_vendedor, 2),
        "payout_usd": round(payout, 2),
        "reserva_usd": round(reserva, 2),
        "ganancia_usd": round(ganancia, 2),
        "margen_pct": round(ganancia / precio * 100, 1) if precio > 0 else 0.0,
        "roi_pct": round(ganancia / costo * 100, 1) if costo > 0 else 0.0,
        "impuesto_comprador_usd": round(impuesto, 2),
        "precio_final_comprador_usd": round(final_usd, 2),
        "precio_final_comprador_local": round(final_usd * tc, 0),
    }


def precio_minimo(p: Producto, cfg_pais: dict, general: dict, margen_obj_pct: float | None = None,
                  ganancia_min_usd: float | None = None, rubro_cfg: dict | None = None,
                  pais: str | None = None) -> float | None:
    """Precio más bajo (USD) que deja el margen objetivo Y la ganancia mínima. None si no existe."""
    m = _num(general.get("margen_objetivo_pct") if margen_obj_pct is None else margen_obj_pct) / 100
    g_min = _num(general.get("ganancia_minima_usd") if ganancia_min_usd is None else ganancia_min_usd)
    pf = peso_facturable(p, general.get("divisor_volumetrico", 5000))
    envio_total = costo_envio_internacional(cfg_pais, pf)
    k = 1 - (comision_pct(cfg_pais, rubro_cfg, pais) + _num(general.get("payout_pct"))
             + _num(general.get("reserva_reclamos_pct"))) / 100
    if k - m <= 0:
        return None
    # Entre cortes (cargo fijo, umbral de envío gratis) la ganancia es lineal en el precio.
    cortes = {0.0}
    for c in (cfg_pais.get("cargo_fijo_hasta_usd"), cfg_pais["envio"].get("umbral_envio_gratis_usd")):
        if _num(c) > 0:
            cortes.add(_num(c))
    puntos = sorted(cortes)
    for i, desde in enumerate(puntos):
        hasta = puntos[i + 1] if i + 1 < len(puntos) else math.inf
        fijos = cargo_fijo(cfg_pais, desde) + envio_a_cargo_vendedor(cfg_pais, desde, envio_total) + p.costo_total
        necesario = max(fijos / (k - m), (fijos + g_min) / k)
        candidato = math.ceil(max(desde, necesario) * 100) / 100
        if candidato < hasta:
            r = calcular(p, cfg_pais, general, candidato, rubro_cfg, pais)
            if r["ganancia_usd"] >= g_min - 0.01 and r["margen_pct"] >= m * 100 - 0.1:
                return candidato
    return None


def precio_competitivo(p: Producto, cfg_pais: dict, general: dict, objetivo_final_usd: float,
                       rubro_cfg: dict | None = None, pais: str | None = None) -> float | None:
    """Precio de lista (USD) más alto con el que el comprador paga (con envío e impuestos) <= objetivo."""
    if not objetivo_final_usd or objetivo_final_usd <= 0:
        return None

    def final(x: float) -> float:
        return calcular(p, cfg_pais, general, x, rubro_cfg, pais)["precio_final_comprador_usd"]

    tramos = [(0.01, objetivo_final_usd)]
    umbral = _num(cfg_pais["envio"].get("umbral_envio_gratis_usd"))
    if cfg_pais["envio"].get("a_cargo_vendedor") == "sobre_umbral" and 0 < umbral < objetivo_final_usd:
        tramos = [(0.01, umbral - 0.01), (umbral, objetivo_final_usd)]
    mejor = None
    for bajo, alto in tramos:
        if alto < bajo or final(bajo) > objetivo_final_usd:
            continue
        if final(alto) <= objetivo_final_usd:
            candidato = alto
        else:
            for _ in range(50):
                medio = (bajo + alto) / 2
                if final(medio) <= objetivo_final_usd:
                    bajo = medio
                else:
                    alto = medio
            candidato = bajo
        mejor = candidato if mejor is None else max(mejor, candidato)
    return None if mejor is None else math.floor(mejor * 100) / 100
